import csv
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jefeaguila.cli import build_parser, main
from jefeaguila.modules.dossier_engine import DossierEngine, verify_dossier
from jefeaguila.modules.evidence_vault import fingerprint_file, verify_fingerprint, write_manifest
from jefeaguila.registry import get_runtime_components, load_configuration, module_status


class EvidenceVaultTests(unittest.TestCase):
    def test_fingerprint_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_text("original evidence", encoding="utf-8")
            record = fingerprint_file(path)
            self.assertEqual(record["algorithm"], "SHA-256")
            self.assertEqual(record["digest"], hashlib.sha256(b"original evidence").hexdigest())
            self.assertTrue(verify_fingerprint(path, record["digest"]))
            path.write_text("changed evidence", encoding="utf-8")
            self.assertFalse(verify_fingerprint(path, record["digest"]))

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            link = Path(tmp) / "link.txt"
            source.write_text("data", encoding="utf-8")
            try:
                link.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is unavailable on this platform.")
            with self.assertRaises(ValueError):
                fingerprint_file(link)

    def test_manifest_cannot_replace_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            source.write_text("original bytes", encoding="utf-8")
            original = source.read_bytes()
            manifest = {"file_count": 1}
            with self.assertRaises(ValueError):
                write_manifest(manifest, source, source_paths=[source])
            self.assertEqual(source.read_bytes(), original)

    def test_manifest_uses_unique_temporary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "manifest.json"
            collision = Path(tmp) / "manifest.json.tmp"
            collision.write_text("preserve this unrelated file", encoding="utf-8")
            write_manifest({"ok": True}, destination)
            self.assertEqual(collision.read_text(encoding="utf-8"), "preserve this unrelated file")
            self.assertTrue(json.loads(destination.read_text(encoding="utf-8"))["ok"])

    def test_fingerprint_preserves_access_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_text("atime test", encoding="utf-8")
            before = path.stat()
            os.utime(path, ns=(before.st_atime_ns - 5_000_000_000, before.st_mtime_ns))
            expected_atime = path.stat().st_atime_ns
            fingerprint_file(path)
            self.assertEqual(path.stat().st_atime_ns, expected_atime)


class DossierEngineTests(unittest.TestCase):
    def test_dossier_digest_covers_data_and_provenance(self):
        dossier = DossierEngine().create(
            target="sample-record",
            data={"reference": "REF-001", "nested": {"note": "user-supplied"}},
            actor="local-user",
            classification="USER_STATEMENT",
        )
        self.assertEqual(dossier["integrity"]["algorithm"], "SHA-512")
        payload = dict(dossier)
        integrity = payload.pop("integrity")
        expected = hashlib.sha512(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(integrity["digest"], expected)
        self.assertEqual(dossier["provenance"][0]["actor"], "local-user")
        self.assertTrue(verify_dossier(dossier))
        tampered = dict(dossier)
        tampered["provenance"] = [{"actor": "changed"}]
        self.assertFalse(verify_dossier(tampered))

    def test_nested_data_is_copied_and_immutable(self):
        source = {"nested": {"items": [1, 2]}}
        dossier = DossierEngine().create("sample", source, "tester")
        source["nested"]["items"].append(3)
        self.assertTrue(verify_dossier(dossier))
        self.assertEqual(list(dossier["data"]["nested"]["items"]), [1, 2])
        with self.assertRaises(TypeError):
            dossier["data"]["nested"]["new"] = "blocked"

    def test_invalid_classification_rejected(self):
        with self.assertRaises(ValueError):
            DossierEngine().create("x", {}, "local-user", "PROVEN_TRUE")

    def test_json_and_csv_exports_preserve_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = DossierEngine()
            dossier = engine.create("x", {"n": 1}, "tester")
            json_path = engine.export_json(dossier, Path(tmp) / "dossier.json")
            csv_path = engine.export_csv([dossier], Path(tmp) / "dossiers.csv")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["dossier_for"], "x")
            with csv_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0]["data_json"]), {"n": 1})
            self.assertEqual(json.loads(rows[0]["provenance_json"])[0]["actor"], "tester")
            self.assertEqual(rows[0]["hash_algorithm"], "SHA-512")
            self.assertEqual(rows[0]["dossier_for"], "x")

    def test_csv_formula_markers_are_neutralized(self):
        dossier = DossierEngine().create(
            target="=1+1",
            data={"note": "+cmd"},
            actor="@SUM(1,1)",
            source_reference="-source",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = DossierEngine.export_csv([dossier], Path(tmp) / "safe.csv")
            with path.open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertTrue(row["dossier_for"].startswith("'"))
            self.assertTrue(row["created_by"].startswith("'"))
            self.assertTrue(row["source_reference"].startswith("'"))


class RegistryTests(unittest.TestCase):
    def test_registry_connects_implemented_modules(self):
        config = load_configuration()
        statuses = {item["name"]: item["state"] for item in module_status(config)}
        self.assertEqual(statuses["local_ai_chat"], "implemented")
        self.assertEqual(statuses["evidence_vault"], "implemented")
        self.assertEqual(statuses["reporting"], "implemented")
        components = get_runtime_components(config)
        self.assertIn("fingerprint_file", components["evidence_vault"])
        self.assertIsInstance(components["reporting"]["dossier_engine"], DossierEngine)
        self.assertEqual(components["local_ai_chat"]["entrypoint"], "python -m examples.interactive_chat")

    def test_disabled_modules_are_not_exposed(self):
        config = {"modules": {"local_ai_chat": {"enabled": True}, "evidence_vault": {"enabled": False}, "reporting": {"enabled": False}}}
        components = get_runtime_components(config)
        self.assertEqual(set(components), {"local_ai_chat"})

    def test_malformed_module_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            module_status({"modules": {"evidence_vault": "disabled"}})


class CliTests(unittest.TestCase):
    def test_dossier_cli_reads_stdin_and_writes_same_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dossier.json"
            args = [
                "dossier", "--target", "REF-1", "--actor", "local-user",
                "--classification", "USER_STATEMENT", "--data-stdin", "--output", str(output),
            ]
            with patch("sys.stdin", io.StringIO('{"note":"stdin source"}')):
                self.assertEqual(main(args), 0)
            file_value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(file_value["dossier_for"], "REF-1")
            parsed = build_parser().parse_args([
                "dossier", "--target", "REF-1", "--actor", "local-user",
                "--data-stdin",
            ])
            self.assertTrue(parsed.data_stdin)

    def test_cli_no_longer_accepts_private_data_as_argv(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([
                "dossier", "--target", "x", "--actor", "y", "--data-json", '{"secret":"x"}',
            ])


if __name__ == "__main__":
    unittest.main()
