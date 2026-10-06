import re
import shutil

SAFE_BINS = {
    "ip", "ls", "cat", "cd", "pwd", "uname", "whoami", "df", "du",
    "free", "uptime", "ps", "env", "head", "tail", "grep", "awk",
    "sed", "which", "whereis", "file", "stat", "hostname", "nmcli",
    "find", "locate", "xargs", "rg", "fd", "getent", "host",
    "searchsploit", "semgrep", "pip-audit", "date", "printf", "echo"
}

def binary_exists(cmd: str) -> bool:
    clean = cmd.strip()
    if not clean:
        return False
    parts = clean.split()
    first = parts[0]
    if first == "sudo" and len(parts) > 1:
        first = parts[1]
    return shutil.which(first) is not None

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

def sanitize_command(raw_cmd: str) -> str:
    cleaned = raw_cmd.strip()
    
    # Strip markdown backticks if wrapped
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned.strip("`").strip()
    
    # Strip surrounding whole-line quotes only if they wrap the entire command erroneously
    if len(cleaned) >= 2:
        if (cleaned.startswith('"') and cleaned.endswith('"') and cleaned.count('"') == 2) or \
           (cleaned.startswith("'") and cleaned.endswith("'") and cleaned.count("'") == 2):
            cleaned = cleaned[1:-1].strip()

    return cleaned