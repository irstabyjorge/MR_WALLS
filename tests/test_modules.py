import json
import tempfile
import unittest
from pathlib import Path

from jefeaguila.modules.dossier_engine import DossierEngine, verify_dossier
from jefeaguila.modules.evidence_vault import fingerprint_file, verify_fingerprint
from jefeaguila.registry import get_runtime_components, load_configuration, module_status


class EvidenceVaultTests(unittest.TestCase):
    def test_fingerprint_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_text("original evidence", encoding="utf-8")
            record = fingerprint_file(path)
            self.assertEqual(record["algorithm"], "SHA-256")
            self.assertTrue(verify_fingerprint(path, record["digest"]))
            path.write_text("changed evidence", encoding="utf-8")
            self.assertFalse(verify_fingerprint(path, record["digest"]))

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            link = Path(tmp) / "link.txt"
            source.write_text("data", encoding="utf-8")
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                fingerprint_file(link)


class DossierEngineTests(unittest.TestCase):
    def test_dossier_has_sha512_and_provenance(self):
        dossier = DossierEngine().create(
            target="sample-record",
            data={"reference": "REF-001", "note": "user-supplied"},
            actor="local-user",
            classification="USER_STATEMENT",
        )
        self.assertEqual(dossier["integrity"]["algorithm"], "SHA-512")
        self.assertEqual(len(dossier["integrity"]["digest"]), 128)
        self.assertEqual(dossier["classification"], "USER_STATEMENT")
        self.assertEqual(dossier["provenance"][0]["actor"], "local-user")
        self.assertTrue(verify_dossier(dossier))

    def test_changes_to_dossier_metadata_are_detected(self):
        dossier = DossierEngine().create("sample", {"note": "source"}, "tester")
        dossier["provenance"][0]["action"] = "modified after creation"
        self.assertFalse(verify_dossier(dossier))

    def test_invalid_classification_rejected(self):
        with self.assertRaises(ValueError):
            DossierEngine().create("x", {}, "local-user", "PROVEN_TRUE")

    def test_json_and_csv_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = DossierEngine()
            dossier = engine.create("x", {"n": 1}, "tester")
            json_path = engine.export_json([dossier], Path(tmp) / "dossiers.json")
            csv_path = engine.export_csv([dossier], Path(tmp) / "dossiers.csv")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))[0]["dossier_for"], "x")
            self.assertIn("hash_digest", csv_path.read_text(encoding="utf-8"))


class RegistryTests(unittest.TestCase):
    def test_registry_connects_implemented_modules(self):
        config = load_configuration()
        statuses = {item["name"]: item["state"] for item in module_status(config)}
        self.assertEqual(statuses["local_ai_chat"], "implemented")
        self.assertEqual(statuses["evidence_vault"], "implemented")
        self.assertEqual(statuses["reporting"], "implemented")
        components = get_runtime_components()
        self.assertIn("fingerprint_file", components["evidence_vault"])
        self.assertIsInstance(components["reporting"]["dossier_engine"], DossierEngine)
        self.assertEqual(components["local_ai_chat"]["entrypoint"], "python -m examples.interactive_chat")


if __name__ == "__main__":
    unittest.main()
