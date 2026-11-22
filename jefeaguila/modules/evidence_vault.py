"""Read-only file fingerprinting for an evidence inventory.

The source is opened once, without following symlinks, and hashed through that
same descriptor. Access-time preservation is attempted without changing source
content or metadata. A digest proves byte identity only, not truth or authorship.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CHUNK_SIZE = 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint_file(file_path: str | os.PathLike[str]) -> dict[str, object]:
    """Fingerprint one regular file through a stable, non-following descriptor."""
    path = Path(file_path).expanduser()
    try:
        path_before = path.lstat()
    except FileNotFoundError:
        raise
    if stat.S_ISLNK(path_before.st_mode):
        raise ValueError(f"Refusing to follow symbolic link: {path}")
    if not stat.S_ISREG(path_before.st_mode):
        raise FileNotFoundError(f"Not a regular file: {path}")

    flags = os.O_RDONLY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    noatime = getattr(os, "O_NOATIME", 0)
    if nofollow:
        flags |= nofollow

    used_noatime = False
    if noatime:
        try:
            fd = os.open(path, flags | noatime)
            used_noatime = True
        except OSError as exc:
            if exc.errno not in {errno.EPERM, errno.EINVAL, getattr(errno, "EOPNOTSUPP", errno.EINVAL)}:
                raise
            fd = os.open(path, flags)
    else:
        fd = os.open(path, flags)

    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"Refusing non-regular file: {path}")
        if (before.st_dev, before.st_ino) != (path_before.st_dev, path_before.st_ino):
            raise RuntimeError(f"File identity changed while opening: {path}")

        digest = hashlib.sha256()
        with os.fdopen(os.dup(fd), "rb") as stream:
            while chunk := stream.read(CHUNK_SIZE):
                digest.update(chunk)

        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise RuntimeError(f"File changed while being fingerprinted: {path}")

        if not used_noatime and after.st_atime_ns != before.st_atime_ns:
            try:
                os.utime(fd, ns=(before.st_atime_ns, before.st_mtime_ns))
            except (TypeError, NotImplementedError, OSError):
                current = path.lstat()
                if stat.S_ISLNK(current.st_mode) or (
                    current.st_dev, current.st_ino
                ) != (before.st_dev, before.st_ino):
                    raise RuntimeError(f"Cannot safely restore access time for replaced file: {path}")
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            restored = os.fstat(fd)
            if restored.st_atime_ns != before.st_atime_ns:
                raise RuntimeError(f"Could not preserve source access time: {path}")

        current = path.lstat()
        if stat.S_ISLNK(current.st_mode) or (current.st_dev, current.st_ino) != (
            before.st_dev, before.st_ino
        ):
            raise RuntimeError(f"File path changed while being fingerprinted: {path}")

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
    finally:
        os.close(fd)


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


def write_manifest(
    manifest: dict[str, object],
    output_path: str | os.PathLike[str],
    source_paths: Iterable[str | os.PathLike[str]] = (),
) -> Path:
    """Atomically write a manifest without replacing any fingerprinted source."""
    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_identity = destination.resolve(strict=False)
    for source in source_paths:
        source_identity = Path(source).expanduser().resolve(strict=True)
        if output_identity == source_identity:
            raise ValueError("Manifest output must not identify any fingerprinted source file.")

    encoded = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    json.loads(encoded)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return destination
