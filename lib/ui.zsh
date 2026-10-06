unalias ask 2>/dev/null
unalias pedir 2>/dev/null

_ask_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/ask"
_ask_config_file="${_ask_config_dir}/config"

_ask_get_active_model() {
  if [ -n "$ASK_MODEL" ]; then
    echo "$ASK_MODEL"
    return
  fi
  if [ -f "$_ask_config_file" ]; then
    local saved_model
    saved_model=$(grep -E "^model=" "$_ask_config_file" 2>/dev/null | cut -d'=' -f2- | tr -d ' "')
    if [ -n "$saved_model" ]; then
      echo "$saved_model"
      return
    fi
  fi
  echo "qwen2.5-coder:7b"
}

_ask_set_active_model() {
  local new_model="$1"
  mkdir -p "$_ask_config_dir"
  if [ -f "$_ask_config_file" ] && grep -qE "^model=" "$_ask_config_file"; then
    sed -i "s|^model=.*|model=${new_model}|" "$_ask_config_file"
  else
    echo "model=${new_model}" >> "$_ask_config_file"
  fi
  echo "\033[1;34m[ask]\033[0m Default model set to: \033[1;32m${new_model}\033[0m in ${_ask_config_file}"
}

_ask_list_ollama_models() {
  local current
  current=$(_ask_get_active_model)
  echo "\033[1;34m[ask]\033[0m Available local models in Ollama:"
  if command -v ollama >/dev/null 2>&1; then
    ollama list | tail -n +2 | awk -v cur="$current" '{
      if ($1 == cur)
        printf "  \033[1;32m* %-25s\033[0m %s\n", $1, "(active)"
      else
        printf "    %-25s %s\n", $1, $4 " " $5
    }'
  else
    echo "  Ollama binary not found in PATH."
  fi
}

ask-widget() {
  local query="$BUFFER"
  if [ -z "$query" ]; then
    return
  fi

  query="${query#ask }"
  query="${query#pedir }"
  query="${query#\"}"
  query="${query%\"}"

  local iterative="false"
  local verbose="false"
  local chat="false"
  local auto_exec="false"
  local custom_model=""

  while true; do
    case "$query" in
      -m\ *\ *)
        custom_model="${query#* }"
        custom_model="${custom_model%% *}"
        query="${query#* }"
        query="${query#* }"
        ;;
      --model\ *\ *)
        custom_model="${query#* }"
        custom_model="${custom_model%% *}"
        query="${query#* }"
        query="${query#* }"
        ;;
      -[a-zA-Z]*\ *)
        local opt="${query%% *}"
        query="${query#* }"
        local flags="${opt#-}"
        local idx=0
        local char=""
        while [ $idx -lt ${#flags} ]; do
          char="${flags:$idx:1}"
          case "$char" in
            i) iterative="true" ;;
            v) verbose="true" ;;
            c) chat="true" ;;
            a) auto_exec="true" ;;
            h)
              BUFFER=""
              _ask_manual
              zle reset-prompt
              return
              ;;
          esac
          (( idx++ ))
        done
        ;;
      --iterative\ *|--iterativo\ *)
        iterative="true"
        query="${query#* }"
        ;;
      --verbose\ *)
        verbose="true"
        query="${query#* }"
        ;;
      --chat\ *)
        chat="true"
        query="${query#* }"
        ;;
      --auto\ *)
        auto_exec="true"
        query="${query#* }"
        ;;
      *)
        break
        ;;
    esac
  done

  BUFFER="Thinking..."
  zle redisplay

  local active_model="${custom_model:-$(_ask_get_active_model)}"
  local cmd
  cmd=$(_ask_query "$iterative" "$verbose" "$chat" "$active_model" "$query")

  if [ -n "$cmd" ]; then
    if [ "$auto_exec" = "true" ]; then
      BUFFER=""
      zle redisplay
      if _ask_requires_elevation "$cmd"; then
        echo -e "\n\033[1;34m[ask]\033[0m Model generated command with privileges: \033[1;33m${cmd}\033[0m"
        if read -q "confirm?Authorize execution? (y/N): "; then
          echo
          eval "$cmd"
          zle reset-prompt
          return $?
        else
          echo
          BUFFER="$cmd"
          zle redisplay
          return 0
        fi
      else
        echo -e "\n\033[1;34m[ask]\033[0m Auto-executing: \033[1;32m${cmd}\033[0m"
        eval "$cmd"
        zle reset-prompt
        return $?
      fi
    else
      BUFFER=""
      local i
      for (( i=0; i<${#cmd}; i++ )); do
        BUFFER="${BUFFER}${cmd:$i:1}"
        CURSOR=$#BUFFER
        zle redisplay
        sleep 0.02
      done
    fi
  else
    BUFFER="$query"
    zle redisplay
  fi
}

function ask {
  local iterative="false"
  local verbose="false"
  local chat="false"
  local auto_exec="false"
  local custom_model=""

  if [ "$1" = "model" ]; then
    if [ -n "$2" ]; then
      _ask_set_active_model "$2"
      return 0
    else
      _ask_list_ollama_models
      return 0
    fi
  fi

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -h|--help)
        _ask_manual
        return 0
        ;;
      -m|--model)
        custom_model="$2"
        shift 2
        ;;
      --iterative|--iterativo)
        iterative="true"
        shift
        ;;
      --verbose)
        verbose="true"
        shift
        ;;
      --chat)
        chat="true"
        shift
        ;;
      --auto)
        auto_exec="true"
        shift
        ;;
      --)
        shift
        break
        ;;
      -[a-zA-Z]*)
        local flags="${1#-}"
        local idx=0
        local char=""
        while [ $idx -lt ${#flags} ]; do
          char="${flags:$idx:1}"
          case "$char" in
            i) iterative="true" ;;
            v) verbose="true" ;;
            c) chat="true" ;;
            a) auto_exec="true" ;;
            h)
              _ask_manual
              return 0
              ;;
            *)
              echo "Unknown option: -${char}" >&2
              _ask_manual
              return 1
              ;;
          esac
          (( idx++ ))
        done
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  if [ -z "$*" ]; then
    _ask_manual
    return 0
  fi

  local active_model="${custom_model:-$(_ask_get_active_model)}"
  local result
  result=$(_ask_query "$iterative" "$verbose" "$chat" "$active_model" "$*")

  if [ -z "$result" ]; then
    return 0
  fi

  if [ "$chat" = "true" ]; then
    echo "$result"
    return 0
  fi

  if [ "$auto_exec" = "true" ]; then
    if _ask_requires_elevation "$result"; then
      echo -e "\033[1;34m[ask]\033[0m Model generated command with privileges: \033[1;33m${result}\033[0m"
      if read -q "confirm?[ask] Authorize execution? (y/N): "; then
        echo
        eval "$result"
        return $?
      else
        echo
        print -z -- "$result"
        return 0
      fi
    else
      echo -e "\033[1;34m[ask]\033[0m Auto-executing: \033[1;32m${result}\033[0m"
      eval "$result"
      return $?
    fi
  else
    print -z -- "$result"
  fi
}

zle -N ask-widget
bindkey '^G' ask-widget

alias pedir='ask'