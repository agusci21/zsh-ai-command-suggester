import os
import re
import json
import shutil
import subprocess
from .client import query_ollama

EQUALIZER_SYSTEM_PROMPT = """You are a Skill Formatting Agent for a Linux CLI assistant.
Convert raw tool documentation and real CLI help into a standardized instruction block.

Rules:
1. Extract the EXACT CLI flags from the documentation or real CLI help.
2. If a flag expects an argument (e.g. '-autostart <modules>', '-eval <commands>', '-caplet <file>'), NEVER leave it without a value or followed directly by another flag.
3. Network sniffing and packet capture tools (such as bettercap, tcpdump) require root privileges: always include 'sudo'.
4. If the tool needs a network interface, define an Inspection Strategy using 'ip -4 route show default'.
5. Strictly forbid generic interface placeholders (eth0, eth1).
6. Output strictly a Markdown block with this schema:

### SKILL: <name>
Inspection Strategy:
EXEC: <safe inspection command if needed, else None>

Rules & Syntax:
- Privilege requirement: Always prefix with 'sudo'.
- Flag for interface: <exact flag, e.g. -iface>
- Valid execution pattern: <safe syntax example, e.g. sudo bettercap -iface <interface> -eval "net.probe on">
"""

def get_binary_help(binary_name: str) -> str:
    bin_path = shutil.which(binary_name)
    if not bin_path:
        return ""
    try:
        proc = subprocess.run([bin_path, "-h"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=2)
        if proc.stdout.strip():
            return proc.stdout[:2000]
    except Exception:
        pass
    try:
        proc = subprocess.run([bin_path, "--help"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=2)
        if proc.stdout.strip():
            return proc.stdout[:2000]
    except Exception:
        pass
    return ""

class CanonicalSkill:
    def __init__(self, name: str, source_type: str, raw_content: str):
        self.name = name.lower()
        self.source_type = source_type
        self.raw = raw_content
        self.formatted_prompt = ""

    def format_with_agent(self, host: str, model: str):
        cli_help = get_binary_help(self.name)
        help_context = f"\n\nReal CLI Help output on this machine:\n{cli_help}" if cli_help else ""

        messages = [
            {"role": "system", "content": EQUALIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Tool: {self.name}\nRaw Documentation:\n{self.raw[:2000]}{help_context}"}
        ]
        response = query_ollama(host, model, messages, chat_mode=True)
        clean = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", response.strip(), flags=re.DOTALL)
        self.formatted_prompt = clean if clean else f"### SKILL: {self.name}\n{self.raw}"

    def to_system_prompt_block(self) -> str:
        if self.formatted_prompt:
            return self.formatted_prompt
        return f"### SKILL: {self.name}\n{self.raw}"

def equalize_skill(file_path: str) -> CanonicalSkill | None:
    ext = os.path.splitext(file_path)[1].lower()
    parent_dir = os.path.basename(os.path.dirname(file_path))

    if parent_dir in ["skills", "custom"]:
        skill_name = os.path.splitext(os.path.basename(file_path))[0]
    else:
        skill_name = parent_dir

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
        if not content:
            return None
        return CanonicalSkill(skill_name, ext.lstrip("."), content)
    except Exception:
        return None