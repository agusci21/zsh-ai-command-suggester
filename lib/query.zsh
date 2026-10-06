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

  local engine_path="${0:A:h}/engine.py"
  if [ ! -f "$engine_path" ]; then
    engine_path="${ZSH_AI_SUGGESTER_DIR:-$HOME/programas/practicas/zsh-ai-comand-suggester}/lib/engine.py"
  fi

  python3 "$engine_path" \
    "$host" \
    "$model" \
    "$iterative_mode" \
    "$verbose_mode" \
    "$chat_mode" \
    "$user_query" \
    "$os_info" \
    "$sys_interfaces" \
    "$sys_route" \
    "$current_dir" \
    "$installed_tools"
}