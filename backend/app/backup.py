"""Portable database/assets backup and offline restore into an empty directory."""

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath


def create_backup(engine, asset_dir, destination):
    with tempfile.TemporaryDirectory() as temp:
        database = Path(temp) / "studio.sqlite3"
        source = engine.raw_connection()
        try:
            with closing(sqlite3.connect(database)) as target:
                source.driver_connection.backup(target)
        finally:
            source.close()
        files = {"studio.sqlite3": database}
        root = Path(asset_dir).resolve()
        # Assets are immutable and written before their database rows. Select the
        # exact files referenced by the snapshot, including archived/removed items.
        with closing(sqlite3.connect(database)) as snapshot:
            for table, folder in (("reference_images", ""), ("artwork", "artwork/")):
                for (digest,) in snapshot.execute(f"SELECT DISTINCT digest FROM {table}"):
                    if not re.fullmatch(r"[a-f0-9]{64}", digest):
                        raise ValueError("Invalid stored asset digest.")
                    name = folder + digest + ".png"
                    path = root / name
                    if (
                        not path.is_file()
                        or path.is_symlink()
                        or not path.resolve().is_relative_to(root)
                    ):
                        raise ValueError(
                            "A referenced image is missing; repair storage before backing up."
                        )
                    with path.open("rb") as stored:
                        matches = hashlib.file_digest(stored, "sha256").hexdigest() == digest
                    if not matches:
                        raise ValueError("A stored image failed its integrity check.")
                    files["assets/" + name] = path
        if sum(p.stat().st_size for p in files.values()) > 2_000_000_000:
            raise ValueError("Portable backups currently support up to 2 GB.")
        manifest = {"version": 1, "files": {}}
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as pack:
            for name, path in files.items():
                with path.open("rb") as source:
                    manifest["files"][name] = hashlib.file_digest(source, "sha256").hexdigest()
                pack.write(path, name)
            pack.writestr("manifest.json", json.dumps(manifest))


def restore(archive, destination):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore destination must be empty. Existing work is never overwritten.")
    with zipfile.ZipFile(archive) as pack:
        entries = pack.infolist()
        names = [i.filename for i in entries]
        if (
            len(names) != len({n.casefold() for n in names})
            or len(names) > 100_000
            or sum(i.file_size for i in entries) > 2_000_000_000
        ):
            raise ValueError("Duplicate entries or backup exceeds 2 GB restore limit.")
        for name in names:
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or ":" in name
                or str(path) != name
                or any(
                    part.endswith((".", " "))
                    or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?", part)
                    for part in path.parts
                )
                or any(ord(c) < 32 or c in '<>"|?*' for c in name)
                or not (name in ("manifest.json", "studio.sqlite3") or name.startswith("assets/"))
            ):
                raise ValueError("Unsafe backup path.")
        if (
            "studio.sqlite3" not in names
            or "manifest.json" not in names
            or pack.getinfo("manifest.json").file_size > 10_000_000
        ):
            raise ValueError("Missing database or invalid backup manifest.")
        manifest = json.loads(pack.read("manifest.json"))
        if manifest.get("version") != 1 or set(manifest["files"]) != set(names) - {"manifest.json"}:
            raise ValueError("Invalid backup manifest.")
        # Validate everything before writing the requested destination.
        with tempfile.TemporaryDirectory() as temp:
            staged = Path(temp)
            for name, digest in manifest["files"].items():
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with pack.open(name) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                with target.open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() != digest:
                        raise ValueError("Backup checksum mismatch.")
            with closing(sqlite3.connect(staged / "studio.sqlite3")) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup database integrity check failed.")
                if not db.execute(
                    "SELECT name FROM sqlite_master WHERE name='schema_versions'"
                ).fetchone():
                    raise ValueError("Not a Variance database.")
            destination.mkdir(parents=True, exist_ok=True)
            for source in staged.rglob("*"):
                if source.is_file():
                    target = destination / source.relative_to(staged)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open("rb") as original, target.open("xb") as output:
                        shutil.copyfileobj(original, output, length=1024 * 1024)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    restore(args.archive, args.destination)
    print(
        "Restored. Stop the server, point DATABASE_URL and ASSET_DIR at this directory, then restart."
    )
