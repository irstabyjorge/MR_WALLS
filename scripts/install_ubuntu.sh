#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-$HOME/JEFEAGUILA}"
umask 077

command -v python3 >/dev/null 2>&1 || {
  printf 'ERROR: python3 is required to write validated JSON.\n' >&2
  exit 1
}

mkdir -p "$root"/{config,docs,evidence/01_ORIGINALS_READ_ONLY,evidence/02_WORKING_COPIES,evidence/03_REPORTS,logs,tools}
config_path="$root/config/installation.json"

if [[ -f "$config_path" ]]; then
  backup_path="$config_path.before_$(date -u +%Y%m%d_%H%M%S).backup"
  cp -- "$config_path" "$backup_path"
  printf 'Previous configuration preserved: %s\n' "$backup_path"
fi

python3 - "$root" "$config_path.tmp" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root, output = sys.argv[1], Path(sys.argv[2])
state = {
    "name": "JEFEAGUILA",
    "installed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "root": root,
    "platform": "Ubuntu",
    "evidence_policy": "preserve_originals",
}
output.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
json.loads(output.read_text(encoding="utf-8"))
PY

mv -- "$config_path.tmp" "$config_path"
printf 'JEFEAGUILA installed at %s\n' "$root"
printf 'No firewall, startup, privilege, or security policy was changed.\n'
