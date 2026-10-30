# Source provenance and licensing status

This project's application code, tests and documents were written independently
for the current workspace. No application code, assets or model definitions were
copied from SerhiyRomanov/jellyfin-msx. Its inspected revision and licensing
limitations are recorded in `docs/research.md`.

The independently authored implementation on this fork's `main` branch is
licensed under MIT; see `LICENSE`. This covers the new `src/jellyfin_msx` package,
its tests, tools, deployment configuration and documentation. The owner selected
MIT on 2026-10-30.

The repository is a GitHub fork of SerhiyRomanov/jellyfin-msx. Its original
`master` branch and inherited commits retain their original authorship and
licensing status. Upstream revision `6bba5553466cd30e52e8bf1908eaa65ff2689aea`
contains no source license grant. Our MIT license does not relicense upstream
code or historical snapshots, nor grant additional rights in them. The current
`main` source tree excludes those original application packages and assets.

Media Station X is a separate third-party runtime. We use its published API and
hosted web client; its proprietary runtime is not included or relicensed. Philips
manuals, Jellyfin and other referenced material retain their respective rights.

Third-party Python packages, container images and build tools retain their own
licenses. Dependency names and resolved versions are recorded in `uv.lock`;
dependencies are installed from their package distributions, not vendored here.
