0="${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
0="${${(M)0:#/*}:-$PWD/$0}"
SUGGESTER_PLUGIN_DIR="${0:h}"

source "${SUGGESTER_PLUGIN_DIR}/lib/manual.zsh"
source "${SUGGESTER_PLUGIN_DIR}/lib/security.zsh"
source "${SUGGESTER_PLUGIN_DIR}/lib/query.zsh"
source "${SUGGESTER_PLUGIN_DIR}/lib/ui.zsh"