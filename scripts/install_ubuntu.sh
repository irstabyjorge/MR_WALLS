#!/usr/bin/env bash
set -Eeuo pipefail
root="${1:-$HOME/JEFEAGUILA}"
umask 077
mkdir -p "$root"/{config,docs,evidence/01_ORIGINALS_READ_ONLY,evidence/02_WORKING_COPIES,evidence/03_REPORTS,logs,tools}
printf '{"name":"JEFEAGUILA","installed_utc":"%s","root":"%s","platform":"Ubuntu","evidence_policy":"preserve_originals"}\n' "$(date -u +%FT%TZ)" "$root" > "$root/config/installation.json"
printf 'JEFEAGUILA installed at %s\n' "$root"
printf 'No firewall, startup, privilege, or security policy was changed.\n'
