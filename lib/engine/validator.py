import json
import re
from .client import query_ollama

VALIDATOR_SYSTEM_PROMPT = """You are a strict CLI code review agent.
Your task is to review a proposed shell command against the user's intent, the real host environment, and tool syntax.

Evaluation criteria:
1. Is the command complete and non-trivial? (Reject bare binary names without parameters).
2. Does it use valid CLI flags according to modern tool documentation (e.g. rejecting invented flags like '--script' or '--interface' when the tool uses '-eval' or '-iface')?
3. Does it use the actual network interface from the environment rather than generic placeholders (e.g. eth0)?

Output format:
Respond strictly with a JSON object:
{
  "valid": true | false,
  "feedback": "Concise reason why it failed and specific flags/adjustments needed"
}
Do not output markdown code fences or conversational text outside the JSON.
"""

def validate_proposal(host: str, model: str, user_query: str, proposed_cmd: str) -> tuple[bool, str]:
    if not proposed_cmd or proposed_cmd.strip() in ["EXEC:", ""]:
        return False, "Empty or invalid execution string."

    messages = [
        {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User Request: {user_query}\nProposed Command: {proposed_cmd}"
        }
    ]

    raw_response = query_ollama(host, model, messages, chat_mode=True)
    clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.DOTALL)

    try:
        data = json.loads(clean_json)
        return bool(data.get("valid", False)), str(data.get("feedback", ""))
    except Exception:
        # Fallback heurístico si el modelo emite texto libre
        is_trivial = len(proposed_cmd.split()) <= 1
        if is_trivial:
            return False, "Command is too generic or lacks parameters."
        return True, ""