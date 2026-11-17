import json
import py_compile
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
json.loads((root / "config" / "jefeaguila.json").read_text(encoding="utf-8"))
json.loads((root / "config" / "communication.json").read_text(encoding="utf-8"))
assert (root / "prompts" / "JEFEAGUILA_SYSTEM.md").read_text(encoding="utf-8").strip()
for path in (root / "examples").glob("*.py"):
    py_compile.compile(str(path), doraise=True)
print("JEFEAGUILA validation passed")

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(root))
sys.modules.setdefault("ollama", types.SimpleNamespace(Client=object))
from examples import interactive_chat


class HistoryRotationTests(unittest.TestCase):
    def test_rotation_preserves_existing_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / "chat_history.jsonl"
            history.write_bytes(b"current-history")
            stamp = "20261117T120000.123456Z"
            prior = history.with_name(f"{history.stem}.{stamp}.0.previous")
            prior.write_bytes(b"older-archive")

            class FrozenDateTime:
                @staticmethod
                def now(tz):
                    return datetime(2026, 11, 17, 12, 0, 0, 123456, tzinfo=timezone.utc)

            with patch.object(interactive_chat, "HISTORY_PATH", history), \
                 patch.object(interactive_chat, "MAX_HISTORY_BYTES", 1), \
                 patch.object(interactive_chat, "datetime", FrozenDateTime):
                archived = interactive_chat.rotate_history()

            self.assertEqual(prior.read_bytes(), b"older-archive")
            self.assertEqual(archived.read_bytes(), b"current-history")
            self.assertFalse(history.exists())


if __name__ == "__main__":
    unittest.main()
