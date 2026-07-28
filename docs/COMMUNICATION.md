# Communication setup

JEFEAGUILA communication is controlled by:

- `prompts/JEFEAGUILA_SYSTEM.md`: behavior and comprehension charter.
- `config/communication.json`: reader-editable preferences.
- `examples/interactive_chat.py`: interactive Ollama chat with bounded local history.

## Start in PowerShell

```powershell
python -m pip install -r requirements.txt
ollama pull llama3.2:3b
python examples/interactive_chat.py
```

The history file is local at `data/chat_history.jsonl`. Delete that file to reset
conversation history. Do not store government identifiers, credentials, or secrets in
the conversation history.
