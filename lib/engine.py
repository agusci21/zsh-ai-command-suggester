import urllib.request
import json
import sys
import subprocess
import re
import os
import tempfile
import glob

host = sys.argv[1]
model = sys.argv[2]
iterative = sys.argv[3] == "true"
verbose = sys.argv[4] == "true"
chat_mode = sys.argv[5] == "true"
user_query = sys.argv[6]
os_info = sys.argv[7]
interfaces = sys.argv[8]
route = sys.argv[9]
workdir = sys.argv[10]
tools = sys.argv[11].strip()
skills_dir = sys.argv[12] if len(sys.argv) > 12 else ""

def extract_trigger_keywords(content, skill_name):
    keywords = set()
    keywords.add(skill_name.lower())
    
    triggers_match = re.search(r"##\s+Triggers\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if triggers_match:
        trigger_text = triggers_match.group(1).lower()
        cleaned = re.sub(r"[^\w\s-]", " ", trigger_text)
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

def is_skill_triggered(user_text, content, skill_name):
    keywords = extract_trigger_keywords(content, skill_name)
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
        "red": ["network", "interfaces", "subnets", "ip"],
        "puerto": ["ports", "port", "ss"],
        "puertos": ["ports", "port", "ss"],
        "contenedor": ["container", "containers", "docker"],
        "contenedores": ["container", "containers", "docker"],
        "vulnerabilidad": ["vulnerability", "vuln", "target-audit", "network-audit"],
        "vulnerabilidades": ["vulnerability", "vuln", "target-audit", "network-audit"],
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

def load_skills(directory, user_text, is_verbose):
    if not directory or not os.path.isdir(directory):
        return ""
    loaded = []
    loaded_names = []
    pattern = os.path.join(directory, "**", "*.md")
    
    for file_path in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue
                skill_name = os.path.basename(os.path.dirname(file_path))
                if is_skill_triggered(user_text, content, skill_name):
                    loaded.append(f"### SKILL: {skill_name}\n{content}")
                    loaded_names.append(skill_name)
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

def is_safe_command(cmd):
    if "sudo" in cmd.split():
        return False
    if "nmap" in cmd.split():
        return False
    if any(op in cmd for op in [">", ">>", "rm ", "dd ", "chmod ", "chown ", "mkfs", "reboot", "shutdown"]):
        return False

    safe_bins = {
        "ip", "ls", "cat", "cd", "pwd", "uname", "whoami", "df", "du",
        "free", "uptime", "ps", "env", "head", "tail", "grep", "awk",
        "sed", "which", "whereis", "file", "stat", "hostname", "nmcli",
        "find", "locate", "xargs", "rg", "fd", "getent", "host", "searchsploit"
    }

    pipe_segments = cmd.split("|")
    for segment in pipe_segments:
        parts = segment.strip().split()
        if not parts:
            continue
        first = parts[0]
        if first == "git":
            if len(parts) < 2 or parts[1] not in ["status", "diff", "log", "branch", "show", "rev-parse", "check-ignore", "describe"]:
                return False
            continue
        if first == "docker":
            if len(parts) > 1 and parts[1] in ["ps", "images", "stats", "inspect", "container", "volume", "network"]:
                continue
            return False
        if first not in safe_bins:
            return False

    return True

def balance_quotes(cmd):
    s_quote = cmd.count("'") % 2 != 0
    d_quote = cmd.count('"') % 2 != 0
    if s_quote:
        cmd += "'"
    if d_quote:
        cmd += '"'
    return cmd

skills_context = load_skills(skills_dir, user_query, verbose)

if chat_mode:
    system_prompt = (
        f"You are a helpful software engineering assistant on {os_info}.\n"
        f"Working Directory: {workdir}\n"
        f"Available Tools: {tools}\n"
        f"{skills_context}\n\n"
        "Guidelines:\n"
        "- Answer the user query clearly, concisely, and directly.\n"
        "- Respond in Spanish if the user asks in Spanish, otherwise English.\n"
        "- If you need local project files (e.g. README.md, directory tree, code) to answer the query accurately, you MUST request an inspection command prefixed with: EXEC: <command>\n"
        "- Once inspection output is provided, deliver your complete final answer without EXEC."
    )
else:
    system_prompt = (
        f"You are a Linux CLI assistant on {os_info} running Zsh.\n"
        "Host Environment:\n"
        f"Working Directory: {workdir}\n"
        f"Available Search/CLI Tools: {tools}\n"
        f"Network Interfaces:\n{interfaces}\n"
        f"Default Route:\n{route}\n"
        f"{skills_context}\n\n"
        "CRITICAL RULES:\n"
        "- Output strictly and ONLY the raw executable shell command.\n"
        "- NEVER wrap commands in quotes, code fences (```), or assignments (response=...).\n"
        "- NEVER include explanations, comments, or conversational text.\n"
        "- Ensure all quotation marks and parentheses are properly closed.\n"
        "- Prefer faster tools if present in Available Search/CLI Tools (e.g. rg over grep, fd over find)."
    )
    if iterative:
        system_prompt += (
            "\n\nCRITICAL ITERATIVE POLICY:\n"
            "- When an active Skill specifies an Inspection Strategy for a query, you MUST start your response with 'EXEC: <command>' to execute that strategy.\n"
            "- For Git commit requests, you MUST execute 'EXEC: git status -s' first.\n"
            "- DO NOT output the final command until you have received and analyzed the output from EXEC."
        )

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_query}
]

max_steps = 4
step = 0
final_result = ""

while step < max_steps:
    step += 1
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
            content = data.get("message", {}).get("content", "").strip()
    except Exception:
        sys.exit(1)

    if not chat_mode:
        fence = re.search(r"```(?:sh|bash|zsh)?\s*(.*?)\s*```", content, re.DOTALL)
        if fence:
            content = fence.group(1).strip()

        lines = [l.strip() for l in content.splitlines() if l.strip()]
        selected = ""
        for l in lines:
            if l.startswith("EXEC:"):
                selected = l
                break
            cleaned = re.sub(r"^(?:response\s*=\s*['\"]?|cmd\s*=\s*['\"]?)", "", l)
            cleaned = cleaned.rstrip("'\"")
            if not cleaned.startswith(("#", "//", "Para ", "This ", "You ")):
                selected = cleaned
                break

        if not selected and lines:
            selected = lines[0]

        selected = re.sub(r"^(?:response\s*=\s*['\"]?|cmd\s*=\s*['\"]?)", "", selected).strip()
    else:
        selected = content

    if selected.startswith("EXEC:") and (iterative or chat_mode):
        inspect_cmd = selected.replace("EXEC:", "").strip().splitlines()[0].strip("'\"`")
        is_safe = is_safe_command(inspect_cmd)

        if is_safe:
            sys.stderr.write(f"\033[1;34m[ask]\033[0m Automated inspection: \033[1;32m{inspect_cmd}\033[0m\n")
            sys.stderr.flush()
            proc = subprocess.run(inspect_cmd, shell=True, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = proc.stdout[:3000]
            if verbose:
                sys.stderr.write(output + "\n")
                sys.stderr.flush()
        else:
            sys.stderr.write(f"\n\033[1;34m[ask]\033[0m Model requested privileged execution: \033[1;33m{inspect_cmd}\033[0m\n")
            sys.stderr.write("\033[1;31m[ask] Authorize execution? (y/N): \033[0m")
            sys.stderr.flush()

            with open("/dev/tty", "r") as tty_in:
                ans = tty_in.readline().strip().lower()

            if ans in ["y", "s"]:
                sys.stderr.write(f"\033[1;34m[ask]\033[0m Executing: {inspect_cmd}\n")
                sys.stderr.flush()
                with tempfile.NamedTemporaryFile(mode="w+", delete=True) as tmp_out:
                    wrapped_cmd = f"({inspect_cmd}) > >(tee {tmp_out.name}) 2>&1"
                    subprocess.run(wrapped_cmd, shell=True, cwd=workdir, executable="/bin/bash")
                    tmp_out.seek(0)
                    output = tmp_out.read()[:3000]
            else:
                output = "Command rejected by user."

        messages.append({"role": "assistant", "content": f"EXEC: {inspect_cmd}"})
        prompt_suffix = (
            "Provide your comprehensive answer to the original question based on this data. No EXEC."
            if chat_mode
            else "Provide strictly the final single-line command now. If unstaged/untracked files exist, use: 'git add . && git commit -m \"...\"'. Never output only 'git add'. Follow Conventional Commits format. No EXEC, no explanation."
        )
        messages.append({"role": "user", "content": f"Inspection output:\n{output}\n{prompt_suffix}"})
    else:
        final_result = balance_quotes(selected) if not chat_mode else selected
        break

print(final_result)