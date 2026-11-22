# JEFEAGUILA module integration

## Implemented in this revision

- `jefeaguila.modules.evidence_vault`: read-only SHA-256 fingerprinting, manifest generation, and digest verification.
- `jefeaguila.modules.dossier_engine`: source-attributed dossiers with canonical SHA-512 integrity digests and JSON/CSV export.
- `jefeaguila.registry`: validates module configuration, maps enabled entries to implementations, withholds disabled modules, and clearly reports configured-only modules.
- `jefeaguila.cli`: local commands for module status, file fingerprinting, and dossier creation.

## Legacy SiliconOracle migration boundary

The uploaded `SiliconOracle.py` contains a simulated global sweep, pseudo-random entity selection using Python's process-randomized `hash()`, fabricated-looking patent/grant identifiers and values, and labels suggesting that assets were recovered or ownership was established. Those outputs are not verified records and must not be ingested as evidence of real theft, ownership, production, or recovery.

This revision migrates only the defensible engineering patterns: timestamped dossier generation, structured JSON/CSV export, and cryptographic integrity checks. It deliberately excludes simulated asset recovery, ownership assertions, invented entity associations, and non-deterministic pseudo-identifiers.

## Run locally

```bash
python -m jefeaguila.cli status
python -m jefeaguila.cli fingerprint ./path/to/evidence.pdf --output ./manifest.json
printf '%s' '{"note":"source-supplied description"}' | python -m jefeaguila.cli dossier --target REF-001 --actor local-user --classification USER_STATEMENT --data-stdin --output ./dossier.json
```

The fingerprint command opens each source through a stable descriptor, rejects symlinks and output paths that identify source files, and preserves access-time metadata where supported. Exports use unique exclusive temporary files and atomic replacement. Dossier data is read from standard input or a permission-restricted file, nested data is copied and frozen, and CSV output includes data/provenance while neutralizing spreadsheet formula markers. Store manifests and dossiers in a separate working or reporting directory.

## Module state semantics

- `implemented`: a concrete local implementation is registered.
- `configured_only`: enabled in configuration but no executable implementation is registered in this repository.
- `disabled`: configuration disables the module.

A configured name is not evidence that an operational module exists. No network scanning, remote access, background daemon, or external write operation is started by the registry or CLI.
