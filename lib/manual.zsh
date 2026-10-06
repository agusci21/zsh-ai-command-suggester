_ask_manual() {
  cat <<'MANUAL'
USAGE:
  ask [-i] [-a] [-v] [-c] "<instruction>"
  pedir [-i] [-a] [-v] [-c] "<instruction>"
  <inline_instruction> [Ctrl + G]

DESCRIPTION:
  Translates natural language instructions into exact terminal commands,
  auto-executes commands, or provides conversational answers using Ollama.

OPTIONS:
  -a, --auto           Auto-execute mode. Runs safe commands immediately.
                       Prompts for confirmation if elevation/destruction is detected.
  -i, --iterative      Enable interactive system inspection before answering.
  -ai, -ia             Combine auto-execution and iterative inspection.
  -v, --verbose        Stream inspection command output to terminal.
  -c, --chat           Conversational output mode instead of command mode.
  -h, --help           Show this manual.

EXAMPLES:
  ask "reiniciar el servicio cron"
  ask -ia "reiniciar el servicio cron"
  ask -c "de que trata este repo?"
MANUAL
}