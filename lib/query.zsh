_ask_query() {
  local iterative_mode="$1"
  local verbose_mode="$2"
  local chat_mode="$3"
  local user_query="$4"
  local model="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
  local host="${OLLAMA_HOST_IP:-http://localhost:11434}"

  if ! command -v curl &>/dev/null; then
    echo "Missing dependency: curl is required." >&2
    return 1
  fi

  local os_info="Linux"
  if [ -f /etc/os-release ]; then
    os_info=$(. /etc/os-release && echo "$PRETTY_NAME")
  fi

  local sys_interfaces
  sys_interfaces=$(ip -br addr 2>/dev/null | grep -v 'lo')
  local sys_route
  sys_route=$(ip route 2>/dev/null | grep default)
  local current_dir="$PWD"

  local installed_tools=""
  local t
  for t in rg find fd locate grep awk sed git docker nmap curl wget; do
    if command -v "$t" &>/dev/null; then
      installed_tools="${installed_tools}${t} "
    fi
  done

  python3 -c '
import urllib.request, json, sys, subprocess, re, os, tempfile

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

def is_safe_command(cmd):
    if "sudo" in cmd.split():
        return False
    if any(op in cmd for op in [">", ">>", "rm ", "dd ", "chmod ", "chown ", "mkfs", "reboot", "shutdown"]):
        return False

    safe_bins = {
        "ip", "ls", "cat", "cd", "pwd", "uname", "whoami", "df", "du",
        "free", "uptime", "ps", "env", "head", "tail", "grep", "awk",
        "sed", "which", "whereis", "file", "stat", "hostname", "nmcli",
        "find", "locate", "xargs", "rg", "fd"
    }

    pipe_segments = cmd.split("|")
    for segment in pipe_segments:
        parts = segment.strip().split()
        if not parts:
            continue
        first = parts[0]
        if first == "git":
            destructive = ["push", "commit", "reset", "clean", "checkout", "rebase", "merge"]
            if any(d in parts for d in destructive):
                return False
            continue
        if first == "docker":
            if len(parts) > 1 and parts[1] in ["ps", "images", "stats", "inspect"]:
                continue
            return False
        if first not in safe_bins:
            return False

    return True

def balance_quotes(cmd):
    s_quote = cmd.count("\x27") % 2 != 0
    d_quote = cmd.count("\"") % 2 != 0
    if s_quote:
        cmd += "\x27"
    if d_quote:
        cmd += "\""
    return cmd

if chat_mode:
    system_prompt = f"""You are a helpful software engineering assistant on {os_info}.
Working Directory: {workdir}
Available Tools: {tools}

Guidelines:
- Answer the user query clearly, concisely, and directly.
- Respond in Spanish if the user asks in Spanish, otherwise English.
- If you need local project files (e.g. README.md, directory tree, code) to answer the query accurately, you MUST request an inspection command prefixed with: EXEC: <command>
- Once inspection output is provided, deliver your complete final answer without EXEC."""
else:
    system_prompt = f"""You are a Linux CLI assistant on {os_info} running Zsh.
Host Environment:
Working Directory: {workdir}
Available Search/CLI Tools: {tools}
Network Interfaces:
{interfaces}
Default Route:
{route}

CRITICAL RULES:
- Output strictly and ONLY the raw executable shell command.
- NEVER wrap commands in quotes, code fences (```), or assignments (response=...).
- NEVER include explanations, comments, or conversational text.
- Ensure all quotation marks and parentheses are properly closed.
- Prefer faster tools if present in Available Search/CLI Tools (e.g. rg over grep, fd over find)."""

    if iterative:
        system_prompt += """
- If and only if you need to read local files, search paths, or inspect system states to provide the correct command, reply with: EXEC: <command>
- Fast inspection only: for files use cat, find, rg, ls.
- Once the inspection output is given to you, produce strictly the final command."""

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
            "temperature": 0.2 if chat_mode else 0.0,
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
            cleaned = re.sub(r"^(?:response\s*=\s*[\x27\x22]?|cmd\s*=\s*[\x27\x22]?)", "", l)
            cleaned = cleaned.rstrip("\x27\x22")
            if not cleaned.startswith(("#", "//", "Para ", "This ", "You ")):
                selected = cleaned
                break

        if not selected and lines:
            selected = lines[0]

        selected = re.sub(r"^(?:response\s*=\s*[\x27\x22]?|cmd\s*=\s*[\x27\x22]?)", "", selected).strip()
    else:
        selected = content

    if selected.startswith("EXEC:") and (iterative or chat_mode):
        inspect_cmd = selected.replace("EXEC:", "").strip().splitlines()[0].strip("\x27\"`")
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
                # Run through bash/zsh with direct terminal output and capture for Ollama
                with tempfile.NamedTemporaryFile(mode="w+", delete=True) as tmp_out:
                    wrapped_cmd = f"({inspect_cmd}) > >(tee {tmp_out.name}) 2>&1"
                    subprocess.run(wrapped_cmd, shell=True, cwd=workdir, executable="/bin/bash")
                    tmp_out.seek(0)
                    output = tmp_out.read()[:3000]
            else:
                output = "Command rejected by user."

        messages.append({"role": "assistant", "content": f"EXEC: {inspect_cmd}"})
        prompt_suffix = "Provide your comprehensive answer to the original question based on this data. No EXEC." if chat_mode else "Provide the final single-line command now. Ensure all quotes are balanced. No EXEC, no explanation."
        messages.append({"role": "user", "content": f"Inspection output:\n{output}\n{prompt_suffix}"})
    else:
        final_result = balance_quotes(selected) if not chat_mode else selected
        break

print(final_result)
' "$host" "$model" "$iterative_mode" "$verbose_mode" "$chat_mode" "$user_query" "$os_info" "$sys_interfaces" "$sys_route" "$current_dir" "$installed_tools"
}