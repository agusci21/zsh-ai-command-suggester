import os
import re
import json
import sys

def parse_skill_file(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    parent_dir = os.path.basename(os.path.dirname(file_path))
    
    if parent_dir in ["skills", "custom"]:
        skill_name = os.path.splitext(os.path.basename(file_path))[0].lower()
    else:
        skill_name = parent_dir.lower()

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read().strip()

    if not raw_text:
        return None, None, None

    triggers = []
    content_repr = raw_text

    if ext == ".json":
        try:
            data = json.loads(raw_text)
            triggers = data.get("triggers", [])
            content_repr = json.dumps(data, indent=2)
        except Exception:
            return None, None, None
    elif ext in [".yaml", ".yml"]:
        triggers_match = re.search(r"triggers:\s*\n((?:\s*-\s*.*\n?)+)", raw_text, re.IGNORECASE)
        if triggers_match:
            triggers = [line.strip().lstrip("-").strip() for line in triggers_match.group(1).splitlines() if line.strip()]
    else:
        triggers_match = re.search(r"##\s+Triggers\s*\n(.*?)(?=\n##|\Z)", raw_text, re.DOTALL | re.IGNORECASE)
        if triggers_match:
            triggers = triggers_match.group(1).splitlines()

    return skill_name, triggers, content_repr

def extract_trigger_keywords(triggers: list, skill_name: str) -> set:
    keywords = {skill_name.lower()}
    
    combined = " ".join(triggers).lower()
    cleaned = re.sub(r"[^\w\s-]", " ", combined)
    stopwords = {
        "queries", "involving", "about", "the", "and", "for",
        "with", "from", "into", "that", "this", "when", "using", "such"
    }
    for token in cleaned.split():
        if len(token) > 1 and token not in stopwords:
            keywords.add(token)
            if token.endswith("s"):
                keywords.add(token[:-1])
    return keywords

def is_skill_triggered(user_text: str, triggers: list, skill_name: str) -> bool:
    keywords = extract_trigger_keywords(triggers, skill_name)
    normalized_query = re.findall(r"[\w-]+", user_text.lower())
    query_set = set(normalized_query)
    
    for word in list(query_set):
        if word.endswith("s") and len(word) > 2:
            query_set.add(word[:-1])
        if word.endswith("es") and len(word) > 3:
            query_set.add(word[:-2])

    synonyms = {
        "commit": ["git", "commits"],
        "commitear": ["git", "commit"],
        "cambio": ["git", "diff", "status", "commit"],
        "cambios": ["git", "diff", "status", "commit"],
        "rama": ["branch", "git"],
        "ramas": ["branch", "git"],
        "repo": ["git", "repository"],
        "repositorio": ["git", "repository"],
        "red": ["network", "interfaces", "subnets", "ip", "bettercap", "wireshark", "tcpdump"],
        "puerto": ["ports", "port", "ss", "nmap"],
        "puertos": ["ports", "port", "ss", "nmap"],
        "contenedor": ["container", "containers", "docker"],
        "contenedores": ["container", "containers", "docker"],
        "vulnerabilidad": ["vulnerability", "vuln", "target-audit", "network-audit", "backend-audit"],
        "vulnerabilidades": ["vulnerability", "vuln", "target-audit", "network-audit", "backend-audit"],
        "escanear": ["nmap", "scan", "scanning"],
        "escaneo": ["nmap", "scan", "scanning"]
    }

    for word in query_set:
        if word in keywords:
            return True
        if word in synonyms:
            for syn in synonyms[word]:
                if syn in keywords or syn == skill_name.lower():
                    return True

    return False

def load_skills(directory: str, user_text: str, is_verbose: bool) -> str:
    if not directory or not os.path.isdir(directory):
        return ""
    loaded = []
    loaded_names = []

    valid_extensions = {".md", ".txt", ".json", ".yaml", ".yml"}
    candidate_files = []

    for root, _, files in os.walk(directory):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_extensions and not f.startswith("."):
                candidate_files.append(os.path.join(root, f))

    for file_path in sorted(candidate_files):
        try:
            skill_name, triggers, content_repr = parse_skill_file(file_path)
            if not skill_name or not content_repr:
                continue

            if is_skill_triggered(user_text, triggers, skill_name):
                is_custom = "skills/custom" in file_path
                tag = f"{skill_name} (custom)" if is_custom else skill_name
                loaded.append(f"### SKILL: {tag}\n{content_repr}")
                loaded_names.append(tag)
        except Exception:
            continue

    if is_verbose:
        if loaded_names:
            names_str = ", ".join(loaded_names)
            sys.stderr.write(f"\033[1;34m[ask:verbose]\033[0m Loaded skills ({len(loaded_names)}): \033[1;32m{names_str}\033[0m\n")
        else:
            sys.stderr.write("\033[1;34m[ask:verbose]\033[0m No skills matched for this query.\n")
        sys.stderr.flush()

    if loaded:
        return "\n\nACTIVE SPECIALIZED DOMAIN SKILLS:\n" + "\n\n".join(loaded)
    return ""