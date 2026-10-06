# Git Domain Skill

## Triggers
- Queries involving git, commit, commits, commitear, repository status, branches, merges, rebases, stashes, or diffs.

## Inspection Strategy
- Always execute `EXEC: git status -s` first to check modified, untracked, or staged files.
- If more context on actual changes is needed, execute `EXEC: git diff` or `EXEC: git diff --staged`.

## Rules
- When the user asks to commit changes and files are unstaged or untracked:
  * If committing all current changes, ALWAYS use: `git add . && git commit -m "<conventional_commit_message>"`
  * NEVER output only `git add` when a commit is requested. Both commands MUST be chained with `&&`.
- Commit messages MUST strictly follow Conventional Commits format (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- Commit messages MUST be written in English, imperative mood, concise, and reflect the exact inspected modifications.
- Destructive commands (`push`, `reset --hard`, `clean -fd`, `checkout .`) require elevation confirmation and must never be auto-executed silently.