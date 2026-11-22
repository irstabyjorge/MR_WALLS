"""Runtime registry linking configuration to implemented modules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jefeaguila.modules.dossier_engine import DossierEngine, verify_dossier
from jefeaguila.modules.evidence_vault import create_manifest, fingerprint_file, verify_fingerprint


IMPLEMENTATIONS = {
    "local_ai_chat": {
        "implementation": "examples.interactive_chat",
        "exports": ["main"],
    },
    "evidence_vault": {
        "implementation": "jefeaguila.modules.evidence_vault",
        "exports": ["create_manifest", "fingerprint_file", "verify_fingerprint"],
    },
    "reporting": {
        "implementation": "jefeaguila.modules.dossier_engine",
        "exports": ["DossierEngine", "verify_dossier"],
    },
}


def _validate_configuration(config: dict[str, Any]) -> None:
    modules = config.get("modules")
    if not isinstance(modules, dict):
        raise ValueError("Configuration must contain a modules object.")
    for name, settings in modules.items():
        if not isinstance(settings, dict):
            raise ValueError(f"Module configuration for {name!r} must be an object.")
        if "enabled" in settings and not isinstance(settings["enabled"], bool):
            raise ValueError(f"Module {name!r} enabled value must be a boolean.")


def load_configuration(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "jefeaguila.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_configuration(config)
    return config


def module_status(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Report whether each configured module is implemented, configured-only, or disabled."""
    _validate_configuration(config)
    rows: list[dict[str, Any]] = []
    for name, settings in config["modules"].items():
        enabled = settings.get("enabled", False)
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


def get_runtime_components(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return entry points only for modules enabled in validated configuration."""
    if config is None:
        config = load_configuration()
    _validate_configuration(config)
    enabled = {
        name for name, settings in config["modules"].items()
        if settings.get("enabled", False)
    }
    available = {
        "local_ai_chat": {"entrypoint": "python -m examples.interactive_chat"},
        "evidence_vault": {
            "fingerprint_file": fingerprint_file,
            "create_manifest": create_manifest,
            "verify_fingerprint": verify_fingerprint,
        },
        "reporting": {
            "dossier_engine": DossierEngine(),
            "verify_dossier": verify_dossier,
        },
    }
    return {name: component for name, component in available.items() if name in enabled}
