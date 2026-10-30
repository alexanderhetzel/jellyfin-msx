# Temporary synthetic HTTPS preparation — issue #9

**Implemented / automated-tested / device-unverified:** a local-only preparation
milestone. No public tunnel was started, and no new hosted-MSX integration pass
is claimed. Activation is a separate new public-exposure decision; preparing,
reviewing or merging this tool does not grant that approval.

## Exact proposed exposure

After explicit approval, `tools.synthetic_https` can expose one isolated synthetic
application through a temporary Cloudflare Quick Tunnel. The backend binds only
to **127.0.0.1:18092**; Cloudflare provides a random HTTPS `trycloudflare.com`
origin. Anyone knowing that origin can reach the synthetic service. Cloudflare
terminates HTTPS and carries synthetic request bodies/URLs; this setup must never
receive real credentials, media, renewal records or Jellyfin tokens.

No account/domain purchase, named tunnel, global service, DNS/router/firewall
change, certificate/trust import, browser warning bypass or production deployment
is part of the proposal. No email/authentication interstitial is added: MSX is a
non-interactive API/media client. Application pairing still uses the normal
two-stage production CSRF/code/credential flow with the public synthetic fixture
credentials, random expiring capabilities and RAM-only synthetic login tokens.

Cloudflare's [Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
states that the address is temporary, stops when its process stops, has no uptime
guarantee, changes on restart, is limited to 200 in-flight requests and does not
support SSE. This is development delivery, not a production hosting choice.
Actual Cloudflare/MSX compatibility and public startup remain **pending**.

## Reviewed binary and commands

Pinned official [release 2026.10.7](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.7),
published 2026-10-30, asset `cloudflared-windows-amd64.exe`, 55,390,512 bytes:

```text
SHA256 2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343
```

The GitHub asset digest was re-read before downloading into the ignored local
`.lab/tools/cloudflared/cloudflared.exe`, and the downloaded bytes matched it.
Only `--version` and `tunnel --help` were executed; they reported 2026.10.7 and
confirmed the reviewed flags. No service was installed and no tunnel command ran.
The supervisor rechecks the pinned binary hash before activation and again in its
dedicated helper. It disables auto-update; changing the binary requires review.

From the repository root, safe offline preflight (also the default mode):

```sh
uv sync --locked --extra dev --group build
uv run python -m tools.synthetic_https --check
```

It checks binary/committed clip hashes, prints only fixed preparation metadata,
and reports `approval_required: true`, `tunnel_started: false`. It never spawns
a helper, downloads anything, reads operator configuration or contacts a service.

**Proposed command after approval, not executed during preparation:**

```sh
uv run python -m tools.synthetic_https --activate-public-synthetic --seconds 900
```

Only that explicit mode activates the supervisor. Activation is Windows-only;
other platforms fail closed pending equivalent reviewed process containment.
`--cloudflared` may name the already verified executable in another local path;
the pinned hash remains mandatory. The 900-second maximum cannot be increased.
Successful local and verified-HTTPS relay readiness prints only the assigned public origin, never a TV
code, capability, activation link, credential, media URL or third-party log line.
Open its `/__lab/` dashboard in connected Chrome and use its official-MS​​X launch
link. Treat the assigned origin as transient test access information, not a
production address. Do not publish session URLs/captures or copy them to githack.

Stop from another terminal in the same checkout:

```sh
uv run python -m tools.synthetic_https --stop
```

This requests shutdown through the run's local control file; it does not search
for or kill unrelated processes. Ctrl+C in the supervising session also stops it.
The maximum lifetime and helper-failure paths stop it automatically. The local
control directory `.lab/synthetic-https/` contains only non-secret owned PIDs and
a stop marker. No tokens, origins, raw logs or operator secrets are stored there.
If abrupt supervisor termination leaves stale PID state, verify those exact owned
processes are gone before removing that local stale control directory. A new run
refuses an existing directory rather than replacing another run's state.

## Isolation and supervision

- The existing operator `build_lab` loopback/transcoding guards remain intact.
  Its observation attachment is separated from application/transport creation.
  `build_public_synthetic_lab` is a different opt-in factory that accepts only a
  validated, origin-only HTTPS `*.trycloudflare.com` address. Request Host or
  forwarded headers never configure it; unrelated Host values are rejected.
- The factory constructs its own explicit Settings: same-origin `/jellyfin`,
  strict `MockTransport` without a network fallback, no persistent authorization,
  at most 32 in-memory device states, 15-minute sessions, and conversion disabled.
  It never calls environment/dotenv/credential-store readers. No real-server URL
  or arbitrary media path can be supplied to this public factory.
- Only the existing committed generated clip is admitted by its fixed SHA256
  and snapshotted into RAM before serving. Later path/symlink/file changes cannot
  expose another file. The synthetic-only endpoint supports full/HEAD and bounded
  single/suffix byte ranges after token/source validation. It is not a production
  proxy or a filesystem mount. Authenticated posters use the existing fixture.
- The backend exclusively reserves its own loopback listener **before** the tunnel
  helper may start. An occupied port aborts before any tunnel helper. It waits for
  a validated fixed origin on a private parent pipe before creating the application;
  no unconfigured application or unrelated listener is forwarded.
- All helpers use argument arrays without a shell and `CREATE_NO_WINDOW` on
  Windows. A private empty configuration, isolated HOME/USERPROFILE and small
  environment allowlist exclude operator Cloudflare/Jellyfin/MSX/proxy settings.
  No global configuration is modified. Metrics bind only to 127.0.0.1 with an
  ephemeral port; management diagnostics and automatic updates are disabled.
- The reviewed vendor arguments are `tunnel --config <owned-empty.yml>
  --no-autoupdate --url http://127.0.0.1:18092 --metrics 127.0.0.1:0 --loglevel info
  --management-diagnostics=false`. The pinned upstream [dispatch source](https://github.com/cloudflare/cloudflared/blob/2026.10.7/cmd/cloudflared/tunnel/cmd.go)
  selects Quick Tunnel from an explicit `--url`; the empty config avoids reading
  an existing operator config. No token, logfile or TLS-verification bypass flag.
- Raw vendor output is consumed only through a bounded 4096-byte line buffer,
  discarded, and reduced to one strictly validated bare assigned origin. Request
  URLs, query strings, overlong/malformed lines and unrelated origins cannot be
  printed by that channel. Backend access/error logs are disabled in its dedicated
  process; unexpected launcher exceptions become fixed error codes. Provider-side
  handling is outside this local log-redaction claim.
- Startup has a 45-second deadline with bounded local/verified-HTTPS relay health
  checks (two-second public request timeout; no redirects or environment proxy).
  Health readiness is not a successful MSX/private application test. Total parent
  lifetime is at most 900 seconds, plus bounded owned-process shutdown.
  Parent-pipe EOF watchdogs stop helpers on parent loss. The dedicated Windows
  tunnel wrapper enters a non-breakaway `KILL_ON_JOB_CLOSE` Job Object **before**
  starting the vendor child; abrupt wrapper termination closes that handle and
  kills descendants. [Microsoft's job documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
  and [extended limit structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
  define this containment. Failure to configure it aborts before a vendor child.
- On normal end, stop request, timeout, interruption or helper failure, the
  supervisor closes only its owned helper pipes, waits, then terminates/kills only
  those exact processes if necessary. Helpers stop the exact owned vendor child.
  They stop before their temporary cwd/config is removed. No process-name scan or
  broad kill is used. The Job Object adds containment beyond graceful cleanup;
  this is not a guarantee against OS/power failure or provider availability.

The binary, temporary control/config files, tools and test media remain excluded
from production wheel/context/image artifacts by the existing tracked-file
allowlists. Production source/dependencies/authentication policy are unchanged.

## Preparation evidence and remaining gate

Windows / bundled Python 3.12.14: locked dev/build sync passed. The new focused
tests use normal synthetic authentication, real owned **local-only** backend
startup and fake Python tunnel helpers. They cover unsafe origins/opt-in, retained
operator loopback guards, no environment/network fallback, secure cookie/CSRF,
request-host spoofing, immutable reviewed media, ranges, revocation/redaction,
occupied-port refusal before tunnel, bounded log extraction, preflight with no
spawns, readiness timeout, helper exit, stop request, max lifetime and interruption.
A real Windows owned-wrapper/child test forcibly terminated the wrapper and
confirmed the Job Object terminated its harmless Python child. No real vendor
tunnel was used by tests. The first local backend test expected LF and failed on
Windows CRLF; correcting that test assumption made the check pass.

Windows / Python 3.12.14 results: `uv run pytest -W error` **391 passed / 1 POSIX
skip**, without warnings; `uv run ruff check .` passed; `uv run ruff format
--check .` **83 files** passed; `git diff --check` passed. Offline wheel build
with the explicit `.venv/Scripts/python.exe`, locked build group and no isolation
passed; `tools/package_check.py wheel` verified the exact tracked-source/license/
template allowlist and helper exclusion. The ordinary synthetic HTTP command
also passed. These are local/fake-helper checks, not a public tunnel test.

Public tunnel allocation, Cloudflare-to-loopback delivery, HTTPS companion cookies,
official hosted MSX normal private pairing/navigation/source/playback, dynamic
fault/recovery/logout and multi-session checks remain **unexecuted**. They require
the new exposure decision first; existing static public-player and local HTTP
evidence does not pass them. Issue #9 remains open; real-server and final physical
Philips gates remain separate. No new request for TV availability or general
project permissions is needed.
