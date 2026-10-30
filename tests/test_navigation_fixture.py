import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from tools.navigation_fixture import DENIED, EMPTY, EPISODES, LIBRARY, NavigationJellyfin
from tools.public_navigation_fixture import export_pages
from tools.synthetic_check import action, pair


def test_public_graph_reaches_all_episodes_and_preserves_paging(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Unexpected real network")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    pages = export_pages()
    assert pages == export_pages()
    assert pages == json.loads(Path("tests/fixtures/msx-navigation/pages.json").read_text())
    seen, queue = set(), ["init"]
    while queue:
        key = queue.pop()
        if key in seen:
            continue
        seen.add(key)
        page = pages[key]
        for row in page.get("items", []):
            target = row["action"]
            if target.startswith("content:request:interaction:"):
                queue.append(target.rsplit(":", 1)[-1])
            else:
                assert target == "back" or target.startswith(("info:", "video:https://"))
    assert seen == set(pages)
    details = [
        page
        for page in pages.values()
        if page.get("headline", "").startswith("PUBLIC NAVIGATION / Episode")
    ]
    assert {page["headline"] for page in details} == {
        f"PUBLIC NAVIGATION / Episode {i:02d}" for i in range(1, 51)
    }
    assert all(
        any(
            "Year: 2026" in row["title"] and "Type: Episode" in row["title"]
            for row in page["items"]
        )
        for page in details
    )
    browse = pages[action(pages["page2"], "Season 1").rsplit(":", 1)[-1]]
    episode_names = []
    for expected_count in (24, 24, 2):
        rows = [row for row in browse["items"] if row["title"].startswith("Episode ")]
        assert len(rows) == expected_count
        episode_names += [row["title"] for row in rows]
        if expected_count != 2:
            following = pages[action(browse, "Next page").rsplit(":", 1)[-1]]
            previous = pages[action(following, "Previous page").rsplit(":", 1)[-1]]
            assert previous == browse
            browse = following
        else:
            assert not any(row["title"] == "Next page" for row in browse["items"])
    assert episode_names == [f"Episode {i:02d}" for i in range(1, 51)]
    assert pages["page4"]["items"][0]["title"] == "No items available"
    assert pages["page5"]["response"]["status"] == 401
    encoded = json.dumps(pages)
    for marker in (
        "localhost",
        "/msx/device/",
        "ApiKey",
        "csrf",
        "TV code:",
        "synthetic-password",
        "video:resolve:",
    ):
        assert marker not in encoded


def test_normal_private_empty_denial_and_episode_negotiation():
    origin = "https://localhost:18091"
    fixture = NavigationJellyfin(origin)
    app = create_app(
        Settings(origin, origin + "/jellyfin"), transport=httpx.MockTransport(fixture.handle)
    )
    with TestClient(app, base_url=origin) as client:
        home = pair(client, origin).removeprefix("content:")
        private = home.rsplit("/", 1)[0]
        empty = client.get(private + "/browse.json", params={"parent_id": EMPTY})
        assert empty.json()["items"][0]["title"] == "No items available"
        denied = client.get(private + "/browse.json", params={"parent_id": DENIED})
        assert denied.json()["response"]["status"] == 401
        # A folder denial does not destroy the otherwise valid session.
        assert client.get(home).json()["headline"] == "Jellyfin libraries"
        for index in (0, 23, 24, 47, 48, 49):
            detail = client.get(
                private + "/detail.json", params={"item_id": EPISODES[index]}
            ).json()
            play = action(detail, "Try original").removeprefix("video:resolve:")
            resolved = client.get(play).json()["response"]
            assert resolved["status"] == 200
            assert f"/Videos/{EPISODES[index]}/stream.mp4" in resolved["data"]["url"]
        # Revocation denies browsing, details and posters before upstream access.
        client.get(private + "/logout.json")
        for endpoint in (
            f"browse.json?parent_id={LIBRARY}",
            f"detail.json?item_id={EPISODES[0]}",
            f"image/{EPISODES[0]}",
        ):
            response = client.get(private + "/" + endpoint)
            assert response.status_code == 401 or response.json()["response"]["status"] == 401


def test_navigation_transport_requires_authentication():
    fixture = NavigationJellyfin("https://synthetic.test")
    for suffix in (
        "/Users/11111111111111111111111111111111/Views",
        f"/Items/{EPISODES[0]}/Images/Primary",
    ):
        assert (
            fixture.handle(
                httpx.Request("GET", "https://synthetic.test/jellyfin" + suffix)
            ).status_code
            == 401
        )
