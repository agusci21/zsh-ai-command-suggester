# zsh-ai-command-suggester

A lightweight Zsh / Oh My Zsh plugin that translates natural language requests into exact terminal commands using local **Ollama** models.

## Features
- Direct insertion via interactive ZLE typing animation (`Ctrl + G`).
- Standard CLI invocation (`ask "..."` or `pedir "..."`).
- Host network context injection (interfaces, subnets, routes) to avoid hallucinated IPs.
- Iterative mode (`-i`, `--iterative`) with auto-approved read-only inspections and confirmation prompts for commands requiring elevated privileges or `sudo`.
- Verbose mode (`-v`, `--verbose`) to stream inspection stdout/stderr directly to the terminal.
