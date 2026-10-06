import json
import re
from .client import query_ollama

VALIDATOR_SYSTEM_PROMPT = """You are a strict CLI code review agent.
Review the proposed command against the user's intent, the active skills rules, and the host environment.

CRITICAL CHECKS:
1. Privileges: Commands requiring raw network access (e.g. bettercap, tcpdump) must include 'sudo'.
2. Flag Arguments: Flags that require an argument (like '-autostart', '-eval', '-caplet', '-o') must NEVER be immediately followed by another flag starting with '-' or left bare.
3. Grounding: Reject placeholder interfaces (eth0, eth1) if actual interfaces (like enp10s0) exist in Host Interfaces.
4. Valid Syntax: Follow strictly the documented tool flags.

Output format:
Respond strictly with a JSON object:
{
  "valid": true | false,
  "feedback": "Concise failure reason identifying missing sudo, missing argument to flag, or syntax error"
}
Do not output markdown code fences or conversational text outside the JSON.
"""

def validate_proposal(host: str, model: str, user_query: str, proposed_cmd: str, interfaces: str, skills_context: str) -> tuple[bool, str]:
    if not proposed_cmd or proposed_cmd.strip() in ["EXEC:", ""]:
        return False, "Empty or invalid execution string."

    # Heurística rápida: rechazar si -autostart está seguido directamente de otro flag '-'
    tokens = proposed_cmd.split()
    for idx, token in enumerate(tokens):
        if token in ["-autostart", "-eval", "-caplet", "-script"]:
            if idx + 1 >= len(tokens) or tokens[idx + 1].startswith("-"):
                return False, f"Flag '{token}' requires a specific parameter/value before the next flag."

    messages = [
        {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{skills_context}\n\nHost Interfaces:\n{interfaces}\nUser Request: {user_query}\nProposed Command: {proposed_cmd}"
        }
    ]

    raw_response = query_ollama(host, model, messages, chat_mode=True)
    clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.DOTALL)

    try:
        data = json.loads(clean_json)
        return bool(data.get("valid", False)), str(data.get("feedback", ""))
    except Exception:
        parts = proposed_cmd.split()
        if len(parts) <= 1:
            return False, "Command is too generic or lacks parameters."
        return True, ""