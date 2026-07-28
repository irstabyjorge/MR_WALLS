import json
import os
from pathlib import Path

from ollama import Client

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "JEFEAGUILA_SYSTEM.md"
CONFIG_PATH = ROOT / "config" / "communication.json"
DATA_PATH = ROOT / "data"
HISTORY_PATH = DATA_PATH / "chat_history.jsonl"

HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("JEFEAGUILA_MODEL", "llama3.2:3b")


def load_recent(limit: int) -> list[dict[str, str]]:
    if not HISTORY_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            rows.append({"role": item["role"], "content": item["content"]})
    return rows[-limit:]


def remember(role: str, content: str) -> None:
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + "\n")


def main() -> None:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    limit = int(config["local_memory"]["max_messages_sent_to_model"])
    client = Client(host=HOST)

    print(f"JEFEAGUILA conectado a {MODEL}. Escribe /salir para terminar.")
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
            answer = response.message.content.strip()
        except Exception as exc:
            print(f"\nERROR: {exc}")
            continue

        print(f"\nJEFEAGUILA> {answer}")
        remember("user", user_text)
        remember("assistant", answer)


if __name__ == "__main__":
    main()
