import os
import re
import json
import sys
from .equalizer import equalize_skill, CanonicalSkill
from .client import query_ollama

ROUTER_SYSTEM_PROMPT = """You are a strict skill classification agent.
Analyze the user CLI request and select matching skill names from the provided list.

CRITICAL RULES:
1. Select a skill ONLY if the user explicitly mentions the tool name or clearly requests its specialized domain operations.
2. Standard Linux operations (searching files with grep/rg/find, listing processes, tar/zip, file manipulation) do NOT use specialized skills. Return [] for them.
3. If no skill is an exact match, output [].

Output strictly a JSON list of matching skill names, e.g.: ["bettercap"] or []
No conversational text, no markdown fences.
"""

def get_all_canonical_skills(directory: str) -> dict[str, CanonicalSkill]:
    if not directory or not os.path.isdir(directory):
        return {}
    skills = {}
    valid_exts = {".md", ".txt", ".json", ".yaml", ".yml"}

    for root, _, files in os.walk(directory):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts and not f.startswith("."):
                full_path = os.path.join(root, f)
                skill = equalize_skill(full_path)
                if skill:
                    skills[skill.name] = skill
    return skills

def route_skills_with_agent(host: str, model: str, user_query: str, available_skills: list[str]) -> list[str]:
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Available skills: {json.dumps(available_skills)}\nUser Request: {user_query}"}
    ]
    raw_response = query_ollama(host, model, messages, chat_mode=True)
    clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.DOTALL)
    try:
        selected = json.loads(clean_json)
        if isinstance(selected, list):
            return [s.lower() for s in selected if isinstance(s, str)]
    except Exception:
        pass
    return []

def match_skills_heuristic(user_text: str, skills_map: dict[str, CanonicalSkill]) -> list[str]:
    normalized_words = set(re.findall(r"[\w-]+", user_text.lower()))
    selected = []

    for name in skills_map:
        if name in normalized_words:
            selected.append(name)

    return selected

def load_skills(directory: str, user_text: str, is_verbose: bool, is_iterative: bool, host: str, model: str) -> str:
    skills_map = get_all_canonical_skills(directory)
    if not skills_map:
        return ""

    available_names = sorted(list(skills_map.keys()))

    if is_iterative:
        matched_names = route_skills_with_agent(host, model, user_text, available_names)
        if not matched_names:
            matched_names = match_skills_heuristic(user_text, skills_map)
    else:
        matched_names = match_skills_heuristic(user_text, skills_map)

    matched_names = [n for n in matched_names if n in skills_map]

    if is_verbose:
        if matched_names:
            mode_tag = "agent-routed" if is_iterative else "heuristic"
            sys.stderr.write(f"\033[1;34m[ask:skills]\033[0m Loaded ({mode_tag}): \033[1;32m{', '.join(matched_names)}\033[0m\n")
        else:
            sys.stderr.write("\033[1;34m[ask:skills]\033[0m No skills selected.\n")
        sys.stderr.flush()

    if not matched_names:
        return ""

    blocks = []
    for name in matched_names:
        skill = skills_map[name]
        if is_iterative:
            if is_verbose:
                sys.stderr.write(f"\033[1;34m[ask:equalizer]\033[0m Normalizing skill '{name}' via LLM...\n")
                sys.stderr.flush()
            skill.format_with_agent(host, model)
        blocks.append(skill.to_system_prompt_block())

    return "\n\nACTIVE SPECIALIZED DOMAIN SKILLS:\n" + "\n\n".join(blocks)