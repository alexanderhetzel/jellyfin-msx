# Hosted synthetic HTTPS observations — issue #9

**Implemented / device-unverified:** this partial manual
browser run exercised the real application through the official hosted Media
Station X 0.1.167 web runtime in the connected Chrome extension on Windows.
The temporary synthetic-only Cloudflare delivery was explicitly authorized.
No proprietary runtime was copied, hosted or changed. No operator configuration,
server, credentials, media or renewal records were used; no DNS, browser security,
trust or transcoding setting changed. The fixture uses strict mocked Jellyfin and
the committed generated H.264/AAC 1280x720, 30-second clip.

The run used worker-created MSX and companion tabs, a separately displayed test
code and the normal two-stage CSRF pairing form. These were separate tabs in the
same Chrome profile, **not isolated browser cookie contexts**. The worker did not
operate the user's tabs or code. Only the worker's session was disconnected;
the shared relay was not stopped or restarted during the user's test window.
No capability, login token, pairing code, raw JSON or private media URL is recorded
here. Observations were taken on 2026-10-30 UTC (2026-10-31 in Vienna).

## Actual UI and media observations

| Action | Visible result and corroborating observation |
| --- | --- |
| Open the official runtime with the synthetic application start action | Pairing screen rendered with companion instructions, current code, Continue and Create new code. |
| Enter the worker's displayed code in the normal companion form | Step 2 displayed Jellyfin username/password fields; no invalid-code error. |
| Submit the public fixture login through the normal form | Pairing complete / TV paired; return-to-MSX instructions displayed. |
| Select Continue after pairing | Jellyfin libraries displayed Synthetic movies, Diagnostics and Disconnect TV. |
| Open Synthetic movies, then Synthetic clip | Movie list and details rendered; details identified the documentation-based Philips candidate and generated test pattern. Loaded images were observed; poster fidelity was not separately assessed. |
| Select Try original | A moving color-bar/test-pattern frame appeared. Read-only media observations showed 1280x720, readyState 4, no media error and advancing time (including 3.273302 seconds). The synthetic clip was delivered through the fixture's authenticated media path, not a real Jellyfin server. |
| Pause using the actual MSX remote Enter interaction | Paused=true and time 4.414494 remained unchanged across consecutive observations. |
| Resume using Enter / visible selected player control | Paused=false and time advanced; no media error. |
| Select and activate the actual forward/back seek controls with remote arrows and Enter | Media time changed to 12 seconds after forward seek and to 10 seconds after backward seek; neither operation assigned media state through script. Near-end seek was not separately established. |
| Use Escape during playback | Player stopped and usable Synthetic clip details returned; media paused at time 0. BackSpace did not establish Stop behavior. |
| Select Try original again | Replay restarted near 0.020024 seconds with no media error. |
| Use the visible remote Back arrow from details | Library returned with the selected-item position retained; returning from the oversized item showed Library (2/3). Escape did not establish equivalent content Back navigation. |
| Open Oversized candidate and Compatibility details | No Try original action; paused media stayed at time 0. The visible notice stated that the video exceeded the 1920x1080 client limit and that 4K playback/downscaling was disabled. The fixture reused the Synthetic clip detail title; title correctness for this candidate is not claimed. |
| Open Libraries, Disconnect TV, Confirm disconnect | Disconnected and Pair again displayed for the worker's session. |
| Follow stale Back navigation | Actual Data Load Error / 401 Session missing or expired appeared with instructions to reopen the start page. This is visible denial evidence, not a claim that the generic runtime error presentation is polished. |
| Reopen the official start action | Pairing screen and code instructions rendered again. The worker did not pair the new session and closed both owned tabs. |

A frame-only screenshot was saved and inspected locally at ignored
`.lab/https-playback-frame.png`; its crop excludes application identifiers,
credentials, URLs and controls. The frame shows the generated pattern and encoded
time counter. Audible sound was **not verified**. Read-only DOM media observations
never inspected or printed a private source URL and did not alter player state.
Initial mouse/icon activation attempts did not establish pause; only the actual
successful remote/control observations above are counted.

## Scope and remaining acceptance

This is a manual partial integration observation, not a complete reproducible
browser command or public-CI end-to-end test. The complete #9 matrix remains
open: wrong/expired codes and credentials, deliberate JSON/playback/CSRF faults,
controlled network failure, expiry/recovery, series/seasons/episodes, pagination,
full source-version consistency, near-end seeking, cross-session isolation and
post-disconnect poster/media requests were not established by this run. Existing
backend tests do not substitute for those browser observations. The stale-route
401 alone does not prove every private resource was revoked. Storage acceptance
remains with #11. Physical Philips playback, audible audio, remote differences,
standby and stability remain **device-unverified**, deferred to the hardware
stage. This partial result does not close #9 or establish real-server compatibility.
