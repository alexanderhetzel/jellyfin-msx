import json

from conftest import code_stage


def test_waiting_retains_activation_and_only_two_remote_actions(portal):
    initial = portal.client.get("/msx/pair.json").json()
    items = initial["pages"][0]["items"]
    controls = [item for item in items if item.get("action")]
    assert all(item.get("action") or item["type"] == "space" for item in items)
    assert [item["title"] for item in controls] == ["Continue after pairing", "Create new code"]
    assert controls[0]["focus"] is True
    waiting = portal.client.get(controls[0]["action"].removeprefix("content:"))
    assert waiting.json()["headline"] == "Waiting for pairing"
    assert waiting.json()["pages"] == initial["pages"]
    assert not portal.fake.requests
    assert waiting.headers["cache-control"] == "no-store, private"
    assert waiting.headers["referrer-policy"] == "no-referrer"


def test_pairing_status_success_requires_normal_authentication(portal):
    secret, device = portal.state.pair()
    path = f"/msx/device/{secret}/pairing.json"
    assert portal.client.get(path).json()["headline"] == "Waiting for pairing"
    fields = code_stage(portal.client, device.code)
    portal.client.post(
        "/pair",
        data={**fields, "username": "viewer", "password": "test-password"},
        headers={"Origin": portal.settings.public_url},
    )
    assert portal.client.get(path).json()["headline"] == "Jellyfin libraries"


def test_expired_or_unknown_status_only_exposes_public_retry(portal):
    secret, device = portal.state.pair()
    code, activation = device.code, device.activation
    portal.now[0] += portal.settings.pairing_ttl
    for grant in (secret, "unknown"):
        response = portal.client.get(f"/msx/device/{grant}/pairing.json")
        page = response.json()
        assert page["headline"] == "Pairing or session expired"
        assert page["items"] == [
            {
                "title": "Create new code",
                "action": "content:https://portal.test/msx/pair.json",
            }
        ]
        assert all(value not in json.dumps(page) for value in (secret, code, activation))
    assert not portal.fake.requests
    # Library access keeps its existing authenticated denial envelope.
    denied = portal.client.get(f"/msx/device/{secret}/home.json").json()
    assert denied["response"]["status"] == 401
    retry = portal.client.get("/msx/pair.json").json()
    assert retry["headline"] == "Pair this TV"
