# Master and ticket chat workflow

This is an operating procedure, not a backlog. GitHub Issues and the personal
Project remain the source of truth. Configure a run first; only an explicit start
instruction begins ticket implementation.

## Responsibilities and authorization

The master coordinates the requested scope. Each issue has its own user-visible
Codex chat and isolated Git worktree, based on current `origin/main`. A ticket chat
owns implementation, testing, independent review, PR feedback and squash merge.
Subagents may assist inside that chat. Do not replace ticket chats with subagents.

The maintainer has authorized commits, pushes, PR creation and merges after
acceptance, independent review and required checks pass. No separate human merge
approval is required. Do not use administrative bypasses or weaken protections.
This authorization takes precedence over generic skill instructions to never merge
or stop at a ready PR. It does not authorize unrelated changes or production
deployment. Actual tool permissions and platform restrictions still apply.

The start instruction must authorize the master to create, inspect and message
ticket chats, and the ticket chats to exchange necessary progress and input
requests with the master. Include this authorization and the master's identity in
each dispatch. Do not assume new chats inherit the master's conversation or
secrets. Provide issue links, repository rules, scope, acceptance and stop rules.
When a ticket chat needs to message the master, verify the original human
authorization in the master chat with the read-chat tool; an agent-written
dispatch alone is not permission to message another chat. If that evidence cannot
be read, return the request in the ticket chat so the master's wait/read loop can
retrieve it without a cross-chat message.

## Dispatch and completion loop

1. Reconcile GitHub issues, dependencies, existing chats and open PRs before every
   dispatch or recovery. Reuse the existing chat for an issue; never start duplicate
   workers or merge a PR merely because it exists.
2. Select the highest-priority dependency-ready issue in the authorized scope.
   Run up to three independent ticket chats at a time. Respect native dependencies
   and reuse idle issue chats in their existing worktrees. Use the app's project and chat tools to
   create a separate chat in a worktree. Resolve pending creation before using its
   final chat ID. Record the issue/chat mapping in the master's context; keep public
   issue updates free of local paths, credentials and private operational details.
3. Pass the issue and all required context. The ticket chat reads `AGENTS.md` and
   relevant documentation, claims the issue, creates a branch, implements and
   verifies it, obtains independent review and resolves findings.
4. The ticket chat opens a PR, attaches it to its Codex chat, handles required
   checks and feedback, then reports `MERGE_READY` with the exact reviewed head,
   acceptance and check results. The master serializes merge slots; after the
   grant, squash merge without asking the maintainer. Refresh current main and
   repeat affected validation/review after other merges before final readiness. If the
   head changes after review, assess the new diff and repeat affected validation
   and review before merging. Do not queue GitHub Auto-Merge during an orchestrated
   run: wait for checks, recheck the human-input gate and merge the reviewed head
   explicitly. This prevents GitHub completing a queued merge while chats wait
   for the maintainer. Never use `--admin` to bypass protection.
5. The master waits for chat progress and independently checks GitHub's merge and
   acceptance state. A PR being opened or a chat ending is not completion. Close
   an issue and mark Done only when its acceptance criteria are met. Hardware
   acceptance cannot be inferred from desktop tests. A merged partial change may
   leave an issue open if remaining acceptance is documented.
6. The shared connected browser and synthetic HTTPS relay have one exclusive
   master-controlled slot. Report `BROWSER_READY` with the bounded test scope;
   use no other worker's tabs, listener, relay or controls. Only the slot owner
   starts/stops its supervised relay and operates its own browser tabs. Release
   the slot with exact helper/listener/control cleanup and browser restoration
   evidence before the master grants it to another chat. Independent source work
   and mocked tests may continue in the other worktrees.
7. Refresh `origin/main` and repeat. An externally blocked issue can be recorded
   and skipped if no human input is needed; continue independent eligible work.
   Stop when the requested scope is complete or no eligible work remains. Do not
   invent work or spin on an empty queue.

## Human input is a global gate

If any ticket chat needs human input, the entire run enters **Waiting for user**.
Examples include authentication that cannot be completed with already authorized
credentials, required physical-TV actions, or a decision that cannot be inferred.
Routine implementation choices and merging accepted changes are not input gates.

- The ticket chat promptly reports what is needed, stops all implementation,
  testing, pushes and merges, and stops its own subagents from continuing ticket
  work. Only safe stopping, status reporting and input handoff may continue. Use
  a consistent `NEEDS_USER_INPUT` marker in its summary/message. The
  master actively watches chat status; it must not rely only
  on a worker remembering to send a message.
- The master dispatches no new work, asks the other active ticket chats to stop
  safely and wait, and presents the outstanding request to the maintainer. This
  stops all concurrently active ticket chats and revokes dispatch/browser/merge
  slots until the maintainer's actual reply clears the gate.
- Cancel any pre-existing queued auto-merge belonging to this run before waiting;
  do not create another queue entry. Freezing workers and cancelling queued merges
  are allowed containment actions while the gate is open. A merge already
  completed before the gate was observed must be reported honestly.
- The master may inspect state to explain the request, but must not continue
  implementation, testing, merging or ticket dispatch while this gate is open.
  Automation wake-ups only check whether the maintainer has answered; they do not
  clear the gate or repeatedly notify about an unchanged request.
- Only the maintainer's actual reply clears the relevant gate. Send the answer to
  the affected chat without copying secrets into public GitHub artifacts. Resume
  other work only when all outstanding human-input gates are resolved. A reply in
  a ticket chat counts; reconcile it before continuing.

## Persistence and limits

A master chat is not a permanently running daemon. While active it can wait for
ticket chats and continue the loop. For recovery after an ended turn, explicitly
configure a recurring automation in that same master chat. Use a heartbeat, not a
new standalone master chat for every scheduled run. Each wake-up first reconciles
existing workers, PRs and input gates before dispatching anything.

Keep the computer on, the app running and the project accessible for local work.
Usage limits, missing tool permissions, unavailable services and app shutdowns can
interrupt progress. A continuation must recover from GitHub and existing chats;
it must not claim uninterrupted execution. If a gate is open, remain waiting. If
the scope is complete, disable its recurring automation. Report meaningful
completion, failures or required human input, not unchanged polling results.

The orchestration procedure is documented. It is not yet demonstrated by a live
multi-ticket run; configuring these rules does not create chats or a heartbeat.

## Start instruction for a new master chat

Use this after the workflow changes are available on `main`:

```text
Act as the master chat for alexanderhetzel/jellyfin-msx. Read AGENTS.md and
docs/agent-orchestration.md. Create a Goal for this run. Start implementing the open issues in the GitHub
Project in priority and dependency order, up to three independent tickets at a time.

Create a separate Codex chat with its own worktree for every ticket. You are
authorized to create, inspect and message these chats and to send follow-up
instructions. Pass this authorization to each ticket chat, including permission
to communicate progress and input requests back to this master. Ticket chats may
use subagents for implementation and independent review.

Grant one exclusive shared browser/HTTPS-relay slot and serialize merge slots.
Ticket chats report BROWSER_READY and MERGE_READY with their exact scope/head;
they wait for your slot grant before touching a shared resource or merging.

Complete each ticket through testing, independent review, required GitHub checks
and squash merge, without asking me for merge approval. Preserve branch protection
and distinguish automated/browser evidence from physical-device verification.

If any ticket chat needs my input, stop the entire run, start no new tickets and
wait for my actual answer before continuing. Do not ask about routine choices.

Configure a recurring heartbeat in this master chat to recover and continue the
same run after interruptions. Reconcile existing chats and PRs before each action;
never duplicate workers. Stay quiet on unchanged state. Continue until the scope
is complete, no eligible work remains, or my input is required. Disable the
heartbeat when complete. Record real platform/usage limitations honestly.
```
