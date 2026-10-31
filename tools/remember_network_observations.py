"""Offline, bounded projection of task-tab CDP metadata. Never controls a browser.

Raw input and correlation identifiers belong in ephemeral RAM, never a report.
Only a fully drained, untruncated cursor stream exposes joined network evidence.
Even that stream has initial-navigation and unknown child-coverage gaps.
"""

import hashlib
from urllib.parse import urlsplit

METHODS = (
    "Target.attachedToTarget",
    "Target.detachedFromTarget",
    "Page.frameNavigated",
    "Page.frameDetached",
    "Network.requestWillBeSent",
    "Network.responseReceived",
    "Network.loadingFinished",
    "Network.loadingFailed",
    "Network.requestServedFromCache",
)
CATEGORIES = ("entry_content", "plugin_html", "plugin_script", "vendor_sdk")
LIMIT = 1_000_000
MAX_EVENTS = 4096
MAX_PAGE_EVENTS = 1000
MAX_SESSIONS = 16
MAX_REQUESTS = 128
MAX_FRAMES = 64


def identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 256


def increment(row, key):
    row[key] = min(LIMIT, row[key] + 1)


class NetworkObservations:
    def __init__(self, origin, root_target, *, cursor=0):
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("HTTPS origin required")
        if not identifier(root_target):
            raise ValueError("Root target required")
        self.origin = origin
        self.sessions = {"root": root_target}
        self.parents = {}
        self.requests = {}
        self.frames = {}
        self.retired_loaders = set()
        self.cursor = cursor
        self.sequence = cursor
        self.events = 0
        self.coverage = dict.fromkeys(
            (
                "truncated",
                "pending_pages",
                "cursor_gap",
                "budget_exhausted",
                "orphan_event",
                "late_or_unknown_child",
                "detached",
                "loader_gap",
                "unsupported",
                "read_timeout",
                "identity_conflict",
            ),
            False,
        )
        self.drained = False
        self.seen_page = False
        self.own_frame_current = False
        self.own_frame_navigation = False
        self.resources = dict.fromkeys(CATEGORIES, False)
        self.counts = {
            name: dict.fromkeys(
                (
                    "requests",
                    "response_200",
                    "response_other",
                    "loading_finished",
                    "loading_failed",
                    "blocked_csp",
                    "canceled",
                    "cache_observed",
                    "service_worker_observed",
                    "redirects",
                ),
                0,
            )
            for name in CATEGORIES
        }

    def category(self, value):
        if not isinstance(value, str) or len(value) > 8192:
            return None
        try:
            parsed = urlsplit(value)
            if parsed.username or parsed.password:
                return None
            base = parsed.scheme + "://" + parsed.netloc
            if base == self.origin:
                return {
                    "/msx/remember.json": "entry_content",
                    "/msx/remember.html": "plugin_html",
                    "/msx/remember.js": "plugin_script",
                }.get(parsed.path)
            if value == "https://msx.benzac.de/js/tvx-plugin.min.js":
                return "vendor_sdk"
        except ValueError:
            pass
        return None

    def _session(self, source):
        session = source.get("sessionId")
        if session is not None:
            if session not in self.sessions or session == "root":
                return None
            if source.get("targetId", self.sessions[session]) != self.sessions[session]:
                self.coverage["identity_conflict"] = True
                return None
            return session
        target = source.get("targetId")
        matches = [key for key, value in self.sessions.items() if value == target]
        if len(matches) > 1:
            self.coverage["identity_conflict"] = True
            return None
        return matches[0] if matches else None

    def _clear(self, session, frame=None, keep_loader=None):
        for key, value in list(self.requests.items()):
            if key[0] == session and (frame is None or value["frame"] == frame):
                if keep_loader is None or value["loader"] != keep_loader:
                    del self.requests[key]
        if frame is None:
            self.frames = {key: value for key, value in self.frames.items() if key[0] != session}

    def _drop_session(self, session):
        for child, parent in list(self.parents.items()):
            if parent == session:
                self._drop_session(child)
        self._clear(session)
        self.sessions.pop(session, None)
        self.parents.pop(session, None)

    def ingest(self, page, *, after_cursor, methods=METHODS):
        self.coverage["truncated"] |= page.get("truncated") is True
        if not isinstance(page.get("events"), list) or len(page["events"]) > MAX_PAGE_EVENTS:
            self.coverage["budget_exhausted"] = True
            self.drained = False
            return
        sequences = [event.get("sequence") for event in page.get("events", [])]
        if any(type(value) is not int for value in sequences) or any(
            right < left
            for left, right in zip(sequences, sequences[1:], strict=False)
            if type(left) is int and type(right) is int
        ):
            self.coverage["cursor_gap"] = True
        if (
            self.seen_page
            and tuple(methods) == METHODS
            and type(page.get("cursor")) is int
            and page["cursor"] <= self.cursor
            and all(
                type(e.get("sequence")) is int and e["sequence"] <= self.sequence
                for e in page.get("events", [])
            )
        ):
            if page.get("hasMore") is not False:
                self.coverage["pending_pages"] = True
                self.drained = False
            return
        self.seen_page = True
        if after_cursor != self.cursor or tuple(methods) != METHODS:
            self.coverage["cursor_gap"] = True
        self.coverage["pending_pages"] = page.get("hasMore") is not False
        self.drained = not self.coverage["pending_pages"]
        cursor = page.get("cursor")
        if type(cursor) is not int or cursor < self.cursor:
            self.coverage["cursor_gap"] = True
            return
        for event in page.get("events", []):
            sequence = event.get("sequence")
            if type(sequence) is not int or sequence <= self.sequence:
                continue
            if sequence > cursor:
                self.coverage["cursor_gap"] = True
                continue
            if self.events >= MAX_EVENTS:
                self.coverage["budget_exhausted"] = True
                break
            self.sequence = sequence
            self.events += 1
            self._event(event)
        self.cursor = cursor

    def _event(self, event):
        method, params = event.get("method"), event.get("params", {})
        session = self._session(event.get("source", {}))
        if session is None:
            self.coverage["late_or_unknown_child"] = True
            return
        if method == "Target.attachedToTarget":
            child, info = params.get("sessionId"), params.get("targetInfo", {})
            if not identifier(child) or child == "root" or info.get("type") != "iframe":
                return
            if self.category(info.get("url")) != "plugin_html":
                self.coverage["late_or_unknown_child"] = True
                return
            if child not in self.sessions and len(self.sessions) >= MAX_SESSIONS:
                self.coverage["budget_exhausted"] = True
                return
            if not identifier(info.get("targetId")):
                return
            # Only a new/detached child may be attached below this parent; reject
            # ancestry cycles rather than recursively walking invalid metadata.
            ancestor = session
            while ancestor != "root":
                if ancestor == child:
                    self.coverage["late_or_unknown_child"] = True
                    return
                ancestor = self.parents[ancestor]
            self._drop_session(child)
            self.sessions[child] = info["targetId"]
            self.parents[child] = session
            return
        if method == "Target.detachedFromTarget":
            child = params.get("sessionId")
            if child in self.sessions and child != "root":
                self._drop_session(child)
                self.coverage["detached"] = True
            return
        if method == "Page.frameDetached":
            frame = params.get("frameId")
            if identifier(frame):
                old = self.frames.get((session, frame))
                if old is not None:
                    self._retire(session, frame, old)
                self._clear(session, frame)
                self.frames.pop((session, frame), None)
                self.coverage["detached"] = True
            return
        if method == "Page.frameNavigated":
            frame = params.get("frame", {})
            if identifier(frame.get("id")) and identifier(frame.get("loaderId")):
                accepted = self._frame(session, frame["id"], frame["loaderId"])
                if accepted and self.category(frame.get("url")) == "plugin_html":
                    self.own_frame_navigation = True
            return
        if method == "Network.requestWillBeSent":
            self._request(session, params)
            return
        if method not in METHODS or not method.startswith("Network."):
            return
        key = (session, params.get("requestId"))
        record = self.requests.get(key)
        if record is None:
            self.coverage["orphan_event"] = True
            return
        row = self.counts[record["category"]]
        if method == "Network.responseReceived":
            response = params.get("response", {})
            if (
                params.get("frameId") != record["frame"]
                or params.get("loaderId") != record["loader"]
                or self.category(response.get("url")) != record["category"]
                or self._url_key(response.get("url")) != record["url_key"]
            ):
                del self.requests[key]
                self.coverage["loader_gap"] = True
            elif not record["response"]:
                record["response"] = True
                increment(
                    row, "response_200" if response.get("status") == 200 else "response_other"
                )
                if response.get("fromServiceWorker") is True:
                    increment(row, "service_worker_observed")
                if response.get("fromDiskCache") is True:
                    self._cache(record, row)
        elif method == "Network.requestServedFromCache":
            self._cache(record, row)
        elif (
            method in {"Network.loadingFinished", "Network.loadingFailed"}
            and not record["terminal"]
        ):
            if method == "Network.loadingFinished" and not record["response"]:
                self.coverage["orphan_event"] = True
                return
            record["terminal"] = True
            increment(row, "loading_finished" if method.endswith("Finished") else "loading_failed")
            if method.endswith("Failed"):
                if params.get("blockedReason") == "csp":
                    increment(row, "blocked_csp")
                if params.get("canceled") is True:
                    increment(row, "canceled")

    @staticmethod
    def _cache(record, row):
        if not record["cache"]:
            record["cache"] = True
            increment(row, "cache_observed")

    @staticmethod
    def _url_key(value):
        if not isinstance(value, str) or len(value) > 8192:
            return None
        return hashlib.sha256(value.encode("utf-8")).digest()

    def _frame(self, session, frame, loader):
        key = (session, frame)
        if (session, frame, loader) in self.retired_loaders:
            self.coverage["loader_gap"] = True
            return False
        if key not in self.frames and len(self.frames) >= MAX_FRAMES:
            self.coverage["budget_exhausted"] = True
            return False
        old = self.frames.get(key)
        if old is not None and old != loader:
            if not self._retire(session, frame, old):
                return False
        self._clear(session, frame, loader)
        self.frames[key] = loader
        return True

    def _retire(self, session, frame, loader):
        if len(self.retired_loaders) >= MAX_REQUESTS:
            self.coverage["budget_exhausted"] = True
            return False
        self.retired_loaders.add((session, frame, loader))
        return True

    def _request(self, session, params):
        request = params.get("request", {})
        request_id, frame, loader = (
            params.get(key) for key in ("requestId", "frameId", "loaderId")
        )
        if not all(identifier(value) for value in (request_id, frame, loader)):
            return
        key = (session, request_id)
        old = self.requests.get(key)
        name = self.category(request.get("url")) if request.get("method") == "GET" else None
        if old is not None:
            if "redirectResponse" in params:
                increment(self.counts[old["category"]], "redirects")
            elif (
                not old["terminal"]
                and old["frame"] == frame
                and old["loader"] == loader
                and old["category"] == name
                and old["url_key"] == self._url_key(request.get("url"))
            ):
                return
            del self.requests[key]
        if name is None:
            return
        if name in {"plugin_script", "vendor_sdk"}:
            if self.category(params.get("documentURL")) != "plugin_html":
                return
        known = self.frames.get((session, frame))
        if known is not None and known != loader and params.get("type") != "Document":
            self.coverage["loader_gap"] = True
            return
        if len(self.requests) >= MAX_REQUESTS:
            self.coverage["budget_exhausted"] = True
            return
        if not self._frame(session, frame, loader):
            return
        self.requests[key] = {
            "category": name,
            "frame": frame,
            "loader": loader,
            "response": False,
            "terminal": False,
            "cache": False,
            "url_key": self._url_key(request.get("url")),
        }
        increment(self.counts[name], "requests")

    def observe_tree(self, tree, *, session="root"):
        """Snapshot positives only; never use tree entries to repair event joins."""
        if session not in self.sessions:
            self.coverage["late_or_unknown_child"] = True
            return
        pending, visited = [tree], 0
        while pending and visited < MAX_FRAMES:
            node = pending.pop()
            visited += 1
            if self.category(node.get("frame", {}).get("url")) == "plugin_html":
                self.own_frame_current = True
                if len(node.get("resources", [])) > MAX_REQUESTS:
                    self.coverage["budget_exhausted"] = True
                for resource in node.get("resources", [])[:MAX_REQUESTS]:
                    name = self.category(resource.get("url"))
                    if name is not None:
                        self.resources[name] = True
            children = node.get("childFrames", [])
            if len(children) > MAX_FRAMES:
                self.coverage["budget_exhausted"] = True
            pending.extend(children[:MAX_FRAMES])
        if pending:
            self.coverage["budget_exhausted"] = True

    def snapshot(self):
        valid = self.drained and not any(
            self.coverage[key]
            for key in (
                "truncated",
                "cursor_gap",
                "budget_exhausted",
                "unsupported",
                "read_timeout",
                "identity_conflict",
            )
        )
        return {
            "joined_network_evidence": "available" if valid else "withheld_partial_drain",
            "initial_navigation_gap": True,
            "child_coverage": "unknown",
            "coverage": dict(self.coverage),
            "own_frame_seen_in_snapshot": self.own_frame_current,
            "own_frame_navigation_observed": self.own_frame_navigation,
            "resource_tree_seen": dict(self.resources),
            "resources": {
                name: {
                    key: value if valid or key == "requests" else None for key, value in row.items()
                }
                for name, row in self.counts.items()
            },
        }

    def mark_incomplete(self, reason):
        """Collector supplies a fixed outcome only, never a protocol error string."""
        if reason not in {"unsupported", "read_timeout"}:
            raise ValueError("Unknown observation outcome")
        self.coverage[reason] = True
        self.drained = False
