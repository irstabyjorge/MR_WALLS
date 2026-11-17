import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ollama import Client

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "JEFEAGUILA_SYSTEM.md"
CONFIG_PATH = ROOT / "config" / "communication.json"
DATA_PATH = ROOT / "data"
HISTORY_PATH = DATA_PATH / "chat_history.jsonl"

HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("JEFEAGUILA_MODEL", "llama3.2:3b")
MEMORY_ENABLED = os.getenv("JEFEAGUILA_MEMORY", "1").lower() not in {"0", "false", "off"}
MAX_HISTORY_BYTES = 5_000_000


def load_recent(limit: int) -> list[dict[str, str]]:
    if not MEMORY_ENABLED or not HISTORY_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in HISTORY_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            rows.append({"role": item["role"], "content": item["content"]})
    return rows[-limit:]


def rotate_history() -> Path | None:
    if not HISTORY_PATH.exists() or HISTORY_PATH.stat().st_size < MAX_HISTORY_BYTES:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    for index in range(1000):
        backup = HISTORY_PATH.with_name(f"{HISTORY_PATH.stem}.{stamp}.{index}.previous")
        try:
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as destination, HISTORY_PATH.open("rb") as source:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            if backup.stat().st_size != HISTORY_PATH.stat().st_size:
                raise OSError("history archive size verification failed")
            HISTORY_PATH.unlink()
            return backup
        except Exception:
            try:
                backup.unlink()
            except OSError:
                pass
            raise
    raise FileExistsError("unable to allocate a unique history archive name")


def remember(role: str, content: str) -> None:
    if not MEMORY_ENABLED:
        return
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    rotate_history()
    with HISTORY_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + "\n")


def main() -> None:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    limit = max(0, min(int(config["local_memory"]["max_messages_sent_to_model"]), 100))
    client = Client(host=HOST)

    memory_status = "activa" if MEMORY_ENABLED else "desactivada"
    print(f"JEFEAGUILA conectado a {MODEL}. Memoria {memory_status}. Escribe /salir para terminar.")
    while True:
        try:
            user_text = input("\nTU> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJEFEAGUILA cerrado.")
            return

        if not user_text:
            continue
        if user_text.lower() in {"/salir", "/exit", "/quit"}:
            print("JEFEAGUILA cerrado.")
            return

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(load_recent(limit))
        messages.append({"role": "user", "content": user_text})

        try:
            response = client.chat(model=MODEL, messages=messages)
            raw_answer = response.message.content
            answer = raw_answer.strip() if isinstance(raw_answer, str) else ""
            if not answer:
                answer = "El modelo local devolvió una respuesta vacía."
        except Exception as exc:
            print(f"\nERROR: {exc}")
            continue

        print(f"\nJEFEAGUILA> {answer}")
        remember("user", user_text)
        remember("assistant", answer)


if __name__ == "__main__":
    main()
