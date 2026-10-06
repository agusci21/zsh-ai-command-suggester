_ask_is_safe_command() {
  local full_cmd="$1"

  if echo "$full_cmd" | grep -qw "sudo"; then
    return 1
  fi

  if echo "$full_cmd" | grep -qE "(>|>>|rm |dd |chmod |chown |mkfs|reboot|shutdown|systemctl (restart|stop|disable|mask))"; then
    return 1
  fi

local safe_bins="ip|ls|cat|cd|pwd|uname|whoami|df|du|free|uptime|ps|env|head|tail|grep|awk|sed|which|whereis|file|stat|hostname|nmcli|systemctl|find|locate|xargs|rg|fd|searchsploit"
  local segments
  segments=("${(@s/|/)full_cmd}")

  local segment part
  for segment in "${segments[@]}"; do
    part=$(echo "$segment" | awk '{print $1}')
    case "$part" in
      git)
        if ! echo "$segment" | grep -qE "^git\s+(status|diff|log|branch|show|rev-parse|check-ignore|describe)(\s+|$)"; then
          return 1
        fi
        ;;
      docker)
        if echo "$segment" | grep -qE "(rm|rmi|kill|stop|prune|exec)"; then
          return 1
        fi
        if ! echo "$segment" | grep -qE "(ps|images|stats|inspect|container (ls|list|ps)|volume (ls|list)|network (ls|list))"; then
          return 1
        fi
        ;;
      *)
        if ! echo "$part" | grep -qE "^(${safe_bins})$"; then
          return 1
        fi
        ;;
    esac
  done

  return 0
}

_ask_requires_elevation() {
  local cmd="$1"

  if echo "$cmd" | grep -qw "sudo"; then
    return 0
  fi

  if echo "$cmd" | grep -qE "(rm\s+-|dd\s+|mkfs|reboot|shutdown|systemctl (restart|stop|disable|mask)|docker (rm|rmi|kill|stop|prune))"; then
    return 0
  fi

  if echo "$cmd" | grep -qE "(^|\s|&&|\|\|)git\s+(commit|push|add|rm|merge|rebase|tag|cherry-pick|reset|clean|checkout)(\s+|$)"; then
    return 0
  fi

  return 1
}