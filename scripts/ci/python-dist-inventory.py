#!/usr/bin/env python3
"""Bind the CI artifact roundtrip to the producer's wheel and sdist bytes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import zipfile


def inventory(directory: Path) -> list[dict]:
    files = sorted(directory.iterdir())
    if len(files) != 2 or any(not p.is_file() or p.is_symlink() for p in files):
        raise ValueError("expected exactly one wheel and one sdist, without extra entries")
    wheels = [p for p in files if p.name.endswith(".whl")]
    sdists = [p for p in files if p.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("expected exactly one wheel and one sdist")

    with zipfile.ZipFile(wheels[0]) as archive:
        if archive.testzip() is not None or not any(
            name.endswith(".dist-info/METADATA") for name in archive.namelist()
        ):
            raise ValueError("invalid wheel archive or missing METADATA")
    with tarfile.open(sdists[0], "r:gz") as archive:
        members = archive.getmembers()
        if not any(member.name.endswith("/PKG-INFO") for member in members):
            raise ValueError("sdist is missing PKG-INFO")
        for member in members:
            if member.isfile():
                with archive.extractfile(member) as stream:
                    while stream.read(1024 * 1024):
                        pass

    return [
        {"filename": p.name, "size": p.stat().st_size,
         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in files
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    actual = inventory(args.directory)
    if args.mode == "verify":
        expected = json.loads(os.environ["PYTHON_DIST_INVENTORY"])
        if actual != expected:
            raise ValueError("downloaded distribution inventory differs from producer")
        print("Producer inventory matched: filenames, sizes, SHA256 and package archives")
    print(json.dumps(actual, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
