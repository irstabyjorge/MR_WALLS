import os
from ollama import Client

HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("JEFEAGUILA_MODEL", "llama3.2:3b")

client = Client(host=HOST)
response = client.chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "You are JEFEAGUILA, a local, defensive, evidence-first "
                "assistant. Distinguish facts, technical data, user statements, "
                "inferences, hypotheses, contradictions, and unverified claims."
            ),
        },
        {"role": "user", "content": "Reply: JEFEAGUILA Python client works."},
    ],
)
print(response.message.content)
