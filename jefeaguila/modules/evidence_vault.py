"""Read-only file fingerprinting for an evidence inventory.

This module hashes files in place. It does not modify, move, delete, or upload them.
A hash supports byte-integrity checks; it does not establish authenticity or truth.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CHUNK_SIZE = 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint_file(file_path: str | os.PathLike[str]) -> dict[str, object]:
    """Return a SHA-256 fingerprint without changing the source file."""
    path = Path(file_path).expanduser()
    if path.is_symlink():
        raise ValueError(f"Refusing to follow symbolic link: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Not a regular file: {path}")

    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    after = path.stat()

    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise RuntimeError(f"File changed while being fingerprinted: {path}")

    return {
        "path": str(path.resolve()),
        "size_bytes": after.st_size,
        "observed_mtime_utc": datetime.fromtimestamp(
            after.st_mtime, timezone.utc
        ).isoformat(),
        "fingerprinted_at_utc": _utc_now(),
        "algorithm": "SHA-256",
        "digest": digest.hexdigest(),
        "interpretation_limit": (
            "The digest identifies the observed bytes; it does not prove "
            "authorship, origin, ownership, or the truth of the file contents."
        ),
    }


def create_manifest(paths: Iterable[str | os.PathLike[str]]) -> dict[str, object]:
    """Fingerprint each supplied file and return a deterministic path ordering."""
    entries = [fingerprint_file(path) for path in paths]
    entries.sort(key=lambda item: str(item["path"]))
    return {
        "manifest_type": "JEFEAGUILA_EVIDENCE_FINGERPRINTS",
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "hash_algorithm": "SHA-256",
        "file_count": len(entries),
        "files": entries,
    }


def verify_fingerprint(file_path: str | os.PathLike[str], expected_digest: str) -> bool:
    """Return whether the current file bytes match a previously recorded SHA-256."""
    if len(expected_digest) != 64:
        raise ValueError("A SHA-256 digest must contain exactly 64 hexadecimal characters.")
    try:
        int(expected_digest, 16)
    except ValueError as exc:
        raise ValueError("Expected digest is not hexadecimal.") from exc
    current = fingerprint_file(file_path)
    return current["digest"].lower() == expected_digest.lower()


def write_manifest(manifest: dict[str, object], output_path: str | os.PathLike[str]) -> Path:
    """Write a JSON manifest to the explicitly selected destination."""
    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary.write_text(encoded, encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(destination)
    return destination
