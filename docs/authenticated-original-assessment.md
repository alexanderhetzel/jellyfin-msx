# Authenticated original-file route assessment — issue #32

**Source-reviewed / implemented default-off candidate / mock-tested /
device-unverified — 2026-10-31.** This evaluates a new delivery hypothesis and
records its restricted software candidate. It does not enable deployment,
rerun the real matrix, or replace the retained `/Videos` post-logout failure.
There is no complete supported-version range or new revocation/playback pass.

## Concrete route comparison

All source links below pin official Jellyfin 12.4 commit
`83d0d0e7f76e23e2e085c8ff67d28b772d35967d`.

| Boundary | Current `/Videos` original | `/Items/{id}/File` candidate | `/Items/{id}/Download` |
| --- | --- | --- | --- |
| Declared route authorization | None on original-file actions | `[Authorize]` | `Policies.Download` |
| Selection | Parent item plus media-source selector | URL item's `Path`; no media-source selector | URL item's `Path`; no media-source selector |
| Item lookup | Streaming helper's unscoped item/source lookup | Current-principal scoped lookup | Current-user scoped lookup |
| Response | Static physical file/range | Physical file/range, inferred MIME, no download filename | Physical file/range plus attachment filename |
| Download permission | Not a prerequisite for this client | No explicit download requirement | Download policy and `item.CanDownload(user)` |
| Playback-enabled bit on each native request | Not established | Not explicitly checked | Download is a distinct permission |
| Logout denial | Retained old path failed | Source-supported hypothesis; untested | Source-supported hypothesis; untested |

[LibraryController.GetFile/GetDownload](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/LibraryController.cs)
establishes the `/File` and `/Download` distinctions. Both resolve symlinks for
file-protocol paths. Download also records download activity. Neither method
binds an added `MediaSourceId` query to selection: using the primary item would
serve its path, even when details selected a different cut. A query spelling or
GUID shape cannot fix that.

[DefaultAuthorizationHandler](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Auth/DefaultAuthorizationPolicy/DefaultAuthorizationHandler.cs)
checks remote access and, for ordinary users, parental schedule; API keys and
administrators have distinct branches. This client must keep user-session
credentials, never substitute a server API key. The
[download permission handler](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Auth/UserPermissionPolicy/UserPermissionHandler.cs)
and action's `CanDownload(user)` must not be conflated with playback permission.
No server permission is widened to make an endpoint work.

## Exact stored-version identity: conditional source proof

[BaseItem.GetVersionInfo](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/MediaBrowser.Controller/Entities/BaseItem.cs)
sets a generated static media source's ID from its **version item's** ID and its
path, container, size, runtime and streams from that same item.
[Video.GetAllItemsForMediaSources](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/MediaBrowser.Controller/Entities/Video.cs)
enumerates this item, linked alternatives, a primary when applicable, and local
alternatives, deduplicated by item ID. Therefore the exact selected version can
differ from the parent shown in details. The
[media-source manager](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Emby.Server.Implementations/Library/MediaSourceManager.cs)
filters GUID-valued static alternate sources through a user-scoped lookup.

This identity proof does not extend to channel/dynamic provider sources simply
because their ID happens to parse as a GUID. The source manager also adds dynamic
provider results; its key-prefix helper changes opening/live tokens, not every
provider's media-source ID. JSON shape alone is not independent evidence of
stock static-library provenance.

The bounded mock-only prototype in `tools/original_file_candidate.py` therefore
has an explicit stock static-library provenance precondition. It performs fresh
parent and version lookups, exact source membership and self-source checks,
path/container/size/runtime equality, strict playback access, conservative local
stream admission and a source-pinned conversion-disabled PlaybackInfo request.
Both metadata snapshots are rechecked after negotiation. It returns an immutable
snapshot candidate containing IDs/container only: no URL, route replacement or
media fetch. There is no CLI or production import. Top-level item DTO `PartCount` is treated
according to pinned DtoService: null/omitted for a single file, populated from
AdditionalParts only when stacked. Explicit malformed/stacked counts are rejected.
Stock channel provenance is checked using absent/null SourceType and ChannelId;
the [nullable GUID converter](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/src/Jellyfin.Extensions/Json/Converters/JsonNullableGuidConverter.cs)
writes empty GUIDs as null. Malformed falsy values are not treated as null.

Unknown metadata, missing/ambiguous membership, changed identity/extent, denied
or revoked selected-version access, remote/opening/live/header-dependent sources,
disc or placeholder sources and policy denial are rejected without fallback to
the old route. Equality is conservative: path substitution or symlink differences
cannot be normalized into assumed permission. File mutation between requests,
plugin provenance and atomic byte identity remain outside this metadata proof.
The final parent and version reads are sequential snapshots: a parent permission
change during the last version await is still possible. This does not create a
transaction, freeze server policy, or change later native request semantics.

## Playback permission is separate from visibility

[LibraryManager.GetItemById(id,user)](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Emby.Server.Implementations/Library/LibraryManager.cs)
checks item visibility; that is not a call to `GetPlayAccess`. In
[BaseItem](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/MediaBrowser.Controller/Entities/BaseItem.cs),
`GetPlayAccess(user)` separately maps disabled `EnableMediaPlayback` to `None`.
[UserLibraryController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/UserLibraryController.cs)
uses default all-field DTO options for item detail, and
[DtoService](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Emby.Server.Implementations/Dto/DtoService.cs)
populates PlayAccess from that method. The pinned
[enum](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/MediaBrowser.Model/Library/PlayAccess.cs)
defines only `Full` and `None`; `NavigationOnly` is an unknown-contract test value,
not a documented permission state.

The actual current resolver was challenged using MockTransport-only fresh item
metadata with `None` and the unknown `NavigationOnly` value while negotiation
otherwise allowed Direct Play. Both desired-denial regression cases were red:
the resolver emitted a result instead of raising, because it did not inspect
PlayAccess. This was a local admission counterexample, not a server API observation.
The separately scoped software guard now requires exact `Full` after fresh item
type validation and before source selection/PlaybackInfo. Documented `None`
returns fixed 403; absent/null/unknown/wrong-type values return fixed 502 without
negotiation or a media URL. There is no backward-compatibility assumption of Full.
Synthetic adapters explicitly declare their assumed permission; production
metadata is never filled in. This changes URL-issuance admission only and leaves
the current media route unchanged. It is not a `/File` delivery implementation.

An issuance guard must require exact `Full` from fresh authorized metadata and
reject absent/null/unknown values rather than inventing a permission. It can
close a local admission gap and prevent new URLs while playback is denied. It
does not make `/File` recheck that bit for a previously disclosed native URL.
Compared with the current original route, `/File` adds credential authentication
and scoped item visibility; it does not newly promise per-request playback-bit
revocation. Those allowed-request sets and timing boundaries must be evaluated
separately, not dismissed as equivalent or declared universally fixed.

## Falsifiable minimum before a production route decision

- Independently review stock static-source provenance and exact selected-version
  membership/self-source/path/extent checks, with no fallback to a primary cut.
- Admit only fresh `PlayAccess == Full`, retain eligible Direct Play/source-pinned
  PlaybackInfo and disabled conversion; do not use authentication to bypass a ban.
- Restrict to actual local video files. Exclude dynamic/channel/opening/remote,
  discs, stacked/special sources and unresolved path substitution. Preserve the
  1920x1080 client boundary; do not proxy or enable conversion.
- Under a separately authorized isolated run, compare actual bytes/ranges and
  content type for two distinct cuts, linked and local alternatives, symlink/path
  cases, denied membership, metadata mutation, and missing/invalid/revoked user
  credentials. `/File` logout tests are a **new** case; old `/Videos` failures stay.
- Retain configured origin/base-path and no-redirect boundaries, canonical ApiKey,
  safe logs, native seek/resume observations and policy-change timing limits.

Other inspected direct routes do not remove these constraints: the video static
route is the retained failure; audio routes are not a video-original replacement;
PlaybackInfo is metadata/negotiation rather than a byte route. HLS conversion,
remote tunneling, global authentication settings, extra download permissions and
a default video proxy are outside the decision. No server/browser/media request
has run during this source inquiry, and no production routing change is made.

## Cross-version source feasibility — retained exact releases

This is a source comparison, not a supported runtime range. Official Git trees
at the five commits below contain the **same** `LibraryController.cs`
[blob `39a6fbace870783b22f41ed964e55620a96fe78b`](https://api.github.com/repos/jellyfin/jellyfin/git/blobs/39a6fbace870783b22f41ed964e55620a96fe78b), including `/File` authorization,
scoped lookup, symlink handling, MIME and range-enabled physical response.
`Video.cs` is also identical: `e2f91aa04a437af8e883350e44fb0aae8f063cf5`.
The default authorization handler is identical:
`6b80d537fbb1f38c641c506a8f1da6fbc44c09e5`. Its policy scope, including the
post-issuance playback-bit limitation, remains as described above.

| Exact release source | Commit | BaseItem blob | MediaSourceManager blob |
| --- | --- | --- | --- |
| [12.0.0](https://github.com/jellyfin/jellyfin/tree/6c073e19ddf604b2369c638716164fdab4c952dc) | `6c073e19ddf604b2369c638716164fdab4c952dc` | `d030c8f4202b1f75d02ad85f51d9ffd0f13527b3` | `97e00177b6811af6c12d832b282f919ad4fce7d9` |
| [12.1.0](https://github.com/jellyfin/jellyfin/tree/ee91c75e777da41a9c4f4855e70adc604fbf2ef8) | `ee91c75e777da41a9c4f4855e70adc604fbf2ef8` | `70e7da8932b7a10daa5a49d1a8b77902e664a88a` | `e9bba05839211777bce344f8debe4b636f20fbcd` |
| [12.2.0](https://github.com/jellyfin/jellyfin/tree/ca0f16eb7c195f720a1493ed469a27c4657db0c6) | `ca0f16eb7c195f720a1493ed469a27c4657db0c6` | `022f8f0fbf634c9f75da43259e22a912a632bf04` | `e9bba05839211777bce344f8debe4b636f20fbcd` |
| [12.3.0](https://github.com/jellyfin/jellyfin/tree/06de749d435e2d0be0c5119a41f2300fdd7143e5) | `06de749d435e2d0be0c5119a41f2300fdd7143e5` | `a1e955f33f1c98709f3dce9a2b6f7cef2475f670` | `e9bba05839211777bce344f8debe4b636f20fbcd` |
| [12.4.0](https://github.com/jellyfin/jellyfin/tree/83d0d0e7f76e23e2e085c8ff67d28b772d35967d) | `83d0d0e7f76e23e2e085c8ff67d28b772d35967d` | `a1e955f33f1c98709f3dce9a2b6f7cef2475f670` | `e9bba05839211777bce344f8debe4b636f20fbcd` |

Despite different BaseItem blobs, the independent source review compared the
entire `GetVersionInfo` method and obtained identical SHA256
`2176d0c04efcdb0d9d0f02f06b59a4f0e71073eb0313f48967b7a76031ea04a0` for all
five. The 12.0 `GetStaticMediaSources` uses an `IHasMediaSources` cast; later
sources check the interface and throw for non-media items. The admitted video
subset still has the same alternate visibility filter, user source flags and
resume ordering. Neither difference rules out the narrow hypothesis. Source
equality does not attest the deployed framework patch, plugins, operator server,
actual response bytes, revocation or native media compatibility.

## Minimum production candidate contract for assessment

**Implemented / mocked-transport tested / device-unverified; not enabled.** Use an explicit operator-controlled,
default-off authenticated-original candidate mode. When enabled it replaces
original delivery only inside the admitted subset; unsupported requests **deny**
instead of falling back to the old `/Videos` route, a primary cut or Download.
The disabled mode preserves current feature behavior and its documented limits.
No automatic server setting, extra permission, default proxy or conversion is
part of the candidate.

The initial subset is the preferred native **original with watch progress**
flow, Movie/Episode single local files, MP4/H.264/AAC, video/audio streams only
(embedded and external subtitle streams are excluded), and subtitles Off. This is a
bounded candidate scope, not a new decoder limit. The existing 1920x1080 policy
remains. Trusted stock-server/static-library provenance is a deployment
precondition, not something a GUID, a public version string, a TV hint or JSON
shape can grant. Unknown provenance, untested release contracts, dynamic/channel,
remote/opening/header-dependent, disc, stacked, mapped/ambiguous path or incomplete
identity evidence deny. A version gate may restrict scope; it never supplies
permission or proves a stock deployment. General deployment requires review of
how that provenance is established, not a request-supplied assertion.

| Identity/boundary | Required candidate behavior | Counterexample to reject |
| --- | --- | --- |
| Detail identity | Keep the parent item and explicit selected source from details. | Default ordering or latest-played source chooses another cut. |
| Byte target | Use the authorized **selected version item** for `/File` after fresh parent membership, selected-item/self-source and exact path/container/size/runtime checks. | Parent ID substituted for version; same GUID shape with changed file/extent. |
| PlaybackInfo | Keep parent item + selected MediaSourceId + disabled conversion; require Direct Play on that same source. | Negotiate one source but construct another byte target or remux. |
| Resume | Keep current parent UserData policy, bounded by selected/returned duration, StartTimeTicks negotiation and native `resume:position`. | Re-read another cut's UserData, send a seek query to `/File`, or accept a changed duration. |
| Lifecycle | Keep parent ItemId, selected MediaSourceId, upstream PlaySessionId, generation/old-Stop binding and observed-only positions. | Replace reporting ItemId with File URL's version ID or treat file GET as observed Start. |
| Final authority | Recheck original capability/expiry/user-token generation after all source awaits and generation issuance, immediately before returning the URL. | Logout/expiry while metadata, negotiation or old Stop is awaiting. |
| URL construction | Only configured HTTPS/base path plus validated version ID; canonical ApiKey through existing destination validation, no arbitrary returned path. | Request-supplied host, path traversal, duplicate legacy tokens, redirects accepted as proof. |

The preferred `/api/playback/start` already checks local authority after
negotiation and after awaited lifecycle generation replacement. A candidate must
retain those fences, including the same user/token generation. The current
preferred bridge's XHR timeout is **18 seconds**, the application middleware's
deadline is 25 seconds and the mock prototype's source deadline is 20 seconds:
copying that prototype deadline into production would be too slow. The candidate
needs a new whole-operation budget below 18 seconds, including metadata,
PlaybackInfo, final checks, session-lock waiting and old-Stop/generation issuance.
An initial design is at most 10 seconds for source work inside an at-most-15-second
backend operation, leaving about three seconds for response/network overhead.
These are implemented cancellation deadlines tested with blocked mocked awaits,
not measured server/native latency. Retain the existing finite report-flush bound and deny rather than
publish a replacement if old Stop cannot be acknowledged within the budget.
Do not extend the client timeout without separate review. The legacy
unreported resolver does not supply the same final fence; it is outside this
initial candidate. No new reporting grant is issued after authority is lost.
Sequential server metadata reads still cannot create an atomic permission lease.

`/File` does not consume `StartTimeTicks` as a byte-route query. Its range/MIME
contract is source-backed; an extensionless media URL's actual native decode,
seek/resume and buffering behavior is not. The candidate must preserve the
existing requested-versus-observed distinction and validate those behaviors in a
separately authorized official-runtime run before rollout.

HLS/burn-in, external WebVTT/HTML5X and legacy unreported playback are explicitly
outside the initial candidate. Existing #19 and #22 behavior remains unchanged
when the mode is off; enabling it must refuse unsupported combinations clearly,
not silently remove subtitles, change timelines, disable reporting or fall back
to an unprotected route. Supporting those combinations later needs its own
source/interaction assessment. There is no new subtitle route or offset rewrite.

This still exposes the same user-session ApiKey to the trusted native player.
Keep the controlled private portal/interaction origin, no-store/referrer policy,
safe diagnostics and no operator material on shared preview origins. Initial
origin validation does not constrain native redirects or subsequent requests;
the isolated candidate test must require a direct non-redirect File response.
Already buffered bytes, later valid-token playback-policy changes and browser
cache behavior remain explicit limits, not promised logout cleanup.

**Assessment outcome:** a narrow authenticated-credential/scoped-file hypothesis
is source-feasible on the listed source contracts, with no newly widened user
permission, but it is not ready to replace production delivery. Minimum missing
evidence is actual exact-cut bytes/ranges/MIME and revoked/invalid/missing-token
denial on `/File`, followed by native decode/seek/resume/lifecycle correlation.
The old strict `/Videos` failure stays separate. Production candidate route code
is now present but default-off; no new live job, server, browser relay or operator
request was used for this continuation. The earlier tools-only prototype remains
independent and is not imported by production. Deployment settings are documented
in the [configuration contract](deployment.md#configuration).
