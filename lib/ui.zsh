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

  while true; do
    case "$query" in
      -i\ *|--iterative\ *|--iterativo\ *)
        iterative="true"
        query="${query#-i }"
        query="${query#--iterative }"
        query="${query#--iterativo }"
        ;;
      -v\ *|--verbose\ *)
        verbose="true"
        query="${query#-v }"
        query="${query#--verbose }"
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
  cmd=$(_ask_query "$iterative" "$verbose" "$query")

  if [ -n "$cmd" ]; then
    BUFFER=""
    local i
    for (( i=0; i<${#cmd}; i++ )); do
      BUFFER="${BUFFER}${cmd:$i:1}"
      CURSOR=$#BUFFER
      zle redisplay
      sleep 0.03
    done
  else
    BUFFER="$query"
    zle redisplay
  fi
}

ask() {
  local iterative="false"
  local verbose="false"

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -h|--help)
        _ask_manual
        return 0
        ;;
      -i|--iterative|--iterativo)
        iterative="true"
        shift
        ;;
      -v|--verbose)
        verbose="true"
        shift
        ;;
      --)
        shift
        break
        ;;
      -*)
        echo "Unknown option: $1" >&2
        _ask_manual
        return 1
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

  local cmd
  cmd=$(_ask_query "$iterative" "$verbose" "$*")

  if [ -n "$cmd" ]; then
    print -z -- "$cmd"
  fi
}

zle -N ask-widget
bindkey '^G' ask-widget

alias pedir='ask'