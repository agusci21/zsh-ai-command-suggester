import urllib.request
import json
import sys

def query_ollama(host: str, model: str, messages: list, chat_mode: bool) -> str:
    req_body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            content = msg.get("content", "").strip()

            if not content and "thinking" in msg:
                content = msg.get("thinking", "").strip()

            return content
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[ask:error]\033[0m Ollama connection failed: {e}\n")
        sys.exit(1)