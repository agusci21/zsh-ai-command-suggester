import sys
import subprocess
import re
import tempfile
from .skills import load_skills
from .security import is_safe_command, sanitize_command, binary_exists
from .client import query_ollama
from .validator import validate_proposal

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
            f"You are a Linux CLI generator on {os_info} running Zsh.\n"
            "Host Environment:\n"
            f"Working Directory: {workdir}\n"
            f"Available Search/CLI Tools: {tools}\n"
            f"Network Interfaces:\n{interfaces}\n"
            f"Default Route:\n{route}\n"
            f"{skills_context}\n\n"
            "CRITICAL RULES:\n"
            "- Output strictly and ONLY the raw executable shell command.\n"
            "- NEVER wrap commands in quotes, code fences (```), or assignments.\n"
            "- NEVER include explanations, comments, or conversational text.\n"
            "- NEVER output an isolated binary name without required flags or parameters.\n"
            "- Follow strictly the flags and syntax documented in ACTIVE SPECIALIZED DOMAIN SKILLS.\n"
            "- Use ONLY real network interfaces from the Host Environment or inspection output.\n"
            "- Ensure all quotation marks and parentheses are properly closed."
        )
        if iterative:
            system_prompt += (
                "\n\nCRITICAL ITERATIVE POLICY:\n"
                "- If the active skill requires environment data, run inspection with 'EXEC: <cmd>'.\n"
                "- Never guess interfaces; extract them from the Host Environment or run an inspection.\n"
                "- DO NOT output the final command until inspection is complete."
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
        content = query_ollama(host, model, messages, chat_mode=chat_mode)

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
                cleaned = re.sub(r"^(?:response\s*=\s*['\"]?|cmd\s*=\s*['\"]?)", "", l).rstrip("'\"")
                if not cleaned.startswith(("#", "//", "Para ", "This ", "You ")):
                    selected = cleaned
                    break

            if not selected and lines:
                selected = lines[0]

            selected = re.sub(r"^(?:response\s*=\s*['\"]?|cmd\s*=\s*['\"]?)", "", selected).strip()
        else:
            selected = content

        if selected.startswith("EXEC:") and (iterative or chat_mode):
            raw_inspect = selected.replace("EXEC:", "").strip().splitlines()[0]
            inspect_cmd = sanitize_command(raw_inspect)

            if not binary_exists(inspect_cmd):
                output = f"Error: Command '{inspect_cmd.split()[0]}' not found. Use available tools or inspect provided Network Interfaces."
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
                "Provide strictly the final single-line command now using discovered real parameters. No EXEC, no explanation."
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
                "content": f"The proposed command is invalid: {feedback}. Output strictly the corrected raw command respecting the skill flags and real environment."
            })

    print(final_result)