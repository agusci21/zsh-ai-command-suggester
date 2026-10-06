unalias ask 2>/dev/null
unalias pedir 2>/dev/null

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

  while true; do
    case "$query" in
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

  case "$query" in
    -h|--help)
      BUFFER=""
      _ask_manual
      zle reset-prompt
      return
      ;;
  esac

  BUFFER="Thinking..."
  zle redisplay

  local cmd
  cmd=$(_ask_query "$iterative" "$verbose" "$chat" "$query")

  if [ -n "$cmd" ]; then
    if [ "$auto_exec" = "true" ]; then
      BUFFER=""
      zle redisplay
      if _ask_requires_elevation "$cmd"; then
        echo -e "\n\033[1;34m[ask]\033[0m Model generated command with privileges: \033[1;33m${cmd}\033[0m"
        echo -ne "\033[1;31m[ask] Authorize execution? (y/N): \033[0m"
        read -q "confirm? "
        echo
        case "$confirm" in
          y|Y|s|S)
            eval "$cmd"
            zle reset-prompt
            return $?
            ;;
          *)
            BUFFER="$cmd"
            zle redisplay
            return 0
            ;;
        esac
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

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -h|--help)
        _ask_manual
        return 0
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

  local result
  result=$(_ask_query "$iterative" "$verbose" "$chat" "$*")

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
      echo -ne "\033[1;31m[ask] Authorize execution? (y/N): \033[0m"
      read -q "confirm? "
      echo
      case "$confirm" in
        y|Y|s|S)
          eval "$result"
          return $?
          ;;
        *)
          print -z -- "$result"
          return 0
          ;;
      esac
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