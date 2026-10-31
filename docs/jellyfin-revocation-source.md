# Retained original-file response: source investigation

**Source-reviewed / mocked regression tested / device-unverified — 2026-10-31.**
This source-evidence and mocked-observer subset of #32 does not replace or rerun
[retained ten-cell real-server evidence](https://github.com/alexanderhetzel/jellyfin-msx/actions/runs/41132506701)
at harness `dc80fa6`. Draft PR #52 and its strict failing expectation remain
unchanged. The retained exact 12.0.0–12.4.0 root and `/jellyfin` cases passed core
API checks but failed original-file revocation. No complete supported-version
range or acceptance pass is claimed. This subset includes no real-server runner,
image/version manifest or matrix workflow.

## Observation, source and inference

**Retained observation:** after upstream Logout completed, the production client
reported item denial as `PortalError.status == 401`. A fresh independent media
request returned 206 with matching original-prefix bytes. The client normalizes
both upstream HTTP 401 and 403 to that PortalError. The retained probe therefore
does **not** distinguish raw upstream 401 from 403 for the metadata denial.
The original-file status and byte comparison came from the raw media response.

**Confirmed source path:** the official source distinguishes authentication from
an endpoint's authorization requirement. Credential invalidation and a denied
private item do not by themselves establish denial on the original-file path.
The following links pin Jellyfin 12.4 to commit
`83d0d0e7f76e23e2e085c8ff67d28b772d35967d`:

1. [AuthorizationContext](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Server.Implementations/Security/AuthorizationContext.cs)
   reads the modern header's Token, otherwise canonical `ApiKey`, and resolves
   the credential against device/API-key state. Legacy spellings are conditional.
   [AuthService](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Emby.Server.Implementations/HttpServer/Security/AuthService.cs)
   rejects an unresolved supplied credential, but
   [CustomAuthenticationHandler](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Auth/CustomAuthenticationHandler.cs)
   turns that security exception into a failed authentication result. Returning
   that result is distinct from writing a denial response and stopping execution.
2. [API registration](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Server/Extensions/ApiServiceCollectionExtensions.cs)
   sets a default authorization policy, not a fallback policy. Its MVC options
   add no global authorization filter.
   [Startup](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Server/Startup.cs)
   invokes authentication/authorization middleware and maps controllers without
   a global `RequireAuthorization`. Neither the
   [base controller](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/BaseJellyfinApiController.cs)
   nor the original-file actions in
   [VideosController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/VideosController.cs)
   declare an authorization requirement. The container-specific action delegates
   to the same handler. IP/startup middleware adds network/readiness checks,
   not a credential-denial requirement for that action.
3. [StreamingHelpers](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Helpers/StreamingHelpers.cs)
   populates the user only when the principal has a user ID, looks up the item
   without a user parameter, and requests playback sources with a null user.
   The static local-file branch then calls
   [FileStreamResponseHelpers](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Helpers/FileStreamResponseHelpers.cs),
   which returns a physical file result with range processing enabled.
4. The authenticated Logout action in
   [SessionController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/SessionController.cs)
   passes the principal's credential to
   [SessionManager](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Emby.Server.Implementations/Session/SessionManager.cs).
   That implementation deletes the corresponding device record and ends device
   sessions. There is no item-scoped media-ticket revocation in this method.

Jellyfin's server project targets `net10.0`. The official ASP.NET Core 10.0.0
reference, commit `7387de91234d3ef751fa50b3d1bfede4130213ff`, explains the
middleware distinction: [AuthenticationMiddleware](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Security/Authentication/Core/src/AuthenticationMiddleware.cs)
continues after the ordinary handler result;
[AuthorizationPolicy](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Security/Authorization/Core/src/AuthorizationPolicy.cs)
uses the fallback when there is no endpoint authorization metadata;
[AuthorizationOptions](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Security/Authorization/Core/src/AuthorizationOptions.cs)
defaults that fallback to null; and
[AuthorizationMiddleware](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Security/Authorization/Policy/src/AuthorizationMiddleware.cs)
continues when there is no applicable policy. This is a framework source
reference, not a measurement of the exact framework patch inside each image.

**Inference:** this source path supplies a concrete explanation consistent with
the retained original-file result after credential deletion. It does not require
a client header/query mismatch, reused connection or client response cache.
It is not a claim that every endpoint, image build, plugin or reverse proxy has
the same behavior, nor a new live characterization of missing credentials.
No production setting, workaround, media gateway or security bypass follows.

## Version and blob provenance

The official release API was checked on October 31: latest stable remained
[12.4, published October 26](https://github.com/jellyfin/jellyfin/releases/tag/v12.4).
Official tag refs and recursive Git trees were read for all five selected releases:

| Tag | Commit |
| --- | --- |
| v12.0 | `6c073e19ddf604b2369c638716164fdab4c952dc` |
| v12.1 | `ee91c75e777da41a9c4f4855e70adc604fbf2ef8` |
| v12.2 | `ca0f16eb7c195f720a1493ed469a27c4657db0c6` |
| v12.3 | `06de749d435e2d0be0c5119a41f2300fdd7143e5` |
| v12.4 | `83d0d0e7f76e23e2e085c8ff67d28b772d35967d` |

These nine relevant files have identical Git blob IDs in all five trees:

| File (within the linked upstream repository) | Git blob ID |
| --- | --- |
| `Emby.Server.Implementations/HttpServer/Security/AuthService.cs` | `8a79cdebc171a7dda020cbad0f4b1e013cedf4b1` |
| `Jellyfin.Api/Auth/CustomAuthenticationHandler.cs` | `f6f2f59c52c25743155863ccdab3e88cab9cd5ed` |
| `Jellyfin.Api/BaseJellyfinApiController.cs` | `5b4bd0adb0280624ddea0e6a77129e086793d569` |
| `Jellyfin.Api/Controllers/SessionController.cs` | `84c2d90fb1ae9817f5cb6f965e8d5a69332069ac` |
| `Jellyfin.Api/Controllers/VideosController.cs` | `29a92cdb906792a095217728f783e016efc5739e` |
| `Jellyfin.Api/Helpers/FileStreamResponseHelpers.cs` | `d123dbc82e31c053837023f7d232dfe443544931` |
| `Jellyfin.Api/Helpers/StreamingHelpers.cs` | `60c5bb2ef6d3fd81d5cb6f121bb82fb36eca45d7` |
| `Jellyfin.Server.Implementations/Security/AuthorizationContext.cs` | `8657cb7dbbf7bea9cf3b5f27093dd083258cc49c` |
| `Jellyfin.Server/Extensions/ApiServiceCollectionExtensions.cs` | `a4989014810066551081f8315acf9dd3626de6b8` |

`Startup.cs` differs between 12.0 (`1802440dc43a9ac44344d3cc86ed5f224b0fdbc0`)
and 12.1–12.4 (`560a419945dc6a387410692fceccc60672d5e621`); both middleware
pipelines were inspected. `SessionManager.cs` has three blobs: 12.0
`94215bed79e893f8e5506076fb2e623c1200f225`, 12.1
`08e25788674dab9886d685b802e75777162d0040` and 12.2–12.4
`dd71f843e8d2df7cb8902fc070123fd8753bc3a8`. The relevant Logout method bodies
were inspected and have the same credential/device deletion path. These are
source comparisons, not another version matrix run. No upstream implementation
was copied into the application or tests.

## Local correctness milestone and remaining acceptance

The standalone observer in `tools/media_revocation.py` exposes
`verify_revoked_original` for mocked
regressions. It still makes a fresh request, ignores environment proxies, follows
no redirects, bounds the body to 2048 bytes and requires HTTP 401/403. It now
also rejects a nominal denial containing the original prefix anywhere in the
bounded response: denial status alone cannot certify that no bytes escaped.
The standalone helper suppresses HTTP-client request-target logs and replaces
transport/URL/timeout errors with a fixed exception without a chained traceback.
A total 12-second deadline also bounds slow reads. Only numeric status and a
boolean comparison are emitted. The retained HTTP 206
case remains a failure. Tests use MockTransport; none is a server/playback pass.

Remaining #32 acceptance is unchanged: the complete contract must actually pass
before a complete supported range is advertised. This source-only work neither
waives the real failure nor implements #24's persistent authorization cleanup.
#24/#28 must assess local capability invalidation, upstream credential deletion
and already disclosed original-file access as separate boundaries. Any subsequent
live diagnostic needs its separately authorized scope. Normal repository CI uses
mocked tests and the existing application build checks, never the deferred
Jellyfin server matrix. The observer has no CLI or automatic invocation; its
presence creates no live-resource authorization or complete #32 acceptance. Follow
[SECURITY.md](../SECURITY.md) for any security report.
