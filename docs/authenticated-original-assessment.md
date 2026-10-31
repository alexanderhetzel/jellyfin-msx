# Authenticated original-file route assessment — issue #32

**Source-reviewed / mock-only prototype / device-unverified — 2026-10-31.**
This evaluates a new delivery hypothesis. It does not change production routing,
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
