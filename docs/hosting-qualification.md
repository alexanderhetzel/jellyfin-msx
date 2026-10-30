# TV-reachable hosting qualification

Research date: **2026-10-30**, issue [#3](https://github.com/alexanderhetzel/jellyfin-msx/issues/3).
This is a deployment decision and runbook, not a deployed-service or TV pass.

## Decision

Use the existing single-worker Docker Compose package on an operator-controlled
Linux host with a dedicated DNS name, for example `tv.example.com`, and Caddy
terminating HTTPS at that origin's root. This is the supported **application
deployment shape**, not a claim that a particular host is provisioned. Keep
Jellyfin on Ultra; the TV fetches video directly from its configured HTTPS URL.
No additional TV hardware or media proxy is needed by this design.

**Implemented:** `compose.yaml`, `Dockerfile`, `deploy/Caddyfile` and origin-only
configuration. **Deferred:** provisioning, public DNS, certificate issuance,
production startup and physical TV checks. Those require a separately authorized
rollout. Do not purchase hosting, expose this development machine, configure a
tunnel/router or modify the Ultra account as part of this research.

## Official provider evidence

These are provider-published pages checked on the research date; some are
explicitly labelled unofficial/as-is guides by the provider.

| Concern | Evidence and consequence |
| --- | --- |
| Custom Python service | [Generic installation](https://docs.ultra.cc/unofficial-application-installers/generic-software-installation) permits custom home-directory applications subject to policy, without root/sudo or Docker. This is not managed support for Jellyfin MSX. |
| Python version | [Pyenv guide](https://docs.ultra.cc/unofficial-language-installers/install-python-using-pyenv) describes user-managed interpreters but shows old examples. This project needs Python >=3.12; actual slot availability/build success is unverified. |
| Process supervision | The generic guide documents user systemd units in `~/.config/systemd/user` with `systemctl --user` and restart-on-failure. Login-independent/reboot persistence on a particular slot still needs verification. |
| Ports | [Assigned ports](https://docs.ultra.cc/unofficial-ssh-utilities/assigned-ports-command): use only allocated ports, discover unused ones with `app-ports free`; inspect allocations with `app-ports show`. Do not assume 8090 is available. |
| HTTPS/proxy | The generic guide documents Nginx snippets in `~/.apps/nginx/proxy.d`, an HTTPS application path prefix and `app-nginx restart`. It does not establish a dedicated root origin for this application. |
| Public entry points | [Terms](https://docs.ultra.cc/terms-of-service), effective 2026-08-01, sections 5.5–5.7 require authentication for customer interfaces/resources absent an express exception and written agreement for public services. The [FAQ](https://docs.ultra.cc/getting-started/faq) also excludes unauthenticated public custom services. Our public start/pair/health endpoints cannot be assumed exempt. |
| Resources and support | Terms sections 4.7–4.11 and 5.12–5.13 place custom configuration responsibility on the customer and allow resource enforcement. Keep this project's Ultra transcoding/burn-in prohibition; no conversion experiment is justified here. |
| Environment/secrets | The cited guides do not establish a managed secret-injection facility, private environment visibility or URI-free proxy error logs. Treat these as unknown, not provider guarantees. |

## Why Ultra is not selected for the current portal

Source evidence: `Settings.__post_init__` rejects a path in `MSX_PUBLIC_URL`.
`app.py` builds absolute root paths for pairing, private JSON, images and CSRF
origin checks. Setting `https://portal.example.com/customapp` fails validation;
stripping a prefix only in Nginx leaves generated links outside that prefix.
Uvicorn `--root-path` alone does not change this explicit URL construction.
The host-only MSX setup also discovers `/msx/start.json` at the origin root.

Consequently, Ultra's documented prefix deployment is not a drop-in route for
this version. Do not claim it works by publishing only a static start file,
using an HTTP assigned port, replacing the shared Nginx root location, or placing
an extra password prompt in front of MSX. None qualifies the whole pairing/private
route contract. A future Ultra path would need provider confirmation of the
public bootstrap/authentication policy and logging controls, plus either an
approved dedicated origin or separately implemented and reviewed prefix support.
No provider inquiry or account change was performed in this milestone.

Configuration is not a credential store. The current `.env.example` holds URLs
and policy flags only; Jellyfin credentials enter through the normal companion
form and session tokens live in RAM. Keep real configuration out of Git, restrict
its OS permissions, never print process environments and never put credentials
in service command lines, unit files or proxy URLs. Do not add a password/token
environment variable to make this deployment work.

## Existing Windows development host

The permanent development host can run the locked Python application for isolated
loopback checks. That does not establish TV reachability. `localhost` on the TV
refers to the TV; the local lab deliberately refuses a non-loopback public URL.
A locally trusted certificate on the PC does not establish Philips trust.
No Docker CLI was available on PATH during this qualification; no local Compose
runtime or Windows reboot supervision pass is claimed. Use the repository's
Linux container CI for package evidence and retain this host for development.
Public exposure and Windows service installation are deferred, not required to
complete this research milestone.

## Rollout procedure (separate authorization required)

On the chosen controlled Linux host, use a reviewed revision and a dedicated DNS
record. The operator must control inbound TCP 80/443, persistent Caddy storage
and the complete proxy/CDN logging policy. Ensure the TV and companion device can
reach both the portal and configured Jellyfin HTTPS endpoint. The TV needs a
trusted certificate chain for both; desktop TLS success is insufficient.

1. Copy `.env.example` to a private `.env`, replace only the example domains and
   keep `MSX_ALLOW_HTTP=false` and `MSX_ALLOW_TRANSCODING=false`. Set
   `MSX_PUBLIC_URL=https://tv.example.com` and `MSX_DOMAIN=tv.example.com` to the
   same dedicated host; use the operator's configured Jellyfin URL including its
   existing base path. Never add Jellyfin credentials to this file.
2. Run the following from the repository on an isolated host first, using
   `JELLYFIN_URL=https://jellyfin.invalid` until real integration is authorized:

   ```sh
   docker compose --env-file .env config --quiet
   docker compose --env-file .env build portal
   docker compose --env-file .env run --rm --no-deps https caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   docker compose --env-file .env up -d
   docker compose --env-file .env ps
   ```

   `up` is deployment: do not run it on a production host under research-only
   authorization. Exactly one portal process/container is supported; restarts
   discard pairings and require re-pairing. The portal port must remain private.
   Compose restart policies do not prove recovery after a real host reboot.
3. Before entering credentials, exercise normal and upstream-failure requests
   using a fictional marker such as `/qualification-marker-not-a-secret`.
   Stop only the isolated portal, request that path via HTTPS, and inspect proxy
   and service logs privately. The marker must not occur in URI/request logs.
   For example, after the isolated host has passed normal HTTPS checks:

   ```sh
   docker compose --env-file .env stop portal
   curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://tv.example.com/qualification-marker-not-a-secret
   docker compose --env-file .env logs --no-color https portal
   docker compose --env-file .env start portal
   ```

   Expect a proxy failure (normally 502), not a successful content response.
   Inspect logs locally; do not upload raw output. Restart even if the check
   fails, then recheck health. Apply the same requirement to every intermediary and the
   Jellyfin proxy; empty normal access logs alone do not prove safe error logs.
4. Verify the public endpoints below without disabling TLS validation. Perform
   normal pairing only after these checks pass, using a dedicated non-admin
   Jellyfin account. Direct media URLs expose its user-scoped token to the TV;
   accept that documented tradeoff before rollout. Keep captures/private JSON
   out of reports. Check restart recovery and expiry separately.

## Public reachability checks

On a device using the TV's network, with the deployment's actual origin substituted:

```sh
curl --fail --silent --show-error https://tv.example.com/healthz
curl --fail --silent --show-error https://tv.example.com/msx/start.json
```

Do not use `-k`, follow redirects into unrelated hosts, or run these examples
against capability URLs. Expect HTTP 200 and JSON: health contains `status: "ok"`,
`version: "0.1.0"` and `device_verified: false`;
start contains `name: "Jellyfin MSX"`, version `0.1.0`, and
`parameter: "content:https://tv.example.com/msx/pair.json"`. Verify the actual
origin, HTTPS scheme and root path. A login page, prefix rewrite, certificate
error or HTML response is a failure. `/healthz` checks the process, not Jellyfin
authentication, video delivery or the TV decoder. Start JSON contains no code or
capability; `/msx/pair.json` does, so do not print or archive that response.

## Host-only MSX setup

The official [MSX setup API](https://msx.benzac.de/wiki/index.php?title=Setup_Start_Parameter)
defines discovery at `https://{SERVER}/msx/start.json` with the security lock on
(HTTPS supported since MSX 0.1.88). Use the official installed application on the
TV; use the official hosted runtime in the integrated browser for desktop checks.
Never copy or host MSX runtime code.

1. Open **Settings → Start Parameter → Setup** in MSX.
2. Enter **`tv.example.com`** (replace with the actual dedicated hostname).
   Enter the host only: no `https://`, `/msx/start.json`, application prefix or
   private capability. Enable the **security lock / HTTPS** before loading.
3. Confirm the displayed **Jellyfin MSX** start parameter. It loads the public
   start object and then the absolute HTTPS pairing content URL.
4. Open the displayed companion `/pair` address on a browser, enter the displayed
   TV code and Jellyfin credentials through the normal form, then select
   **Continue after pairing** on TV. Never publish the code or private actions.

All subsequent JSON/image/media URLs must remain HTTPS. DNS/health checks from a
PC on the same network are preliminary only. On the actual TV record successful
start discovery/pairing or the exact sanitized failure, firmware and MSX version
in [device results](device-test-results.md). Use the [device checklist](device-test-checklist.md)
for playback, audio and remote tests. Those are **device-unverified** here.

## Acceptance boundary

The research milestone can be merged after review and checks. Issue #3 remains
open until isolated packaging evidence and actual rollout's TV HTTPS/start-JSON
verification are recorded against the chosen host. A green CI job proves only
what it executes; it does not prove certificate issuance, URI-free error paths,
network reachability or physical playback. See [status](status.md) for actual
commands/results; none of the rollout steps above is a claimed execution record.
