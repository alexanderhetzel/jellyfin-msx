# Contributing

Development is tracked in [repository issues](https://github.com/alexanderhetzel/jellyfin-msx/issues)
and the [personal GitHub Project](https://github.com/users/alexanderhetzel/projects/5).
Search for an existing issue before creating one. Use an issue for each outcome,
including acceptance criteria and verification. Claim work before implementation;
do not assign all work to the maintainer by default.

The default `main` branch contains the maintained Jellyfin MSX implementation.
The preserved upstream `master` branch is historical reference, not the source
to run or copy. Read `NOTICE.md` before reusing any historical source. Original
contributions to the current implementation are accepted under MIT.

## Working on an issue

1. Read `AGENTS.md`, the issue and its dependencies.
2. Branch from current `main`, for example `12-remember-paired-tv`.
3. Make one coherent change. Preserve authentication boundaries and the default
   no-transcoding policy. Do not contact a real Jellyfin in automated tests.
4. Run `uv sync --frozen --extra dev`, `uv run pytest`, `uv run ruff check .`,
   `uv run ruff format --check .` and `uv build --wheel` as relevant to the change.
5. For MSX UI/player changes, also exercise the official runtime and record real
   observations. Desktop playback does not certify a Philips decoder or remote.
6. Open a PR against this fork's `main`, link the issue, describe validation and
   remaining limits, and use a Conventional Commit-style title.
7. Merge by squash after required CI and review findings are resolved. Close only
   accepted work; a mock test cannot close a hardware acceptance issue.

## Privacy and reports

Use fictional servers under `example.com`, `.test` or `.invalid` in source/tests.
Keep operator configuration in environment variables. Never commit `.env` files,
private keys, tokens, pairing codes, media/capability URLs, real media titles or
paths, raw captures or test-account credentials. `.lab/` is local and ignored.
Only `.env.example` with placeholders belongs in Git. Dependency secret scanning
does not replace checking the staged file list and diff before each commit.

For security vulnerabilities, use [private reporting](https://github.com/alexanderhetzel/jellyfin-msx/security/advisories/new),
not a public issue. See `SECURITY.md`.
