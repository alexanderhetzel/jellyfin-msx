"""Explicit disposable REAL-server contract check; never collected by pytest.

Only digest-allowlisted official images, synthetic local files and isolated Docker
bridge addresses are accepted. Credentials/responses stay in RAM; output is allowlisted.
"""

import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.jellyfin import Jellyfin
from jellyfin_msx.playback import resolve
from jellyfin_msx.state import Device, State

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = json.loads((ROOT / "tools/jellyfin_versions.json").read_text())


class ContractFailure(Exception):
    """Only fixed assertion messages and sanitized numeric diagnostics."""


def require(condition, label):
    if not condition:
        raise ContractFailure(label)


def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=180, check=False
    )
    if check and result.returncode:
        categories = {
            "manifest unknown": "manifest unavailable",
            "unauthorized": "registry authorization denied",
            "toomanyrequests": "registry rate limit",
            "not found": "resource unavailable",
            "no matching manifest": "platform unavailable",
            "network is internal": "internal network limitation",
            "cannot assign requested address": "port binding unavailable",
            "permission denied": "permission denied",
        }
        category = next(
            (v for k, v in categories.items() if k in result.stderr.lower()),
            "unclassified; output withheld",
        )
        raise ContractFailure(f"docker {args[0]} failed (exit {result.returncode}; {category})")
    return result.stdout.strip()


async def probe(base, version):
    settings = Settings(public_url="http://127.0.0.1:18090", jellyfin_url=base, allow_http=True)
    jf = Jellyfin(settings)
    admin = Device(time.monotonic() + 600)
    stage = "readiness"
    async with httpx.AsyncClient(timeout=12, follow_redirects=False, trust_env=False) as client:

        async def request(method, path, device=admin, expected=(200, 204), **kwargs):
            response = await client.request(
                method, base + path, headers=jf.headers(device), **kwargs
            )
            require(
                response.status_code in expected, f"{stage}: unexpected HTTP {response.status_code}"
            )
            return response

        try:
            deadline = time.monotonic() + 120
            while True:
                try:
                    response = await request("GET", "/System/Info/Public")
                    if "Version" in response.json():
                        break
                except (httpx.RequestError, ContractFailure):
                    pass
                require(time.monotonic() < deadline, "readiness deadline exceeded")
                await asyncio.sleep(1)
            observed_version = response.json()["Version"]
            require(
                isinstance(observed_version, str)
                and re.fullmatch(r"[0-9.]{1,20}", observed_version),
                "invalid server version",
            )
            print(json.dumps({"server_version": observed_version}), flush=True)
            require(observed_version == version + ".0", "unexpected server version")
            stage = "regular startup wizard"
            await request("GET", "/Startup/User")
            password = secrets.token_urlsafe(32)
            await request(
                "POST", "/Startup/User", json={"Name": "fixture-admin", "Password": password}
            )
            await request("POST", "/Startup/Complete")
            stage = "normal authentication"
            admin.user_id, admin.token = await jf.authenticate(admin, "fixture-admin", password)
            await request(
                "GET", "/Startup/User", device=Device(time.monotonic() + 600), expected=(401, 403)
            )
            await request(
                "POST",
                "/Users/AuthenticateByName",
                device=Device(time.monotonic() + 600),
                json={"Username": "fixture-admin", "Pw": secrets.token_urlsafe(32)},
                expected=(401, 403),
            )
            users = []
            for name, allowed in (("fixture-viewer", True), ("fixture-denied", False)):
                password = secrets.token_urlsafe(32)
                created = (
                    await request("POST", "/Users/New", json={"Name": name, "Password": password})
                ).json()
                policy = created["Policy"]
                policy.update(
                    IsAdministrator=False,
                    EnableAllFolders=allowed,
                    EnabledFolders=[],
                    EnableMediaPlayback=True,
                    EnableVideoPlaybackTranscoding=False,
                    EnableAudioPlaybackTranscoding=False,
                    EnablePlaybackRemuxing=False,
                )
                await request("POST", f"/Users/{created['Id']}/Policy", json=policy)
                device = Device(time.monotonic() + 600)
                device.user_id, device.token = await jf.authenticate(device, name, password)
                users.append(device)
            viewer, denied = users
            stage = "isolated library scan"
            await request(
                "POST",
                "/Library/VirtualFolders",
                params={
                    "name": "Synthetic",
                    "collectionType": "movies",
                    "paths": "/media",
                    "refreshLibrary": "true",
                },
                json={
                    "LibraryOptions": {
                        "EnableRealtimeMonitor": False,
                        "EnableInternetProviders": False,
                        "EnableAutomaticSeriesGrouping": False,
                        "TypeOptions": [
                            {"Type": "Movie", "MetadataFetchers": [], "ImageFetchers": []}
                        ],
                    }
                },
            )
            deadline = time.monotonic() + 120
            while True:
                items = (
                    await request(
                        "GET",
                        f"/Users/{viewer.user_id}/Items",
                        device=viewer,
                        params={
                            "Recursive": "true",
                            "IncludeItemTypes": "Movie",
                            "Fields": "MediaSources",
                        },
                    )
                ).json()["Items"]
                if len(items) == 1 and items[0].get("MediaSources"):
                    break
                require(time.monotonic() < deadline, "library scan deadline exceeded")
                await asyncio.sleep(1)
            item_id = items[0]["Id"]
            stage = "private item and nullable metadata"
            item = await jf.item(viewer, item_id)
            require(
                not item.get("Overview") and not item.get("ProductionYear"),
                "minimal metadata fixture changed",
            )
            require(item["MediaSources"][0]["MediaStreams"], "missing probed stream metadata")
            metadata_shapes = {
                key: "absent" if key not in item else "null" if item[key] is None else "present"
                for key in ("Overview", "ProductionYear", "CommunityRating", "PremiereDate")
            }
            anonymous = Device(time.monotonic() + 600, user_id=viewer.user_id)
            for device in (anonymous, denied):
                try:
                    await jf.item(device, item_id)
                except PortalError as error:
                    require(error.status in (401, 403, 404), "unexpected item denial")
                else:
                    raise ContractFailure("private item authorization was not denied")
            try:
                await resolve(jf, denied, item_id, False, -1)
            except PortalError as error:
                require(error.status in (401, 403, 404), "unexpected playback denial")
            else:
                raise ContractFailure("restricted playback permitted")
            stage = "authenticated portal images"
            state = State(settings)
            capability, paired = state.pair()
            paired.user_id, paired.token = viewer.user_id, viewer.token
            app = create_app(settings, state=state)
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app), base_url=settings.public_url
                ) as portal,
            ):
                # The upstream image GET may be public. The portal must enforce
                # its own capability AND the signed-in user's item permission.
                image_path = f"/msx/device/{capability}/image/{item_id}"
                image = await portal.get(image_path)
                require(
                    image.status_code == 200 and image.headers["content-type"].startswith("image/"),
                    "portal image fetch failed",
                )
                require(
                    (await portal.get(f"/msx/device/invalid/image/{item_id}")).status_code == 401,
                    "anonymous portal image permitted",
                )
                paired.user_id, paired.token = denied.user_id, denied.token
                require(
                    (await portal.get(image_path)).status_code in (401, 403, 404),
                    "restricted portal image permitted",
                )
            stage = "Direct Play and canonical ApiKey"
            url, diagnostic = await resolve(jf, viewer, item_id, False, -1)
            parsed = urlsplit(url)
            base_path = urlsplit(base).path
            require(
                parsed.path == f"{base_path}/Videos/{item_id}/stream.mp4",
                "generated media base path changed",
            )
            credentials = [
                (k, v)
                for k, v in parse_qsl(parsed.query)
                if k.lower() in {"apikey", "api_key", "token"}
            ]
            require(credentials == [("ApiKey", viewer.token)], "canonical media credential changed")
            require(
                diagnostic["mode"] == "DirectPlay" and not diagnostic["transcoding_allowed"],
                "Direct Play not negotiated",
            )
            # Stream instead of buffering a potentially changed file. Never log URL.
            async with client.stream("GET", url, headers={"Range": "bytes=0-1023"}) as media:
                require(media.status_code == 206, "canonical ApiKey range request failed")
                data = b""
                async for chunk in media.aiter_bytes():
                    data += chunk
                    require(len(data) <= 1024, "range response exceeded bound")
                fixture = ROOT / "tests/fixtures/msx-public/synthetic.mp4"
                require(data == fixture.read_bytes()[:1024], "original file bytes differ")
            print(
                json.dumps(
                    {
                        "version": observed_version,
                        "base_path": urlsplit(base).path or "/",
                        "core_api_checks": "passed",
                        "metadata_shapes": metadata_shapes,
                    }
                ),
                flush=True,
            )
            stage = "logout revocation"
            await jf.logout(viewer)
            try:
                await jf.item(viewer, item_id)
            except PortalError as error:
                require(error.status == 401, "unexpected logout denial")
            else:
                raise ContractFailure("logged-out session remained authorized")
            # Use a new transport/connection and explicitly request revalidation;
            # neither a prior authorized connection nor a cached body is evidence.
            async with httpx.AsyncClient(
                timeout=12, follow_redirects=False, trust_env=False
            ) as fresh:
                async with fresh.stream(
                    "GET", url, headers={"Range": "bytes=0-1023", "Cache-Control": "no-cache"}
                ) as media:
                    received = b""
                    async for chunk in media.aiter_bytes():
                        received += chunk
                        require(len(received) <= 2048, "revoked range body exceeds bound")
                    print(
                        json.dumps(
                            {
                                "logout_media_status": media.status_code,
                                "matches_original_prefix": received == fixture.read_bytes()[:1024],
                            }
                        ),
                        flush=True,
                    )
                    require(
                        media.status_code in (401, 403),
                        f"fresh logged-out media HTTP {media.status_code}",
                    )
            return {
                "version": version + ".0",
                "base_path": "/jellyfin" if base.endswith("/jellyfin") else "/",
                "result": "passed",
                "metadata_shapes": metadata_shapes,
                "checks": [
                    "regular-auth",
                    "wrong-password-denied",
                    "private-item-denied",
                    "minimal-metadata",
                    "portal-image-access-and-denial",
                    "DirectPlay-no-conversion",
                    "ApiKey-original-range",
                    "logout-revoked",
                ],
            }
        except Exception as error:
            # Exception strings, response bodies and tracebacks can contain credentials.
            detail = (
                str(error)
                if isinstance(error, ContractFailure)
                else f"HTTP {error.status}"
                if isinstance(error, PortalError)
                else type(error).__name__
            )
            raise ContractFailure(f"contract failed at {stage}: {detail}") from None
        finally:
            await jf.client.aclose()


def run(version):
    require(os.name == "posix" and shutil.which("docker"), "Linux and Docker are required")
    image = f"jellyfin/jellyfin:{version}@{VERSIONS[version]}"
    owner = os.environ.get("CONTRACT_OWNER", secrets.token_hex(16))
    docker("pull", image)
    failed = False
    for base_path in ("", "/jellyfin"):
        name = "msx-contract-" + secrets.token_hex(8)
        with tempfile.TemporaryDirectory(prefix="msx-contract-") as directory:
            root = Path(directory)
            media = root / "media" / "Synthetic"
            media.mkdir(parents=True)
            shutil.copyfile(
                ROOT / "tests/fixtures/msx-public/synthetic.mp4", media / "Synthetic.mp4"
            )
            shutil.copyfile(ROOT / "tests/fixtures/msx-public/poster.png", media / "poster.png")
            (media / "movie.nfo").write_text(
                "<movie><title>Synthetic</title><lockdata>true</lockdata></movie>"
            )
            config = root / "config"
            (config / "config").mkdir(parents=True)
            (root / "cache").mkdir()
            (config / "config/network.xml").write_text(
                f"<NetworkConfiguration><BaseUrl>{base_path}</BaseUrl><EnableUPnP>false</EnableUPnP><EnableIPv6>false</EnableIPv6></NetworkConfiguration>"
            )
            # Upstream logout can log tokens. Disable every sink before startup.
            (config / "config/logging.default.json").write_text(
                json.dumps({"Serilog": {"MinimumLevel": {"Default": "Fatal"}, "WriteTo": []}})
            )
            docker(
                "network", "create", "--internal", "--label", f"msx-contract.owner={owner}", name
            )
            try:
                docker(
                    "run",
                    "--detach",
                    "--name",
                    name,
                    "--label",
                    f"msx-contract.owner={owner}",
                    "--network",
                    name,
                    "--user",
                    f"{os.getuid()}:{os.getgid()}",
                    "--memory",
                    "1g",
                    "--cpus",
                    "2",
                    "--log-driver",
                    "none",
                    "--volume",
                    f"{config}:/config",
                    "--volume",
                    f"{root / 'cache'}:/cache",
                    "--volume",
                    f"{root / 'media'}:/media:ro",
                    image,
                )
                address = docker(
                    "inspect",
                    "--format",
                    "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                    name,
                )
                require(ipaddress.ip_address(address).is_private, "invalid isolated bridge address")
                try:
                    result = asyncio.run(probe(f"http://{address}:8096{base_path}", version))
                except ContractFailure as error:
                    failed = True
                    result = {
                        "version": version + ".0",
                        "base_path": base_path or "/",
                        "result": "failed",
                        "stage": str(error),
                    }
                result.update(
                    image_digest=VERSIONS[version],
                    fixture_sha256=hashlib.sha256(
                        (media / "Synthetic.mp4").read_bytes()
                    ).hexdigest(),
                )
                print(json.dumps(result), flush=True)
            finally:
                # Report failed cleanup as a failed check; never remove other resources.
                try:
                    docker("rm", "--force", "--volumes", name)
                finally:
                    docker("network", "rm", name)
    require(not failed, "one or more isolated contracts failed; no complete version pass")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS, required=True)
    args = parser.parse_args()
    try:
        run(args.version)
    except Exception as error:
        # Only our fixed messages are safe; never print arbitrary exception text.
        print("Isolated Jellyfin contract failed; credentials and responses withheld.", flush=True)
        if isinstance(error, ContractFailure):
            print(str(error), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
