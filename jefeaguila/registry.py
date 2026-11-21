"""Runtime registry linking configuration to implemented modules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jefeaguila.modules.dossier_engine import DossierEngine
from jefeaguila.modules.evidence_vault import create_manifest, fingerprint_file, verify_fingerprint


IMPLEMENTATIONS = {
    "evidence_vault": {
        "implementation": "jefeaguila.modules.evidence_vault",
        "exports": ["create_manifest", "fingerprint_file", "verify_fingerprint"],
    },
    "reporting": {
        "implementation": "jefeaguila.modules.dossier_engine",
        "exports": ["DossierEngine"],
    },
}


def load_configuration(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "jefeaguila.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config.get("modules"), dict):
        raise ValueError("Configuration must contain a modules object.")
    return config


def module_status(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Report whether each configured module is implemented, configured-only, or disabled."""
    rows: list[dict[str, Any]] = []
    for name, settings in config["modules"].items():
        enabled = bool(settings.get("enabled", False)) if isinstance(settings, dict) else False
        implementation = IMPLEMENTATIONS.get(name)
        if not enabled:
            state = "disabled"
        elif implementation:
            state = "implemented"
        else:
            state = "configured_only"
        rows.append({
            "name": name,
            "enabled": enabled,
            "state": state,
            "implementation": implementation["implementation"] if implementation else None,
        })
    return rows


def get_runtime_components() -> dict[str, Any]:
    """Return concrete module entry points; no background tasks are started."""
    return {
        "evidence_vault": {
            "fingerprint_file": fingerprint_file,
            "create_manifest": create_manifest,
            "verify_fingerprint": verify_fingerprint,
        },
        "reporting": {"dossier_engine": DossierEngine()},
    }
