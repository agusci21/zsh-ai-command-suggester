# Git Domain Skill

## Triggers
- Queries involving git, commits, repository status, branches, merges, rebases, stashes, or diffs.

## Inspection Strategy
- Always execute `EXEC: git status -s` first to check modified, untracked, or staged files.
- If more context on actual changes is needed, execute `EXEC: git diff` or `EXEC: git diff --staged`.

## Rules
- If files are untracked (`??`) or unstaged (` M`, ` D`), the final command MUST stage them first (e.g., `git add <files>` or `git add .`) before executing the commit.
- Commit messages MUST strictly follow Conventional Commits format (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- Commit messages MUST be written in English, imperative mood, concise, and reflect the exact inspected modifications.
- Destructive commands (`push`, `reset --hard`, `clean -fd`, `checkout .`) require elevation confirmation and must never be auto-executed silently.