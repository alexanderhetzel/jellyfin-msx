# Real MSX integration observations — 2026-10-30

Status: **REAL BROWSER VIDEO PATH PASSED; broader M2a/TV acceptance still open.**

## Current real-server run with HD-policy-v2

Human pairing succeeded in the integrated browser. The agent operated official
MSX 0.1.167 through the full route: libraries, posters, 720p detail, original play,
pause, resume, forward/back seek, Stop, replay and Back. Existing media was used;
no transcoding, remuxing, uploads or production settings changes occurred.

| Case | Observed evidence |
| --- | --- |
| Video startup | Actual frame visible; H.264 1280x720, readyState=4, error=null; currentTime 4.3748 then 29.4338 |
| Pause/resume | Pause held at 73.2087 in two observations; actual MSX Play control resumed time |
| Forward seek | MSX fast-forward control jumped to 116 seconds; continued to 132.3544, readyState=4, error=null |
| Backward seek | MSX rewind moved 136.2956 to 107; continued to 121.5698, readyState=4, error=null |
| Stop | Actual MSX eject/Stop returned to details; video paused at zero, readyState=0 |
| Replay | Second original-play action reached 9.0322 seconds, 1280x720, readyState=4, error=null |
| Back/focus | Poster list returned, retaining selected item's focus |
| Actual oversized-item denial | Detail displayed width/height policy rejection and an unlisted-codec reason; no play control, no third PlaybackInfo request |
| No conversion | Exactly two real PlaybackInfo calls, HTTP 200; DirectPlay=true, DirectStream=false, Transcoding=false, subtitle index=-1; both decisions DirectPlay |

The MKV source contains two E-AC-3 6-channel tracks. The browser video was not
muted, but audible sound was not independently confirmed by tooling; do not label
audio/Atmos verified. The player reported platform `mac-detected`, player
`html5/plugin`; this does not characterize the SAPHI engine. Remote-style
ArrowLeft automation failed at the browser API despite a visible body element;
the successful actions above used DOM clicks, not injected player state.
Physical remote control, populated series, subtitles, long playback and near-end
seeking remain open. Local sanitized request evidence is in ignored
`.lab/reports/msx-real-playback-2026-10-30.json`.

## Earlier profile and renderer observations

Profile correction: the current source now uses a named, documentation-based
Philips 32PHS6605/12 candidate profile. After the operator requested the next step,
the lab was restarted with the HD-policy-v2 profile and fresh pairing succeeded
in the integrated browser, followed by the real playback run above.
The prior denials below used the old assumed 720p/MP4/AAC-stereo policy and are historical
software-policy observations, not proof of hardware incompatibility.
The operator's new 720p file was inspected through the signed-in Jellyfin web UI
in the integrated browser: MKV, AVC Main level 3.1, 1280x720/24fps/8-bit, with two
E-AC-3/Atmos 5.1 audio tracks. That shape is now a conditional original-play
candidate in source and mocked PlaybackInfo tests. It subsequently passed the
browser video tests above; physical SAPHI playback remains untested.

New-profile renderer check: production FastAPI detail JSON using mocked metadata
was sanitized to remove private/media actions, then rendered in official MSX
0.1.167. The model row and “Try original (TV unverified)” control rendered;
clicking the model row displayed the conditional-audio and unverified-limit warning.
No actual video or upstream request was made by this isolated preview.

4K-policy correction renderer check: the current FastAPI detail route was called
with a 3840x2160 HEVC mock source and direct-only settings. Its returned rejection
JSON was rendered in official MSX 0.1.167 in the integrated browser; the private
diagnostics action was replaced with a harmless notice. Clicking the first row
displayed: maximum 1920x1080, no client 4K playback/downscaling, a matching stored
720p/1080p copy required, transcoding disabled. Screenshot inspection at 1280x720
showed the complete message on two readable lines, and no play row. An incorrect
initial inline URL caused a 404; the published `content:json:` format then loaded
the page correctly. No real PlaybackInfo/video request or TV decoding occurred.
The 169-test automated suite and independent review additionally verify 4K
rejection with optional conversion enabled and after changed upstream metadata.

| Case | Result | Evidence / boundary |
| --- | --- | --- |
| Official runtime starts | PASS | MSX 0.1.167 web loaded in the isolated browser; separate Arc startup also observed |
| Production-shaped list rendered by MSX | BUG FOUND | Inline smoke fixture showed selected text clipped with the original separate-item template |
| List template correction | PASS in real web runtime | Corrected default-item template showed full-height focus rectangle and readable centered titles; poster cards remain separate |
| Local HTTP backend from HTTPS MSX | FAIL, explained | MSX upgraded to HTTPS; HTTP server logged invalid TLS-as-HTTP requests |
| Local HTTPS certificate | PASS after scoped correction | System SSL verification passed; Arc and isolated browser accepted the same non-CA localhost leaf after removing unsupported additional policy-string constraint |
| Arc native accessibility | Initially incomplete, recovered | First native captures exposed only browser chrome; later a fresh AX query exposed the actual lab dashboard and MSX link |
| MSX → loopback backend | PASS in Arc | User approved the displayed loopback-network permission; actual Pair this TV page loaded from FastAPI |
| Real Jellyfin public connection | PASS | Operator-authorized HTTPS endpoint returned version 12.4.0 |
| Pairing failure reproduced | CONFIRMED application bug | Real native browser form POST, with dummy username, no password and an invalid code, returned Form expired/403. The no-referrer policy makes Chromium send Origin:null, conflicting with strict origin validation. The initial code-expiry hypothesis did not explain the repeated failure |
| Form POST policy correction | PASS in real isolated browser | Only /pair now uses Referrer-Policy:same-origin; private routes retain no-referrer. A fresh GET followed by the same native form submission reached code validation (400 invalid code), proving CSRF validation passed without weakening its origin or token checks. No Jellyfin authentication request was made |
| Real Jellyfin authentication and pairing recovery | PASS | User confirmed paired; Arc displayed the separate TV paired / Sign-in succeeded page. Redacted report recorded one authentication request, HTTP 200 pairing result and one paired session |
| First private-library request | FAILED; interoperability fix implemented | MSX Continue triggered the real backend and Jellyfin; actual MSX displayed a 401 Jellyfin-denied error. Client used removed X-Emby-Token authentication. Current code uses MediaBrowser Authorization Token and canonical ApiKey video parameter; updated mocks and independent review passed |
| Authentication after Jellyfin 12 fix | PASS | Fresh human sign-in again showed TV paired in Arc; report corroborated HTTP 200, one upstream authentication request and one paired session |
| Private-library rerun after fix | PASS for library overview | Operator screenshot shows the actual Jellyfin libraries menu, movie/series entries and focus rectangle. Fresh agent AX observation also read this menu. The earlier black agent capture was not evidence of a black application screen. Authentication and library access are confirmed; deeper browsing/playback remain separate gates |
| Movie browsing and details | PASS in real MSX browser | Direct DOM clicks opened the real movie library and two movie detail pages. Titles, year/type and overview rendered. MSX Back returned to the library; Libraries returned to the library chooser |
| Private posters | PASS in real MSX browser | Two posters visible in a real screenshot; DOM img.complete=true and natural dimensions 360x540 for both. No image URLs retained |
| TV-sized browser layout | PASS for poster library | At 1366x768, screenshot showed both posters, focus rectangle, titles/year and navigation tile. Resize transition briefly showed a busy indicator, then full-size layout settled. Viewport override reset afterward; this is not a SAPHI rendering claim |
| Incompatible-only denial | PASS for two existing movies | Both detail pages displayed No compatible TV version. Clicking the control showed the explicit 720p H.264/AAC MP4 requirement and transcoding-disabled message. Redacted report retained no PlaybackInfo negotiations during these denials |
| Compatible stored version selection and actual playback | PENDING AT THAT EARLIER RUN | Then neither movie exposed an eligible source under the old policy; the new real 720p playback run above supersedes this result |
| Series library | EMPTY | Series chooser opened successfully but contains no titles. Season/episode traversal cannot be exercised with current real data |
| Native Arc control | LIMITED | Leaving fullscreen produced a visible agent screenshot of the library menu, but coordinate input still failed and AX/action state was inconsistent. This does not establish an application defect |
| Agent-controlled browser lab connection | PASS | A separate official MSX tab in the isolated browser loaded actual loopback pairing JSON without a new permission prompt. Down/Down/Enter visibly reached Waiting for pairing; separate sign-in requested for this test session. Existing Arc session retained |
| Sustained browser control | PASS for current direct-click flow | After successful additional sign-in, mixed native/DOM observations showed libraries followed by a fresh pairing page; cause not conclusively isolated. Direct DOM clicks in one bound tab with pointer input and suspend disabled subsequently completed pairing → libraries → movies → details → Back → libraries → series → libraries → movies without another sign-in. No private playback pass inferred |
| Standalone MSX sample playback | PASS, renderer smoke only | Keyboard Down/Down/Enter started official sample; video readyState=4, no error, 1280x720, duration 117.823s, currentTime 8.890s and paused=false; not a Jellyfin playback test |
| Standalone sample time advancement and pause | PASS, renderer smoke only | Video time advanced to 113.010s; on a subsequent run Enter displayed controls and Enter paused at 39.822s with paused=true and no media error |
| Standalone sample seek | UNVERIFIED | Progress controls appeared, but no convincing time jump was measured. Insert returned to the menu; no seek pass is claimed |
| Real media play/pause/seek | NOT RUN AT THAT EARLIER STAGE | Subsequently passed the current real browser run above |
| SAPHI playback/firmware | NOT RUN | No firmware download or TV change performed |

Software checks include direct-only regression tests and lab safety tests.
Their pass counts are separate from both the historical cases in this table and
the current observed browser playback results above.
