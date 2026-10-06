import re

SAFE_BINS = {
    "ip", "ls", "cat", "cd", "pwd", "uname", "whoami", "df", "du",
    "free", "uptime", "ps", "env", "head", "tail", "grep", "awk",
    "sed", "which", "whereis", "file", "stat", "hostname", "nmcli",
    "find", "locate", "xargs", "rg", "fd", "getent", "host",
    "searchsploit", "semgrep", "pip-audit"
}

def is_safe_command(cmd: str) -> bool:
    if "sudo" in cmd.split():
        return False
    if "nmap" in cmd.split():
        return False
    if any(op in cmd for op in [">", ">>", "rm ", "dd ", "chmod ", "chown ", "mkfs", "reboot", "shutdown"]):
        return False

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
        if first == "npm":
            if len(parts) > 1 and parts[1] == "audit":
                if any(flag in parts for flag in ["fix", "--fix"]):
                    return False
                continue
            return False
        if first not in SAFE_BINS:
            return False

    return True

def balance_quotes(cmd: str) -> str:
    s_quote = cmd.count("'") % 2 != 0
    d_quote = cmd.count('"') % 2 != 0
    if s_quote:
        cmd += "'"
    if d_quote:
        cmd += '"'
    return cmd

def sanitize_command(raw_cmd: str) -> str:
    cleaned = raw_cmd.strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (cleaned.startswith('"') and cleaned.endswith('"')):
        cleaned = cleaned[1:-1].strip()
    return balance_quotes(cleaned)