# JEFEAGUILA

JEFEAGUILA unifies the tools previously described as AEGIS, MR_WALLS, HOMO_DEUS, Desktop Commander, and Evidence Trace into a local-first platform.

## Current capabilities

- Local chat through Ollama.
- Authorized desktop operations with confirmation before writes.
- Read-only evidence fingerprinting with SHA-256.
- Evidence manifests and integrity verification.
- Provenance-aware dossiers with SHA-512 integrity digests.
- JSON and CSV dossier exports.
- Multidimensional analysis configuration: temporal, personal, institutional, documentary, technical, medical/scientific, legal, financial, geographic, and evidentiary.
- Defensive audit configuration for Windows and Ubuntu.

## Quick start

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Inspect the module registry:

```bash
python -m jefeaguila.cli status
```

Fingerprint files without modifying them:

```bash
python -m jefeaguila.cli fingerprint ./evidence/example.pdf --output ./reports/manifest.json
```

Create a source-attributed dossier:

```bash
python -m jefeaguila.cli dossier --target REF-001 --actor local-user --classification USER_STATEMENT --data-json '{"note":"description supplied by the source"}' --output ./reports/dossier.json
```

Run validation:

```bash
python -m unittest discover -s tests -v
npm run check
bash -n scripts/install_ubuntu.sh
```

## Evidence doctrine

JEFEAGUILA never presents an inference as a fact. A hash demonstrates byte integrity, not truth, authorship, or ownership. An open port does not prove intrusion; an IP address does not by itself identify a person; and technological similarity does not establish appropriation.

Original evidence must remain unchanged. Fingerprinting reads files in place. Reports and manifests should be stored separately from original evidence.

## Module state

The runtime registry distinguishes implemented modules from modules that are only configured. An enabled configuration entry is not proof that a corresponding operational implementation exists.

## Authorization and privacy

All operations are limited to owner-controlled, public, legally delivered, or expressly authorized sources. No unauthorized remote access or offensive actions are implemented. Do not place passwords, API keys, OAuth tokens, CURP, RFC, or full government identifiers in source code, prompts, logs, or Git history.
