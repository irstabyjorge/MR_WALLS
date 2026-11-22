"""Create and export evidence dossiers from supplied source material.

No asset recovery, ownership adjudication, or external-entity attribution is performed.
All supplied assertions remain attributed to their source and classification.
"""
from __future__ import annotations

import csv
import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ALLOWED_CLASSIFICATIONS = {
    "CONFIRMED_FACT",
    "TECHNICAL_DATA",
    "USER_STATEMENT",
    "INFERENCE",
    "HYPOTHESIS",
    "CONTRADICTED",
    "UNVERIFIED",
}


class FrozenDict(dict):
    """JSON-serializable dictionary that prevents mutation of nested dossier data."""

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Dossier nested data is immutable; create a new dossier to revise it.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _atomic_text_write(destination: Path, write_callback: Any) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            write_callback(stream)
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


def _safe_csv_cell(value: Any) -> Any:
    """Neutralize spreadsheet formula markers in caller-controlled string cells."""
    if not isinstance(value, str):
        return value
    probe = value.lstrip(" \t\r\n")
    if value.startswith(("\t", "\r", "\n")) or (
        probe and probe[0] in {"=", "+", "-", "@"}
    ):
        return "'" + value
    return value


def verify_dossier(dossier: Mapping[str, Any]) -> bool:
    """Verify SHA-512 over every dossier field except the digest envelope itself."""
    integrity = dossier.get("integrity")
    if not isinstance(integrity, Mapping) or integrity.get("algorithm") != "SHA-512":
        return False
    expected = integrity.get("digest")
    if not isinstance(expected, str) or len(expected) != 128:
        return False
    try:
        int(expected, 16)
        payload = dict(dossier)
        payload.pop("integrity", None)
        actual = hashlib.sha512(_canonical_bytes(payload)).hexdigest()
    except (TypeError, ValueError):
        return False
    return actual == expected.lower()


class DossierEngine:
    """Build SHA-512 integrity records for user-supplied evidence data."""

    def create(
        self,
        target: str,
        data: Mapping[str, Any],
        actor: str,
        classification: str = "UNVERIFIED",
        source_reference: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(target, str) or not target.strip():
            raise ValueError("target must be a non-empty string")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string")
        classification = classification.upper()
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError(f"Unsupported classification: {classification}")
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")

        copied_data = copy.deepcopy(dict(data))
        created_at = _now_utc()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "dossier_for": target.strip(),
            "created_at_utc": created_at,
            "created_by": actor.strip(),
            "classification": classification,
            "source_reference": source_reference,
            "data": copied_data,
            "interpretation_limit": (
                "The digest detects changes to all serialized dossier metadata, provenance, and data. "
                "It does not prove the truth, authorship, ownership, or legal status "
                "of the supplied information."
            ),
            "provenance": [
                {
                    "actor": actor.strip(),
                    "action": "Dossier generated from supplied data",
                    "recorded_at_utc": created_at,
                }
            ],
        }
        digest = hashlib.sha512(_canonical_bytes(payload)).hexdigest()
        frozen_payload = _freeze(payload)
        result = dict(frozen_payload)
        result["integrity"] = FrozenDict({"algorithm": "SHA-512", "digest": digest})
        return result

    @staticmethod
    def export_json(
        dossiers: Mapping[str, Any] | list[dict[str, Any]],
        output_path: str | os.PathLike[str],
    ) -> Path:
        destination = Path(output_path).expanduser()
        encoded = json.dumps(dossiers, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        json.loads(encoded)
        return _atomic_text_write(destination, lambda stream: stream.write(encoded))

    @staticmethod
    def export_csv(dossiers: list[dict[str, Any]], output_path: str | os.PathLike[str]) -> Path:
        destination = Path(output_path).expanduser()
        fields = [
            "dossier_for", "created_at_utc", "created_by", "classification",
            "source_reference", "data_json", "provenance_json", "hash_algorithm", "hash_digest",
        ]

        def write(stream: Any) -> None:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for dossier in dossiers:
                integrity = dossier.get("integrity") or {}
                data_json = json.dumps(dossier.get("data", {}), ensure_ascii=False, sort_keys=True)
                provenance_json = json.dumps(
                    dossier.get("provenance", []), ensure_ascii=False, sort_keys=True
                )
                row = {
                    "dossier_for": dossier.get("dossier_for", ""),
                    "created_at_utc": dossier.get("created_at_utc", ""),
                    "created_by": dossier.get("created_by", ""),
                    "classification": dossier.get("classification", ""),
                    "source_reference": dossier.get("source_reference") or "",
                    "data_json": data_json,
                    "provenance_json": provenance_json,
                    "hash_algorithm": integrity.get("algorithm", ""),
                    "hash_digest": integrity.get("digest", ""),
                }
                writer.writerow({key: _safe_csv_cell(value) for key, value in row.items()})

        return _atomic_text_write(destination, write)
