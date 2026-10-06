0="${ZERO:-${${0:A}:-${(%):-%N}}}"
ASK_PLUGIN_DIR="${0:A:h}"

source "${ASK_PLUGIN_DIR}/lib/security.zsh"
source "${ASK_PLUGIN_DIR}/lib/ui.zsh"

_ask_manual() {
  cat << 'EOF'
Usage: ask [OPTIONS] <query>

Options:
  -i, --iterative   Enable multi-step automated inspection
  -v, --verbose     Display debug traces and inspection outputs
  -c, --chat        Chat mode (returns conversational answers)
  -a, --auto        Auto-execute generated command (prompts if privileged)
  -m, --model NAME  Override Ollama model for this execution
  -h, --help        Show this help manual

Commands:
  ask model         List installed Ollama models and show active one
  ask model <name>  Set default model persistently in ~/.config/ask/config
EOF
}

_ask_query() {
  local iterative="$1"
  local verbose="$2"
  local chat="$3"
  local model="$4"
  local query="$5"

  local host="${ASK_HOST:-http://localhost:11434}"
  local os_info="$(uname -srm)"
  local interfaces="$(ip -br addr 2>/dev/null)"
  local route="$(ip route 2>/dev/null | grep default)"
  local workdir="$PWD"
  local tools="rg, fd, fzf, jq, curl, git, docker, nmap, ss, ip, semgrep"
  local skills_dir="${ASK_PLUGIN_DIR}/skills"

  python3 "${ASK_PLUGIN_DIR}/lib/engine.py" \
    "$host" \
    "$model" \
    "$iterative" \
    "$verbose" \
    "$chat" \
    "$query" \
    "$os_info" \
    "$interfaces" \
    "$route" \
    "$workdir" \
    "$tools" \
    "$skills_dir"
}