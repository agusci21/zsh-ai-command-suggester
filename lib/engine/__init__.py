import sys
import subprocess
import re
import tempfile
from .skills import load_skills
from .security import is_safe_command, sanitize_command, binary_exists
from .client import query_ollama
from .validator import validate_proposal

def clean_reasoning_tokens(content: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    if "<think>" in cleaned and "</think>" not in cleaned:
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()

def extract_command_from_text(content: str, allow_exec: bool) -> str:
    cleaned_content = clean_reasoning_tokens(content)

    fence_matches = re.findall(r"```(?:sh|bash|zsh)?\s*(.*?)\s*```", cleaned_content, re.DOTALL)
    if fence_matches:
        candidate = fence_matches[-1].strip()
        lines = [l.strip() for l in candidate.splitlines() if l.strip() and not l.strip().startswith(("#", "//"))]
        if lines:
            line = lines[0]
            if not allow_exec and line.startswith("EXEC:"):
                line = line.replace("EXEC:", "").strip()
            return line

    lines = [l.strip() for l in cleaned_content.splitlines() if l.strip()]

    thought_starters = (
        "okay", "let's", "let me", "first", "next", "to achieve", "we can",
        "in linux", "the user", "para ", "this ", "you ", "here ", "el ",
        "puedes ", "usa ", "nota:", "sure", "claro", "so the command", "i'll"
    )

    valid_candidates = []
    for line in lines:
        if line.startswith("EXEC:"):
            return line if allow_exec else line.replace("EXEC:", "").strip()
        sub = re.sub(r"^(?:response\s*=\s*['\"]?|cmd\s*=\s*['\"]?)", "", line).rstrip("'\"")
        lower_sub = sub.lower()
        if not any(lower_sub.startswith(prefix) for prefix in thought_starters):
            valid_candidates.append(sub)

    if valid_candidates:
        res = valid_candidates[-1]
        return res if (allow_exec or not res.startswith("EXEC:")) else res.replace("EXEC:", "").strip()

    if lines:
        res = lines[0]
        return res if (allow_exec or not res.startswith("EXEC:")) else res.replace("EXEC:", "").strip()

    return ""

def run():
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

    skills_context = load_skills(skills_dir, user_query, verbose, iterative, host, model)

    if chat_mode:
        system_prompt = (
            f"You are a helpful software engineering assistant on {os_info}.\n"
            f"Working Directory: {workdir}\n"
            f"Available Tools: {tools}\n"
            f"{skills_context}\n\n"
            "Guidelines:\n"
            "- Answer the user query clearly, concisely, and directly.\n"
            "- Respond in Spanish if the user asks in Spanish, otherwise English.\n"
            "- If you need local project files to answer accurately, request an inspection command prefixed with: EXEC: <command>\n"
            "- Once inspection output is provided, deliver your complete final answer without EXEC."
        )
    else:
        system_prompt = (
            f"You are a raw shell command generator for Linux {os_info} running Zsh.\n"
            f"Working Directory: {workdir}\n"
            f"Available Search/CLI Tools: {tools}\n"
            f"Network Interfaces:\n{interfaces}\n"
            f"{skills_context}\n\n"
            "CRITICAL:\n"
            "- Do NOT explain, do NOT analyze, do NOT output your thoughts.\n"
            "- Respond ONLY with a markdown block containing the raw executable Zsh command:\n"
            "```zsh\n"
            "<command>\n"
            "```"
        )
        if iterative:
            system_prompt += (
                "\n\nIf environment inspection is strictly needed, output ONLY:\n"
                "EXEC: <command>"
            )
        else:
            system_prompt += "\n- NEVER output 'EXEC:'. Return directly the final command."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    max_steps = 4
    step = 0
    final_result = ""

    while step < max_steps:
        step += 1
        content = query_ollama(host, model, messages, chat_mode=chat_mode)

        if not chat_mode:
            selected = extract_command_from_text(content, allow_exec=iterative)
        else:
            selected = content

        if selected.startswith("EXEC:") and (iterative or chat_mode):
            raw_inspect = selected.replace("EXEC:", "").strip().splitlines()[0]
            inspect_cmd = sanitize_command(raw_inspect)

            if not binary_exists(inspect_cmd):
                output = f"Error: Command '{inspect_cmd.split()[0]}' not found in PATH."
                if verbose:
                    sys.stderr.write(f"\033[1;31m[ask:inspect error]\033[0m {output}\n")
                    sys.stderr.flush()
            else:
                is_safe = is_safe_command(inspect_cmd)
                if is_safe:
                    if verbose:
                        sys.stderr.write(f"\033[1;34m[ask:inspect]\033[0m Automated: \033[1;32m{inspect_cmd}\033[0m\n")
                        sys.stderr.flush()
                    proc = subprocess.run(inspect_cmd, shell=True, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    output = proc.stdout[:3000]
                    if verbose and output.strip():
                        sys.stderr.write(f"\033[1;30m{output.strip()}\033[0m\n")
                        sys.stderr.flush()
                else:
                    sys.stderr.write(f"\n\033[1;34m[ask]\033[0m Privilege authorization required: \033[1;33m{inspect_cmd}\033[0m\n")
                    sys.stderr.write("\033[1;31m[ask] Authorize execution? (y/N): \033[0m")
                    sys.stderr.flush()

                    with open("/dev/tty", "r") as tty_in:
                        ans = tty_in.readline().strip().lower()

                    if ans in ["y", "s"]:
                        if verbose:
                            sys.stderr.write(f"\033[1;34m[ask:inspect]\033[0m Executing privileged: {inspect_cmd}\n")
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
                "Provide strictly the final single-line command in a ```zsh block now. No EXEC, no explanation."
            )
            messages.append({"role": "user", "content": f"Inspection output:\n{output.strip()}\n{prompt_suffix}"})
            continue

        if chat_mode:
            final_result = selected
            break

        candidate_cmd = sanitize_command(selected)

        if not iterative:
            final_result = candidate_cmd
            break

        is_valid, feedback = validate_proposal(host, model, user_query, candidate_cmd, interfaces, skills_context)

        if verbose:
            sys.stderr.write(f"\033[1;34m[ask:critic]\033[0m Candidate: '\033[1;33m{candidate_cmd}\033[0m' | Valid: {is_valid}\n")
            if not is_valid and feedback:
                sys.stderr.write(f"\033[1;31m[ask:critic feedback]\033[0m {feedback}\n")
            sys.stderr.flush()

        if is_valid or step >= max_steps:
            final_result = candidate_cmd
            break
        else:
            messages.append({"role": "assistant", "content": candidate_cmd})
            messages.append({
                "role": "user",
                "content": f"The proposed command is invalid: {feedback}. Output strictly the corrected command in a ```zsh code block."
            })

    print(final_result)