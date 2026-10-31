# Jellyfin MSX agent instructions

## Scope and workflow

Jellyfin MSX continues SerhiyRomanov/jellyfin-msx:master as a Jellyfin client for
Media Station X. Present functionality first; device evidence belongs in
`docs/compatibility.md`. The independently authored current implementation has one
Philips candidate profile; do not infer universal device support.
Read the owning GitHub issue, `docs/development.md`, `docs/architecture.md` and
`docs/status.md` before changing behavior.
Use local source and tests as evidence. Keep unrelated user work intact.

For new work: inspect -> define acceptance criteria in the owning GitHub issue ->
implement one coherent milestone -> test -> review -> update documentation.
Work autonomously within the user's request. Do not require a specification approval
for routine implementation already requested. Repository Issues are the task
source of truth; the personal Project is their planning view. Do not maintain a
Markdown backlog or parallel local task plan. See `docs/development.md`.
Link accepted issues to the Project and populate its Status, Priority, Work type,
Area and Size fields; keep native dependency links and issue descriptions aligned.
The maintainer has explicitly authorized autonomous implementation, commits,
pushes, PR creation and squash merges for requested work in this repository.
Do not wait for human merge approval after acceptance, independent review and
required checks pass. This project-specific authorization overrides generic
skill instructions to stop at a PR or never merge. Never bypass branch protection
or merge failing, unreviewed or unaccepted work. Production deployment and actions
outside the requested scope still need their own authorization.
Use a task branch before implementation and preserve dirty worktrees.

When the maintainer starts a multi-ticket run, use one master chat to coordinate
one separate Codex chat per issue, each in its own worktree. Subagents may help
inside a ticket chat; they do not replace the separate ticket chats. Read
`docs/agent-orchestration.md` before coordinating a run. The master may create,
read, wait for and send follow-up instructions to those chats within that run.
Keep three independent ticket chats active whenever at least three authorized,
dependency-ready tickets have useful work available. Three is the operating target,
not merely a concurrency ceiling. After any completion or blocker, immediately
reconcile the queue and refill the free slot without waiting for a reminder or
heartbeat. Use fewer only when fewer tickets are independently actionable or the
global human-input gate is open; record the concrete reason. Waiting for the shared
browser or merge slot does not block independent source, test or review work.
The master grants an
exclusive slot for the shared browser/HTTPS relay and serializes merges; workers
prepare independently and report readiness before using either shared resource.
If any ticket chat needs human input, stop dispatching and pause all active ticket
work until the maintainer responds. Elapsed time, retries and automation wake-ups
are never approval. A workflow-setup request does not start ticket implementation.

## Engineering rules

- Python/FastAPI owns authentication, Jellyfin REST and MSX JSON generation.
- Keep configuration, session state, Jellyfin transport, playback policy and UI separate.
- Never reuse unlicensed reference code. Record reference revision and licensing evidence.
- No passwords, access tokens, capability URLs or pairing codes in logs or documentation.
- Live test credentials belong only in an authorized OS secret store or runtime
  environment, never GitHub/CI/source. Load without printing; CI uses synthetic
  accounts and no authentication bypass. Routine agent pairing needs no feature ticket.
- All private routes must authenticate a random, expiring capability; a TV ID is not authentication.
- Jellyfin server address is operator configuration, never an arbitrary request URL.
- Do not proxy video by default. Explain the token exposure tradeoff for direct URLs.
- Build the Philips 32PHS6605/12 candidate profile from cited model/platform evidence.
  Manufacturer multimedia support and conditional audio-output support are distinct
  from verified MSX playback. Label candidates unverified; never claim a physical
  TV pass from documentation, USB/DLNA lists, desktop results or PlaybackInfo alone.
- Missing essential stream metadata must disable negotiation. Do not invent numeric
  decoder limits from panel size or HDMI timings. HEVC remains a documented candidate
  until physical MSX evidence establishes support for the tested combination.
- Enforce the explicit 1920x1080 client admission policy in local checks and
  PlaybackInfo. 4K playback/downscaling is excluded. Do not turn undocumented
  capability into permission or describe this client boundary as a proven chip limit.
- Ultra.cc is the operator's host: transcoding and subtitle burn-in stay disabled
  by default. Never enable them on the real Ultra server while testing.
- Multi-version movies must select an eligible source consistently for details/playback.
- Use mocked Jellyfin transport in tests; never contact a real server in the test suite.
- Keep dependencies minimal and locked. Use `apply_patch` for source/document edits.
- Tests: `uv run pytest`; quality: `uv run ruff check .`, `uv run ruff format --check .`.
- Verify browser forms with `browser-verify`; only the physical TV can validate MSX playback.
- Use the official MSX runtime for application verification. The user now requires
  one consistent test browser: use the integrated browser for all testing, including
  Jellyfin media inspection. Do not switch back to native Arc automation.
  Do not copy, host or modify the proprietary MSX runtime code. Use its published API.
- A successful test count is not an MSX integration pass. Record UI actions,
  actual media observations and sanitized request evidence separately.
- Review failure paths and security boundaries before handoff. An independent review
  may be delegated as required by the implementation skill; report review limitations.

## Documentation and handoff

Documentation lives in this repository's `docs/`, in English. Chat may be German.
Mark claims **implemented**, **automated-tested**, **device-unverified** or **deferred**.
Update `docs/status.md` with actual commands/results, never inferred passes.
Hardware results belong in `docs/device-test-results.md` with firmware, MSX version,
media properties and redacted diagnostics. Report acceptance status and remaining blockers.
Only this repository's workflow and applicable user instructions govern this
project; unrelated workspace infrastructure and organization policies do not apply.
