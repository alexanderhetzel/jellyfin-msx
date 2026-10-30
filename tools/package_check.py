"""Inspect real build outputs against tracked source; never print file contents."""

import argparse
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CANARY = b"SYNTHETIC_PACKAGING_CANARY_NO_SECRET\n"
CANARY_PATHS = (
    ".env.supply-chain-canary",
    ".lab/supply-chain-canary.txt",
    "secrets/supply-chain-canary.key",
    "media/supply-chain-canary.mkv",
    "supply-chain-canary.sqlite",
    "src/jellyfin_msx/.env.supply-chain-canary",
    "src/jellyfin_msx/supply-chain-canary.sqlite",
    "src/jellyfin_msx/templates/supply-chain-canary.key",
)


def package_sources(root: Path) -> dict[str, bytes]:
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z", "--", "src/jellyfin_msx"], cwd=root)
        .decode()
        .split("\0")
    )
    return {
        name.removeprefix("src/"): (root / name).read_bytes()
        for name in tracked
        if name.endswith((".py", ".html"))
    }


def check_files(actual: dict[str, bytes], expected: dict[str, bytes]) -> None:
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = actual.keys() - expected.keys()
        # Unexpected operator filenames may be private; only identify known canaries.
        canaries = sorted(name for name in extra if "supply-chain-canary" in name)
        raise ValueError(
            f"Package/context file allowlist mismatch: missing reviewed {missing}; "
            f"{len(extra)} unexpected files; synthetic canaries {canaries}"
        )
    if any(actual[name] != expected[name] for name in expected):
        raise ValueError("Packaged bytes differ from reviewed source")
    if any(CANARY in data for data in actual.values()):
        raise ValueError("Synthetic exclusion canary leaked")


def seed(root: Path) -> None:
    # Preflight before any write; never overwrite operator files.
    if any((root / name).exists() or (root / name).is_symlink() for name in CANARY_PATHS):
        raise ValueError("Canary path already exists")
    for name in CANARY_PATHS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(CANARY)


def clean(root: Path) -> None:
    for name in CANARY_PATHS:
        path = root / name
        if path.is_file() and path.read_bytes() == CANARY:
            path.unlink()


def wheel_files(path: Path, root: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate wheel members")
        files = {name: archive.read(name) for name in names}
    expected = package_sources(root)
    info = "jellyfin_msx-0.1.0.dist-info/"
    for name in ("METADATA", "WHEEL", "RECORD"):
        if info + name not in files:
            raise ValueError("Missing wheel metadata")
        expected[info + name] = files[info + name]
    for name in ("LICENSE", "NOTICE.md"):
        expected[info + "licenses/" + name] = (root / name).read_bytes()
    check_files(files, expected)
    return files


def context_files(path: Path, root: Path) -> dict[str, bytes]:
    expected = {"src/" + name: data for name, data in package_sources(root).items()}
    for name in (
        "pyproject.toml",
        "uv.lock",
        "LICENSE",
        "NOTICE.md",
        "tools/requirements.txt",
    ):
        expected[name] = (root / name).read_bytes()
    files = {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    check_files(files, expected)
    return files


def image_files(path: Path, root: Path) -> dict[str, bytes]:
    """Inspect the exported final filesystem, without unpacking an untrusted tar."""
    files = {}
    prefix = "usr/local/lib/python3.12/site-packages/"
    with tarfile.open(path, "r|*") as archive:
        for member in archive:
            name = str(PurePosixPath(member.name)).removeprefix("./")
            if "supply-chain-canary" in name or name.startswith(("app/", "wheels/", "build/")):
                raise ValueError("Local/build/runtime state present in final image")
            if not name.startswith(prefix):
                continue
            relative = name.removeprefix(prefix)
            if relative.split("/", 1)[0].split("-", 1)[0] in {
                "uv",
                "uvx",
                "hatchling",
                "pytest",
                "_pytest",
                "ruff",
                "tomlkit",
                "pathspec",
            }:
                raise ValueError("Build/test tool present in runtime image")
            if relative.startswith("jellyfin_msx/") and member.isfile():
                stream = archive.extractfile(member)
                assert stream is not None
                files[relative] = stream.read()
    check_files(files, package_sources(root))
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("seed", "clean", "wheel", "context", "image"))
    parser.add_argument("path", nargs="?", type=Path)
    args = parser.parse_args()
    if args.kind in ("seed", "clean"):
        {"seed": seed, "clean": clean}[args.kind](ROOT)
        return
    if args.path is None:
        parser.error("artifact path required")
    files = {"wheel": wheel_files, "context": context_files, "image": image_files}[args.kind](
        args.path, ROOT
    )
    print(
        json.dumps({name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())})
    )


if __name__ == "__main__":
    main()
