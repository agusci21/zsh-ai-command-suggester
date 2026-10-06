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

  local plugin_root="${ZSH_AI_SUGGESTER_DIR}"
  if [ -z "$plugin_root" ] || [ ! -d "$plugin_root" ]; then
    local script_source="${(%):-%x}"
    plugin_root="${script_source:A:h:h}"
  fi
  if [ ! -f "${plugin_root}/lib/engine.py" ]; then
    plugin_root="$HOME/programas/practicas/zsh-ai-comand-suggester"
  fi

  local skills_dir="${plugin_root}/skills"
  local engine_path="${plugin_root}/lib/engine.py"

  local installed_tools=""
  local t
  for t in rg find fd locate grep awk sed git docker nmap curl wget; do
    if command -v "$t" &>/dev/null; then
      installed_tools="${installed_tools}${t} "
    fi
  done

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
    "$installed_tools" \
    "$skills_dir"
}