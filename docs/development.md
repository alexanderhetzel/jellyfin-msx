# Development workflow

- Repository: https://github.com/alexanderhetzel/jellyfin-msx
- Project: https://github.com/users/alexanderhetzel/projects/5
- Issues: https://github.com/alexanderhetzel/jellyfin-msx/issues
- Milestones: https://github.com/alexanderhetzel/jellyfin-msx/milestones

GitHub Issues are the source of truth for tasks, bugs and accepted ideas. The
Project is their planning view; do not maintain a parallel Markdown backlog.
Architecture, compatibility evidence, runbooks and dated test results remain docs.

## Issue and Project conventions

Every issue states its goal, background, observable acceptance criteria,
verification, invariants and dependencies. Search before filing. Use issue
templates and leave issues unassigned until work is claimed.

| Field | Convention |
| --- | --- |
| Status | To triage, Backlog, Ready, In progress, In review, Done |
| Priority | P0 critical, P1 high, P2 normal, P3 low |
| Work type | Bug, Feature, Task, Research; GitHub reserves the name Type |
| Area | Pairing, Playback, MSX UI, Jellyfin, Security, Deployment, Testing, Docs, Tooling |
| Size | XS, S, M, L, XL; decompose XL before implementation |
| Milestone | One delivery outcome; no invented deadlines |

Use `type:*`/`area:*` labels in repository lists. `needs-device` means acceptance
requires actual hardware, `blocked` requires a stated dependency, and `security`
marks boundary work. Report vulnerabilities privately. Native issue dependencies
and linked PRs should match issue descriptions.

Project views cover all work, delivery, Ready work, device verification, pairing/
UX and release readiness. Built-in workflows manage added/closed/linked/merged
items. Mark Done only after acceptance; automation is not verification.

## Branches and review

Use the [locked build and dependency-update procedure](build-supply-chain.md)
for artifact changes. CI locks the backend environment as well as runtime
dependencies and inspects wheel, filtered Docker context and final image manifests.

The default `main` is maintained. Preserve the original upstream `master` and its
license boundary. Use issue branches from `main` and PRs to this fork unless
upstream contribution is separately requested. CI checks locked Python tests,
lint/build, Docker/proxy packaging and full-history secrets. Main requires passing
checks and resolved conversations; use squash merges. A solo-maintainer setup
must not require impossible self-approval. Obtain independent review as described
in `CONTRIBUTING.md` and `AGENTS.md`.

The maintainer authorizes agents to complete requested work through squash merge;
do not stop merely to request merge approval. Independent review, acceptance and
the required checks still apply, and protection must never be bypassed. Generic
skills that end at a ready PR do not revoke this explicit project authorization.

Use [master/ticket chat orchestration](agent-orchestration.md) for a requested
multi-issue run. A ticket chat needing human input stops the entire run until the
maintainer responds. Configuring this workflow does not start implementation.

## Live integration credentials

Public CI uses synthetic accounts/servers. Local integration may use an explicitly
authorized account from the OS secret store or runtime environment. Never put
credentials in GitHub, source, command arguments, logs or reports. Do not add a
product feature or issue for routine agent operation of an existing pairing form.

The current macOS lab uses service `jellyfin-msx.local-integration` in the local
login Keychain. Account/password values are not repository configuration. Load
only that entry inside the test process and never print it. A runtime lookup and
real Jellyfin sign-in/sign-out succeeded without exposing credentials. The normal
pairing form remains CSRF protected and requires its current pending TV code.

See [the agentic testing cookbook](agentic-testing.md) for choosing checks,
operating the normal pairing flow and recording meaningful runtime evidence.
