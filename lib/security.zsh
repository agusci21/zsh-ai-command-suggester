_ask_is_safe_command() {
  local full_cmd="$1"

  if echo "$full_cmd" | grep -qw "sudo"; then
    return 1
  fi

  if echo "$full_cmd" | grep -qE "(>|>>|rm |dd |chmod |chown |mkfs|reboot|shutdown|systemctl (restart|stop|disable|mask))"; then
    return 1
  fi

  local safe_bins="ip|ls|cat|cd|pwd|uname|whoami|df|du|free|uptime|ps|env|head|tail|grep|awk|sed|which|whereis|file|stat|hostname|nmcli|systemctl|find|locate|xargs|rg|fd"

  local segments
  segments=("${(@s/|/)full_cmd}")

  local segment part
  for segment in "${segments[@]}"; do
    part=$(echo "$segment" | awk '{print $1}')
    case "$part" in
      git)
        if echo "$segment" | grep -qE "(push|commit|reset|clean|checkout|rebase|merge)"; then
          return 1
        fi
        ;;
      docker)
        if ! echo "$segment" | grep -qE "(ps|images|stats|inspect)"; then
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