# Ollama SDK integration

JEFEAGUILA uses the official Ollama clients as dependencies instead of copying
the complete `ollama-python` and `ollama-js` repositories.

## Python

```powershell
python -m pip install -r requirements.txt
python examples/ollama_chat.py
```

## JavaScript

```powershell
npm install
npm run chat
```

## Runtime

- Local endpoint: `http://127.0.0.1:11434`
- Default model: `llama3.2:3b`
- Override model: `$env:JEFEAGUILA_MODEL = "another-model"`
- Override host: `$env:OLLAMA_HOST = "http://127.0.0.1:11434"`

Ollama must be running and the selected model must already be installed.
