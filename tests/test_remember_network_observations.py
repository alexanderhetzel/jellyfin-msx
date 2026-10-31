import json

import pytest

from tools import remember_network_observations as network

ORIGIN = "https://synthetic.example"
HTML = ORIGIN + "/msx/remember.html"
SCRIPT = ORIGIN + "/msx/remember.js"
SDK = "https://msx.benzac.de/js/tvx-plugin.min.js"


def event(sequence, method, params, *, session=None, target=None):
    source = {"targetId": target or (session + "-target" if session else "root-target")}
    if session is not None:
        source["sessionId"] = session
    return {"sequence": sequence, "method": method, "params": params, "source": source}


def request(sequence, *, url=HTML, request_id="r", frame="f", loader="l", session=None, **extra):
    return event(
        sequence,
        "Network.requestWillBeSent",
        {
            "requestId": request_id,
            "frameId": frame,
            "loaderId": loader,
            "documentURL": HTML,
            "type": "Document" if url == HTML else "Script",
            "request": {"url": url, "method": "GET"},
            **extra,
        },
        session=session,
    )


def response(sequence, *, url=HTML, request_id="r", frame="f", loader="l", session=None, **extra):
    return event(
        sequence,
        "Network.responseReceived",
        {
            "requestId": request_id,
            "frameId": frame,
            "loaderId": loader,
            "response": {"url": url, "status": 200, **extra},
        },
        session=session,
    )


def finish(sequence, *, request_id="r", session=None):
    return event(sequence, "Network.loadingFinished", {"requestId": request_id}, session=session)


def ingest(observation, events, *, has_more=False, truncated=False, after=None, cursor=None):
    page = {
        "events": events,
        "cursor": cursor if cursor is not None else events[-1]["sequence"],
        "hasMore": has_more,
        "truncated": truncated,
    }
    observation.ingest(page, after_cursor=observation.cursor if after is None else after)
    return observation.snapshot()


def observation():
    return network.NetworkObservations(ORIGIN, "root-target")


def attach(sequence=1, *, session="child", target="child-target"):
    return event(
        sequence,
        "Target.attachedToTarget",
        {"sessionId": session, "targetInfo": {"type": "iframe", "targetId": target, "url": HTML}},
    )


def test_root_same_process_frame_works_without_child_and_separates_snapshot_from_completion():
    x = observation()
    x.observe_tree({"frame": {"url": HTML}, "resources": [{"url": SCRIPT}]})
    empty = x.snapshot()
    assert empty["own_frame_seen_in_snapshot"] and empty["resource_tree_seen"]["plugin_script"]
    assert empty["resources"]["plugin_html"]["loading_finished"] is None
    report = ingest(
        x,
        [
            event(1, "Page.frameNavigated", {"frame": {"id": "f", "loaderId": "l", "url": HTML}}),
            request(2),
            response(3),
            finish(4),
        ],
    )
    assert report["own_frame_navigation_observed"]
    row = report["resources"]["plugin_html"]
    assert row["requests"] == row["response_200"] == row["loading_finished"] == 1
    assert report["resources"]["plugin_script"]["loading_finished"] == 0
    assert report["initial_navigation_gap"] and report["child_coverage"] == "unknown"


def test_identical_request_ids_never_join_across_sessions():
    x = observation()
    report = ingest(
        x, [attach(), request(2), response(3, session="child"), finish(4, session="child")]
    )
    assert report["resources"]["plugin_html"]["response_200"] == 0
    assert report["resources"]["plugin_html"]["loading_finished"] == 0
    assert report["coverage"]["orphan_event"]
    report = ingest(
        x, [request(5, session="child"), response(6, session="child"), finish(7, session="child")]
    )
    assert report["resources"]["plugin_html"]["requests"] == 2
    assert report["resources"]["plugin_html"]["loading_finished"] == 1


def test_redirect_hop_reusing_id_cannot_credit_original_resource_completion():
    x = observation()
    report = ingest(
        x,
        [
            request(1),
            request(2, url=SCRIPT, redirectResponse={"status": 302}),
            response(3, url=SCRIPT),
            finish(4),
        ],
    )
    assert report["resources"]["plugin_html"]["redirects"] == 1
    assert report["resources"]["plugin_html"]["loading_finished"] == 0
    assert report["resources"]["plugin_script"]["loading_finished"] == 1
    x = observation()
    report = ingest(
        x,
        [
            request(1),
            request(2, url="https://unknown.example/private", redirectResponse={"status": 302}),
            finish(3),
        ],
    )
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


@pytest.mark.parametrize("boundary", ["loader", "frame-detach", "target-detach", "reattach"])
def test_changed_epoch_or_detach_cannot_complete_stale_request(boundary):
    x = observation()
    events = [attach(), request(2, session="child"), response(3, session="child")]
    if boundary == "loader":
        events.append(
            event(
                4,
                "Page.frameNavigated",
                {"frame": {"id": "f", "loaderId": "new", "url": HTML}},
                session="child",
            )
        )
    elif boundary == "frame-detach":
        events.append(event(4, "Page.frameDetached", {"frameId": "f"}, session="child"))
    elif boundary == "target-detach":
        events.append(event(4, "Target.detachedFromTarget", {"sessionId": "child"}))
    else:
        events.append(attach(4))
    events.append(finish(5, session="child"))
    report = ingest(x, events)
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


def test_reused_id_in_new_loader_and_repeated_urls_across_frames_do_not_join():
    x = observation()
    report = ingest(
        x, [request(1), response(2), request(3, loader="new"), response(4, loader="l"), finish(5)]
    )
    assert report["resources"]["plugin_html"]["requests"] == 2
    assert report["resources"]["plugin_html"]["loading_finished"] == 0
    assert report["coverage"]["loader_gap"]
    x = observation()
    report = ingest(x, [request(1, frame="a"), response(2, frame="b"), finish(3)])
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


def test_orphan_events_cannot_acquire_identity_from_resource_tree_or_late_attachment():
    x = observation()
    x.observe_tree({"frame": {"url": HTML}, "resources": [{"url": SCRIPT}]})
    report = ingest(x, [response(1, url=SCRIPT), finish(2), request(3, session="late"), attach(4)])
    assert report["resource_tree_seen"]["plugin_script"]
    assert report["resources"]["plugin_script"]["loading_finished"] == 0
    assert report["coverage"]["orphan_event"] and report["coverage"]["late_or_unknown_child"]


def test_partial_pagination_withholds_joins_until_same_filter_cursor_drain():
    x = observation()
    first = ingest(x, [request(1), response(2)], has_more=True, cursor=8)
    assert first["resources"]["plugin_html"]["response_200"] is None
    # Filtered sequence gaps are not evidence of lost events.
    report = ingest(x, [finish(10)], cursor=15)
    assert report["joined_network_evidence"] == "available"
    assert report["resources"]["plugin_html"]["loading_finished"] == 1
    assert not report["coverage"]["cursor_gap"]


@pytest.mark.parametrize("gap", ["truncated", "cursor", "filter", "budget"])
def test_partial_capture_never_exposes_joined_completion(gap, monkeypatch):
    x = observation()
    if gap == "budget":
        monkeypatch.setattr(network, "MAX_EVENTS", 2)
    page = {
        "events": [request(1), response(2), finish(3)],
        "cursor": 3,
        "hasMore": False,
        "truncated": gap == "truncated",
    }
    x.ingest(
        page,
        after_cursor=99 if gap == "cursor" else 0,
        methods=("Network.loadingFinished",) if gap == "filter" else network.METHODS,
    )
    report = x.snapshot()
    assert report["joined_network_evidence"] == "withheld_partial_drain"
    assert report["resources"]["plugin_html"]["loading_finished"] is None


def test_replayed_batches_and_duplicate_events_do_not_inflate_counts():
    x = observation()
    events = [request(1), request(2), response(3), response(4), finish(5), finish(6)]
    report = ingest(x, events)
    replay = ingest(x, events, after=0)
    assert replay == report
    row = report["resources"]["plugin_html"]
    assert row["requests"] == row["response_200"] == row["loading_finished"] == 1


def test_cache_worker_http_errors_and_csp_failure_keep_distinct_facts():
    x = observation()
    report = ingest(
        x,
        [
            request(1, url=SCRIPT),
            response(2, url=SCRIPT, status=404, fromDiskCache=True, fromServiceWorker=True),
            event(3, "Network.requestServedFromCache", {"requestId": "r"}),
            finish(4),
        ],
    )
    row = report["resources"]["plugin_script"]
    assert row["response_200"] == 0 and row["response_other"] == row["loading_finished"] == 1
    assert row["cache_observed"] == row["service_worker_observed"] == 1
    report = ingest(
        x,
        [
            request(5, url=SDK, request_id="sdk"),
            event(
                6,
                "Network.loadingFailed",
                {
                    "requestId": "sdk",
                    "blockedReason": "csp",
                    "canceled": True,
                    "errorText": "secret arbitrary message",
                },
            ),
        ],
    )
    row = report["resources"]["vendor_sdk"]
    assert row["blocked_csp"] == row["canceled"] == row["loading_failed"] == 1
    assert row["loading_finished"] == 0


def test_foreign_document_sdk_and_adversarial_secrets_never_enter_output():
    x = observation()
    first = request(1, url=SDK)
    first["params"]["documentURL"] = "https://unknown.example/secret-context"
    secret_request = request(2, url=HTML + "?secret-query", request_id="secret-id")
    secret_request["params"]["request"].update(
        {"headers": {"secret-header": "secret-value"}, "postData": "secret-body"}
    )
    report = ingest(
        x,
        [
            first,
            secret_request,
            response(3, url=HTML + "?secret-query", request_id="secret-id"),
            finish(4, request_id="secret-id"),
        ],
    )
    assert report["resources"]["vendor_sdk"]["requests"] == 0
    serialized = json.dumps(report)
    assert all(value not in serialized for value in ("secret", ORIGIN, "root-target", "frameId"))
    report["resources"]["plugin_html"]["response_200"] = 900
    assert x.snapshot()["resources"]["plugin_html"]["response_200"] == 1


def test_transient_state_budgets_and_saturation_are_bounded(monkeypatch):
    monkeypatch.setattr(network, "MAX_REQUESTS", 2)
    x = observation()
    x.counts["plugin_html"]["requests"] = network.LIMIT
    report = ingest(
        x, [request(1, request_id="a"), request(2, request_id="b"), request(3, request_id="c")]
    )
    assert len(x.requests) == 2
    assert report["coverage"]["budget_exhausted"]
    assert report["resources"]["plugin_html"]["requests"] == network.LIMIT


def test_unknown_or_about_blank_child_is_not_an_own_attached_session():
    x = observation()
    unknown = attach()
    unknown["params"]["targetInfo"]["url"] = "about:blank"
    report = ingest(
        x,
        [
            unknown,
            request(2, session="child"),
            response(3, session="child"),
            finish(4, session="child"),
        ],
    )
    assert len(x.sessions) == 1
    assert report["coverage"]["late_or_unknown_child"]
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


def test_same_category_different_query_response_does_not_join():
    x = observation()
    report = ingest(
        x, [request(1, url=HTML + "?first"), response(2, url=HTML + "?other"), finish(3)]
    )
    assert report["resources"]["plugin_html"]["response_200"] == 0
    assert report["resources"]["plugin_html"]["loading_finished"] == 0
    assert report["coverage"]["loader_gap"]


@pytest.mark.parametrize("reason", ["unsupported", "read_timeout"])
def test_collector_failure_withholds_positive_joins_without_error_text(reason):
    x = observation()
    ingest(x, [request(1), response(2), finish(3)])
    x.mark_incomplete(reason)
    report = x.snapshot()
    assert report["coverage"][reason]
    assert report["resources"]["plugin_html"]["loading_finished"] is None
    with pytest.raises(ValueError, match="Unknown observation outcome"):
        x.mark_incomplete("secret protocol error")


def test_frame_session_and_snapshot_budgets_stay_bounded(monkeypatch):
    monkeypatch.setattr(network, "MAX_FRAMES", 2)
    monkeypatch.setattr(network, "MAX_SESSIONS", 2)
    x = observation()
    ingest(
        x,
        [
            attach(),
            attach(2, session="extra", target="extra-target"),
            request(3, frame="a"),
            request(4, frame="b"),
            request(5, frame="c"),
        ],
    )
    assert len(x.sessions) == len(x.frames) == 2
    assert x.snapshot()["coverage"]["budget_exhausted"]
    x = observation()
    x.observe_tree(
        {
            "frame": {"url": HTML},
            "childFrames": [
                {"frame": {"url": HTML}},
                {"frame": {"url": HTML}},
                {"frame": {"url": HTML}},
            ],
        }
    )
    assert x.snapshot()["coverage"]["budget_exhausted"]


def test_out_of_order_page_cannot_hide_earlier_detachment():
    x = observation()
    events = [request(1), response(2), finish(4), event(3, "Page.frameDetached", {"frameId": "f"})]
    report = ingest(x, events, cursor=4)
    assert report["coverage"]["cursor_gap"]
    assert report["resources"]["plugin_html"]["loading_finished"] is None


@pytest.mark.parametrize("metadata", [{"truncated": True}, {"has_more": True}])
def test_replayed_page_cannot_discard_adverse_coverage_metadata(metadata):
    x = observation()
    events = [request(1), response(2), finish(3)]
    ingest(x, events)
    report = ingest(x, events, after=0, **metadata)
    assert report["joined_network_evidence"] == "withheld_partial_drain"
    assert report["resources"]["plugin_html"]["loading_finished"] is None


@pytest.mark.parametrize("boundary", ["detach", "reattach"])
def test_parent_lifecycle_invalidates_descendant_session_requests(boundary):
    x = observation()
    nested = attach(2, session="nested", target="nested-target")
    nested["source"]["sessionId"] = "child"
    nested["source"]["targetId"] = "child-target"
    events = [attach(), nested, request(3, session="nested"), response(4, session="nested")]
    if boundary == "detach":
        events.append(event(5, "Target.detachedFromTarget", {"sessionId": "child"}))
    else:
        events.append(attach(5))
    events.append(finish(6, session="nested"))
    report = ingest(x, events)
    assert "nested" not in x.sessions and "nested" not in x.parents
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


def test_invalid_attachment_ancestry_cycle_is_ignored():
    x = observation()
    cycle = attach(2)
    cycle["source"]["sessionId"] = "child"
    cycle["source"]["targetId"] = "child-target"
    report = ingest(x, [attach(), cycle])
    assert x.parents == {"child": "root"}
    assert report["coverage"]["late_or_unknown_child"]


def test_late_document_request_cannot_resurrect_retired_loader():
    x = observation()
    report = ingest(
        x,
        [
            event(1, "Page.frameNavigated", {"frame": {"id": "f", "loaderId": "old", "url": HTML}}),
            event(2, "Page.frameNavigated", {"frame": {"id": "f", "loaderId": "new", "url": HTML}}),
            request(3, loader="old"),
            response(4, loader="old"),
            finish(5),
        ],
    )
    assert report["coverage"]["loader_gap"]
    assert report["resources"]["plugin_html"]["loading_finished"] == 0
    assert x.frames[("root", "f")] == "new"


def test_explicit_source_target_and_session_conflict_is_unknown():
    x = observation()
    mismatched = response(3, session="child")
    mismatched["source"]["targetId"] = "foreign-target"
    report = ingest(
        x, [attach(), request(2, session="child"), mismatched, finish(4, session="child")]
    )
    assert report["coverage"]["identity_conflict"]
    assert report["resources"]["plugin_html"]["loading_finished"] is None


def test_oversized_event_page_is_rejected_before_order_or_replay_projection(monkeypatch):
    monkeypatch.setattr(network, "MAX_PAGE_EVENTS", 2)
    x = observation()
    report = ingest(x, [request(1), response(2), finish(3)])
    assert report["coverage"]["budget_exhausted"]
    assert x.events == 0 and x.requests == {}
    assert report["resources"]["plugin_html"]["loading_finished"] is None


def test_detached_frame_cannot_restart_a_retired_loader():
    x = observation()
    report = ingest(
        x,
        [
            request(1),
            event(2, "Page.frameDetached", {"frameId": "f"}),
            request(3),
            response(4),
            finish(5),
        ],
    )
    assert report["coverage"]["loader_gap"]
    assert report["resources"]["plugin_html"]["loading_finished"] == 0


def test_nested_attachment_cannot_make_ancestor_a_child():
    x = observation()
    nested = attach(2, session="nested", target="nested-target")
    nested["source"] = {"sessionId": "child", "targetId": "child-target"}
    cycle = attach(3)
    cycle["source"] = {"sessionId": "nested", "targetId": "nested-target"}
    report = ingest(x, [attach(), nested, cycle])
    assert x.parents == {"child": "root", "nested": "child"}
    assert report["coverage"]["late_or_unknown_child"]


@pytest.mark.parametrize("suffix", ["?different-representation=1", "#fragment"])
def test_only_literal_published_sdk_url_is_in_scope(suffix):
    x = observation()
    url = SDK + suffix
    report = ingest(x, [request(1, url=url), response(2, url=url), finish(3)])
    x.observe_tree({"frame": {"url": HTML}, "resources": [{"url": url}]})
    assert report["resources"]["vendor_sdk"]["requests"] == 0
    assert report["resources"]["vendor_sdk"]["loading_finished"] == 0
    assert not x.snapshot()["resource_tree_seen"]["vendor_sdk"]


def test_target_only_event_cannot_choose_between_multiple_attached_sessions():
    x = observation()
    start = request(3, session="alpha")
    start["source"]["targetId"] = "shared-target"
    terminal = finish(5, session="alpha")
    terminal["source"]["targetId"] = "shared-target"
    report = ingest(
        x,
        [
            attach(1, session="alpha", target="shared-target"),
            attach(2, session="beta", target="shared-target"),
            start,
            event(4, "Network.responseReceived", response(4)["params"], target="shared-target"),
            terminal,
        ],
    )
    assert report["coverage"]["identity_conflict"]
    assert x.counts["plugin_html"]["response_200"] == 0
    assert report["resources"]["plugin_html"]["loading_finished"] is None
