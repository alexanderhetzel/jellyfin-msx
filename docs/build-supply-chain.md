# Build inputs and dependency updates

**Implemented / automated-tested:** the application wheel and Linux container use
the committed Python dependency lock. This is input/version reproducibility, not
a claim that every rebuild is byte-identical or that dependencies are risk-free.
Physical MSX playback, public HTTPS rollout and production credentials are outside
this build check. See [actual results](status.md).

## Reviewed inputs — 2026-10-30

| Input | Selection and evidence |
| --- | --- |
| Python builder/runtime | `python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159` |
| HTTPS proxy | `caddy:2-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5` |
| Build backend | `hatchling==1.33.0` in both build-system requirements and the `build` dependency group; transitive versions/artifact hashes in `uv.lock` |
| Bootstrap | `uv==0.9.8`, existing tool version retained; reviewed PyPI wheel SHA256 values in `tools/requirements.txt` |
| GitHub Actions | Full commit SHAs; checkout does not persist credentials; workflow token has only `contents: read` |
| Secret scanner | Gitleaks 8.30.1 release archive with its existing SHA256 verification; complete Git history, redacted findings |

The image values are multi-platform index digests, preserving the existing tag
families rather than migrating to a new Python minor or Caddy major. Public
[Docker Hub Python tag metadata](https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim)
and [Caddy tag metadata](https://hub.docker.com/v2/repositories/library/caddy/tags/2-alpine)
were checked against the official `registry-1.docker.io/v2/library/{image}/manifests/{tag}`
responses: their `Docker-Content-Digest` and locally computed SHA256 agreed.
Linux amd64 child digests were respectively
`sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b`
and `sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a`.
CI executes Linux amd64 builds; the index listing other architectures is not an
execution pass for them. Bootstrap hashes cover Linux amd64/arm64 and Windows
amd64; add reviewed wheel hashes before using this bootstrap on another platform.
[PyPI's uv release metadata](https://pypi.org/pypi/uv/0.9.8/json) and
[Hatchling metadata](https://pypi.org/pypi/hatchling/1.33.0/json) are the provenance
for those selections.

## Locked build and inspection

Supported automated build matrix: CPython 3.12 and 3.13 on Linux amd64. Local
Windows/Python 3.12 results are reported separately. `requires-python >=3.12`
expresses the package minimum; it does not certify every later interpreter.

```sh
python -m pip install --require-hashes --only-binary=:all: -r tools/requirements.txt
uv lock --check
uv sync --frozen --only-group build
uv sync --frozen --extra dev --group build --no-build-isolation
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync python -m tools.synthetic_check
uv build --python .venv/bin/python --wheel --no-build-isolation --offline
python -m tools.package_check wheel dist/jellyfin_msx-0.1.0-py3-none-any.whl
```

On Windows use `.venv/Scripts/python.exe` for the build interpreter. An explicit
`--python` avoids an unrelated `UV_PYTHON` override selecting an environment
without the locked backend. Plain isolated `uv build` pins the direct backend but
does not lock its transitive environment; use the procedure above for reviewed
builds. Update the backend requirement and build-group requirement together.

Docker exports runtime and build-only groups separately with hashes. Pip requires
hashes and binary wheels for downloaded dependencies; missing compatible wheels
fail closed instead of invoking unreviewed dependency source builds. The project
wheel builds offline using the installed locked backend. Runtime installation is
offline, without dependency resolution, build tools or compiled package caches.
The image uses UID 10001 and the existing single-worker/no-access-log command.

CI installs each built wheel into a fresh environment outside the checkout using
hash-checked runtime wheels. `tools/dependency_smoke.py` exercises the installed
template, offline app construction, Fernet roundtrip/expiry/tamper rejection and
encrypted SQLite restart/renewal rotation/replay denial. Docker runs that same
smoke and `pip check`, checks UID, and exports its final filesystem for inspection.
No real server or credentials are needed.

`tools/package_check.py` compares package bytes with tracked Python/template
source and license/NOTICE files and emits a path/SHA256 manifest. Wheel metadata
is limited to the expected dist-info files; unknown package files fail the check.
The Docker context is an allowlist of build metadata, Python/template source and
bootstrap requirements. CI exports the actual filtered context using a temporary
scratch build and compares its exact file list and bytes. Synthetic secret,
media and SQLite canaries at root and inside the source tree must be absent from
the wheel, context and final image. The final image check also rejects application
state/build directories and build/test tools. These are content-boundary checks,
not a substitute for reviewing new source or scanning secrets; final filesystem
inspection alone does not scan removed files in image layers. The context check
prevents the injected local files from entering the build in the first place.
Hatch file-selection semantics are documented in the
[official build configuration](https://hatch.pypa.io/latest/config/build/).

To repeat the canary check, use a clean disposable checkout, run
`python -m tools.package_check seed` before building and `clean` afterward.
Seeding refuses existing paths; cleanup only deletes the exact synthetic bytes.
Never put real credentials or private media in a build tree for testing.

## Update review procedure

Weekly Dependabot PRs cover uv application/build locks, pip bootstrap requirements,
SHA-pinned Actions and Docker inputs including Compose. Updates are review-only;
there is no automatic merge or production deployment. Keep credentials disabled,
permissions minimal and the required check names intact when updating Actions.

1. Read the actual diff and upstream release/security/compatibility notes. Check
   Python/platform minimums, available wheels and persisted-data compatibility.
   Avoid unrelated upgrades and do not treat a bot compatibility score as proof.
2. For images, retrieve the official index and child manifests; independently
   compute the response digest. Review the underlying runtime/OS release and pin
   the same chosen index in both Python stages. Compose is the Caddy source of
   truth; CI reads its image reference instead of duplicating a floating tag.
3. For Python, update intended constraints, run `uv lock` deliberately and inspect
   every changed version/hash. Retain hashes in exports and bootstrap requirements.
   For a backend update change both exact requirements. Do not edit lock hashes
   by hand or disable TLS/hash checks to repair a build.
4. Run the full frozen matrix, wheel/runtime dependency smoke, real Docker/proxy/
   context/image checks, synthetic HTTP contract and redacted full-history secret
   scan. Record failures and fixes; CI must not use operator accounts or media.
5. Independently review the final head, resolve all actionable review threads and
   require actual branch-protection checks. Recheck an updated head; squash merge
   explicitly only after acceptance. Deployment remains separately authorized.

### Existing cryptography update #44

**Implemented / automated-tested update:** initial independent review of
[#44](https://github.com/alexanderhetzel/jellyfin-msx/pull/44) at
`e99bafd0f2b9573aeb3dc99acd928d69e20b4e8a` found only the `<49` to `<51` constraint
change and 48.0.1 to 50.0.0 lock change. All 40 cryptography artifact URLs/hashes
matched official PyPI. Isolated Python 3.12.14 Fernet compatibility in both version
directions passed roundtrip, TTL expiry, tampering and wrong-key denial. This
project uses Fernet/InvalidToken, not the removed asymmetric APIs or PKCS#7 API
affected by the v50 fix. Version 49 drops Intel macOS/32-bit Windows wheels.
The [official changelog](https://cryptography.io/en/latest/changelog/) already lists
50.0.2 with newer bundled OpenSSL, and that PR's base predates current main.
The original candidate was held while the same PR was refreshed onto current
main with `cryptography>=50.0.2,<51` and lock 50.0.2. Independent final review of
`43e4c5e85779e9e3233b902fa12ea4b7a5523a32` verified all 53 new artifact URLs/hashes
against official PyPI, unchanged unrelated dependencies and 48.0.1 ↔ 50.0.2 Fernet
compatibility in both directions. Full Windows/Linux matrix, Docker/proxy/wheel,
secret scan and CodeQL checks passed, with no open review threads. PR #44 was
explicitly squash merged as `e30e1cd6f68e7652ba1d325ef175c9e398c09bf0`.
Old 48.0.1 falls inside the ranges of
[GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c),
[GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww) and
[GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5). No affected
API path was identified in the current application; the update still removes
those known affected dependency versions. No production database migration or
MSX/device pass follows from the synthetic tests. No duplicate major-update PR
was created.
