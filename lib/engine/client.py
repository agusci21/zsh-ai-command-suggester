import urllib.request
import json
import sys

def query_ollama(host: str, model: str, messages: list, chat_mode: bool) -> str:
    req_body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 1024 if chat_mode else 512
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[ask:error]\033[0m Ollama connection failed: {e}\n")
        sys.exit(1)