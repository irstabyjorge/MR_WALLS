"""Small local CLI for module status and evidence integrity operations."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Sequence

from jefeaguila.modules.dossier_engine import DossierEngine
from jefeaguila.modules.evidence_vault import create_manifest, write_manifest
from jefeaguila.registry import load_configuration, module_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jefeaguila", description="Local-first JEFEAGUILA utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Show configured and implemented modules")
    status.add_argument("--config", help="Path to configuration JSON")

    fingerprint = sub.add_parser("fingerprint", help="Create a read-only SHA-256 inventory")
    fingerprint.add_argument("files", nargs="+", help="Files to fingerprint")
    fingerprint.add_argument("--output", help="Optional JSON manifest destination")

    dossier = sub.add_parser("dossier", help="Create a dossier from supplied JSON data")
    dossier.add_argument("--target", required=True)
    dossier.add_argument("--actor", required=True)
    data_source = dossier.add_mutually_exclusive_group(required=True)
    data_source.add_argument("--data-file", help="Read JSON from a private file; on POSIX it must not be group/world accessible")
    data_source.add_argument("--data-stdin", action="store_true", help="Read JSON from standard input")
    dossier.add_argument("--classification", default="UNVERIFIED")
    dossier.add_argument("--source-reference")
    dossier.add_argument("--output", help="Optional JSON output destination")
    return parser


def _read_dossier_data(args: argparse.Namespace) -> dict:
    if args.data_stdin:
        raw = sys.stdin.read()
    else:
        path = Path(args.data_file).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("Dossier input must be a regular, non-symlink file.")
        metadata = path.stat()
        if os.name != "nt" and stat.S_IMODE(metadata.st_mode) & 0o077:
            raise PermissionError("Dossier input file must be private (chmod 600).")
        raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Dossier input must decode to a JSON object.")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            config = load_configuration(args.config)
            print(json.dumps(module_status(config), ensure_ascii=False, indent=2))
            return 0

        if args.command == "fingerprint":
            manifest = create_manifest(args.files)
            if args.output:
                print(write_manifest(manifest, args.output, source_paths=args.files))
            else:
                print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return 0

        if args.command == "dossier":
            data = _read_dossier_data(args)
            result = DossierEngine().create(
                target=args.target,
                data=data,
                actor=args.actor,
                classification=args.classification,
                source_reference=args.source_reference,
            )
            if args.output:
                DossierEngine.export_json(result, args.output)
                print(Path(args.output).expanduser())
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
