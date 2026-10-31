"""Normal-auth two-session HTTP contract. Never launches a server or browser."""

import argparse
import json

import httpx
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.state import State
from tools.lab import TrafficRecorder, attach_observations
from tools.synthetic_check import ContractFailure, action, content, pair, require
from tools.synthetic_lab import USER, SyntheticJellyfin, attach_fixture_media


class SessionFixture(SyntheticJellyfin):
    def __init__(self, origin, ignore_logout=False):
        super().__init__(origin)
        self.ignore_logout = ignore_logout

    def handle(self, request):
        before = set(self.tokens)
        response = super().handle(request)
        if (
            self.ignore_logout
            and request.method == "POST"
            and request.url.path == "/jellyfin/Sessions/Logout"
            and response.status_code == 204
        ):
            # Trusted in-process counterexample: upstream acknowledges logout but
            # retains its native-media bearer. Portal auth is never bypassed.
            self.tokens.update(before)
        return response


def resources(client, home):
    page = content(client, home)
    browse = action(page, "Synthetic movies")
    movie = next(
        row for row in content(client, browse)["items"] if row["title"] == "Synthetic clip"
    )
    detail = movie["action"]
    resolver = action(content(client, detail), "Try original").removeprefix("video:resolve:")
    response = client.get(resolver).json()["response"]
    require(response["status"] == 200, "source-resolution")
    return {
        "home": home.removeprefix("content:"),
        "browse": browse.removeprefix("content:"),
        "detail": detail.removeprefix("content:"),
        "poster": movie["image"],
        "resolver": resolver,
        "media": response["data"]["url"],
    }


def check(fault=None):
    require(fault in {None, "logout-ignored"}, "invalid-fault")
    origin = "https://localhost:18091"
    settings = Settings(origin, origin + "/jellyfin", session_ttl=120)
    clock = [1000.0]
    fixture = SessionFixture(origin, ignore_logout=fault == "logout-ignored")
    state = State(settings, clock=lambda: clock[0])
    recorder = TrafficRecorder(httpx.MockTransport(fixture.handle))
    app = create_app(settings, transport=recorder, state=state)
    attach_observations(app, settings, recorder)
    # Explicit byte/range fixture, deliberately not a decodable video.
    attach_fixture_media(app, fixture, b"synthetic-session-contract", None)
    checks = []
    with TestClient(app, base_url=origin) as a, TestClient(app, base_url=origin) as b:
        first = resources(a, pair(a, origin))
        second = resources(b, pair(b, origin))
        require(all(first[key] != second[key] for key in first), "distinct-session-authorities")
        checks.append("distinct-session-authorities")
        unknown = a.get(f"/msx/device/{USER}/home.json").json()["response"]
        require(unknown["status"] == 401, "public-id-is-not-authentication")
        checks.append("public-id-is-not-authentication")
        # A full capability URL IS authentication, regardless of browser cookies.
        require(a.get(second["home"]).json()["headline"] == "Jellyfin libraries", "bearer-model")
        checks.append("bearer-url-not-cookie-bound")
        home = a.get(first["home"]).json()
        confirm = content(a, action(home, "Disconnect TV"))
        content(a, action(confirm, "Confirm disconnect"))
        for key in ("home", "browse", "detail", "resolver"):
            require(b.get(first[key]).json()["response"]["status"] == 401, "a-" + key + "-revoked")
            checks.append("a-" + key + "-revoked")
        require(b.get(first["poster"]).status_code == 401, "a-poster-revoked")
        checks.append("a-poster-revoked")
        require(
            b.get(first["media"], headers={"Range": "bytes=0-8"}).status_code == 401,
            "a-media-revoked",
        )
        checks.append("a-media-revoked")
        require(len(fixture.tokens) == 1, "logout-only-revoked-a-token")
        require(
            b.get(second["home"]).json()["headline"] == "Jellyfin libraries", "b-survives-a-logout"
        )
        require(b.get(second["poster"]).status_code == 200, "b-poster-survives-a-logout")
        require(
            b.get(second["resolver"]).json()["response"]["status"] == 200,
            "b-resolver-survives-a-logout",
        )
        require(
            b.get(second["media"], headers={"Range": "bytes=0-8"}).status_code == 206,
            "b-media-survives-a-logout",
        )
        checks.append("b-survives-a-logout")
        recovered = resources(a, pair(a, origin))
        require(
            a.get(recovered["media"], headers={"Range": "bytes=0-8"}).status_code == 206,
            "a-repair-recovery",
        )
        require(b.get(first["home"]).json()["response"]["status"] == 401, "old-a-remains-revoked")
        checks.append("a-repair-recovery")
        clock[0] += settings.session_ttl
        for key in ("home", "browse", "detail", "resolver"):
            require(
                a.get(recovered[key]).json()["response"]["status"] == 401, "portal-absolute-expiry"
            )
        require(a.get(recovered["poster"]).status_code == 401, "portal-absolute-expiry")
        checks.append("portal-absolute-expiry")
        # Expiring portal RAM auth does not revoke the already issued upstream token.
        require(
            a.get(recovered["media"], headers={"Range": "bytes=0-8"}).status_code == 206,
            "native-token-expiry-boundary",
        )
        checks.append("native-token-expiry-boundary")
        return {
            "result": "passed",
            "category": "in-process-session-contract",
            "checks": checks,
            "browser_verified": False,
            "physical_device_verified": False,
            "native_media_revoked_by_portal_expiry": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault", choices=["logout-ignored"])
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.fault), indent=2))
    except ContractFailure as error:
        print(
            json.dumps(
                {"result": "failed", "stage": str(error), "category": "in-process-session-contract"}
            )
        )
        raise SystemExit(1) from None
    except Exception:
        # HTTP failures may contain private URLs. Never print tracebacks or bodies.
        print(
            json.dumps(
                {
                    "result": "failed",
                    "stage": "unexpected-contract-error",
                    "category": "in-process-session-contract",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
