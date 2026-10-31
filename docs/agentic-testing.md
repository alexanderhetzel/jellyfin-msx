# Agentic testing cookbook

This is an execution guide, not a task backlog. Repository issues define scope
and acceptance; `docs/status.md` and the MSX/device result files record evidence.
Use `msx-testing.md` for lab startup, TLS and actual runtime details.

## Choose checks from the change

1. Read the issue's observable acceptance criteria, current source and prior
   results. Identify affected contracts and existing behavior to preserve.
2. Cover success, denial and recovery. Relevant boundaries include authentication,
   expired/replayed codes, CSRF, device isolation, private metadata/images, source
   pinning, malformed upstream responses, URL origin/base path, resolution policy,
   no-transcoding flags and network/player failures.
3. Use mocked Jellyfin transport for deterministic automated contracts. Add focused
   regressions for real bugs, not tests that merely repeat implementation details.
4. Run affected tests, then the full required CI checks for a shared change.
   Never count a mocked PlaybackInfo flag as an actual decoding pass.
5. Exercise affected user flows in the official MSX runtime. Use the connected
   Chrome extension consistently for all browser tests and Jellyfin media inspection.
   Do not use the integrated browser or native Chrome app automation.
   Do not copy runtime code, inject player state or switch to native Arc automation.
6. Run the physical-device gate for device/codec/audio/remote claims. A browser or
   USB player cannot establish native MSX-on-TV compatibility.

## Normal live pairing without operator involvement

The operator authorized a dedicated account in the local OS secret store. This
is test operation, not a product feature and not a separate feature ticket.

1. Keep an existing session when suitable; do not restart/reload unnecessarily.
   If a fresh pairing is required, open the official runtime and read its displayed
   pending code. Do not scrape hidden application state or capability URLs.
2. Load only the authorized account in the test process at runtime. On the current
   Mac it is the login-Keychain service `jellyfin-msx.local-integration`. Never
   print the password/token or put it in argv, source, GitHub or reports.
3. Complete the normal pairing form. If using an HTTP form client to keep secret
   values outside agent/browser logs, GET the real `/pair` form, retain its normal
   CSRF cookie in memory, read the hidden form field inside that process and POST
   the current code with the exact expected Origin. Only after a valid code check,
   retain the rotated cookie and new hidden CSRF/stage fields in memory and POST
   those fields plus the account/password to the same clean `/pair`. Validate the
   configured destination and TLS; follow no redirects. Do not bypass validation
   or add a special authentication endpoint.
4. Check the success response, then select Continue in actual MSX and verify that
   authorized libraries render. A direct Jellyfin login alone proves only login.
   Record whether credential submission used native browser input or the normal
   HTTP form path; these are distinct form-rendering checks.
5. Use synthetic credentials in public CI. Inspect only redacted result/status
   counts; leave live account identifiers and server addresses private.

## Playback loop

Use existing authorized media or isolated synthetic fixtures. Browse library,
posters and detail, invoke the actual MSX play control, and verify all of:

- A real picture and advancing video time, dimensions, readyState and no media error.
- Pause holds time across observations; Play resumes time.
- Forward and backward controls cause real jumps followed by resumed frames.
- Stop returns to usable details, media stops, replay works and Back retains focus.
- An ineligible source is denied without an extra conversion/PlaybackInfo request
  when policy requires pre-negotiation rejection.

Inspect only safe video properties: time/duration, paused/muted, readyState,
dimensions and error code. Never read `src`, cookies, bearer tokens or hidden app
state. Use actual controls, not JavaScript setters for play/currentTime. Check
control visibility before clicking; MSX auto-hides the player overlay. CSS icons
may have no DOM text: derive selectors from observed visible DOM classes rather
than guessing glyph text. After transitions inspect settled UI before choosing
another action.

When browser-control handles become stale, rebind/reset the control session
without reloading the page or restarting the backend. An API input failure is
not an application/TV-remote failure. If the tooling cannot verify audible sound,
state that explicitly rather than deriving sound from video readyState.

## Evidence and closure

Correlate actual UI/media observations with redacted upstream request counts,
HTTP statuses, selected profile/source properties and conversion flags. Keep raw
screenshots/captures local and out of Git; publish only sanitized observations.
Never include real media titles/IDs/paths, server addresses, pairing codes,
capability/media URLs or credentials. Automated, official-browser and physical-TV
results are separate categories. Report failures and unavailable tooling honestly.

Before closing an issue, check each criterion against actual evidence, review the
change independently, update durable docs and set the corresponding Project state.
Do not create product tickets for routine agent clicks or sign-in operations.
