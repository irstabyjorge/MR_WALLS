import json
import py_compile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
json.loads((root / "config" / "jefeaguila.json").read_text(encoding="utf-8"))
json.loads((root / "config" / "communication.json").read_text(encoding="utf-8"))
assert (root / "prompts" / "JEFEAGUILA_SYSTEM.md").read_text(encoding="utf-8").strip()
for path in (root / "examples").glob("*.py"):
    py_compile.compile(str(path), doraise=True)
print("JEFEAGUILA validation passed")
