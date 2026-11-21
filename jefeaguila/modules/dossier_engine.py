"""Create and export evidence dossiers from supplied source material.

No asset recovery, ownership adjudication, or external-entity attribution is performed.
All supplied assertions remain attributed to their source and classification.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
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


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


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

        created_at = _now_utc()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "dossier_for": target.strip(),
            "created_at_utc": created_at,
            "created_by": actor.strip(),
            "classification": classification,
            "source_reference": source_reference,
            "data": dict(data),
            "interpretation_limit": (
                "The digest detects changes to all serialized dossier metadata and data. "
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
        return {
            **payload,
            "integrity": {"algorithm": "SHA-512", "digest": digest},
        }

    @staticmethod
    def export_json(dossiers: list[dict[str, Any]], output_path: str | os.PathLike[str]) -> Path:
        destination = Path(output_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(
            json.dumps(dossiers, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(destination)
        return destination

    @staticmethod
    def export_csv(dossiers: list[dict[str, Any]], output_path: str | os.PathLike[str]) -> Path:
        destination = Path(output_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        fields = [
            "dossier_for", "created_at_utc", "created_by", "classification",
            "source_reference", "hash_algorithm", "hash_digest",
        ]
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for dossier in dossiers:
                integrity = dossier.get("integrity") or {}
                writer.writerow({
                    "dossier_for": dossier.get("dossier_for", ""),
                    "created_at_utc": dossier.get("created_at_utc", ""),
                    "created_by": dossier.get("created_by", ""),
                    "classification": dossier.get("classification", ""),
                    "source_reference": dossier.get("source_reference") or "",
                    "hash_algorithm": integrity.get("algorithm", ""),
                    "hash_digest": integrity.get("digest", ""),
                })
        temporary.replace(destination)
        return destination
