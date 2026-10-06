_ask_manual() {
  cat <<'MANUAL'
USAGE:
  ask [-i] [-v] "<instruction>"
  pedir [-i] [-v] "<instruction>"
  <inline_instruction> [Ctrl + G]

DESCRIPTION:
  Translates natural language instructions into exact terminal commands
  using a local Ollama model. Does not execute the command directly;
  it loads it into the interactive buffer for user review.

MODES:
  1. Direct Mode (default):
     Resolves the query with preloaded system context (IP, route, OS).
     Example:
       ask "list open listening tcp ports"

  2. Iterative Mode (-i, --iterative):
     Allows the model to run safe read-only inspection commands.
     - Safe commands (ip, ls, cat, df, etc.): Automated execution.
     - Sudo or commands outside the whitelist: Require user confirmation (y/N).
     Example:
       ask -i "scan local network devices using nmap"

  3. Verbose Mode (-v, --verbose):
     Streams stdout and stderr of inspection commands to the terminal.
     Example:
       ask -i -v "check why docker service failed"

  4. Interactive Mode (ZLE Widget):
     Type your prompt directly into the line without pressing enter, then press:
       Ctrl + G

OPTIONS:
  -i, --iterative      Enable interactive system inspection.
  -v, --verbose        Stream execution output to terminal.
  -h, --help           Show this help manual.

ENVIRONMENT VARIABLES:
  OLLAMA_HOST_IP       Ollama server URL (default: http://localhost:11434).
  OLLAMA_MODEL         Model used (default: qwen2.5-coder:7b).
MANUAL
}