# Docker Domain Skill

## Triggers
- Queries involving docker containers, images, volumes, networks, compose, or daemon status.

## Inspection Strategy
- Use fast read-only commands: `EXEC: docker ps -a`, `EXEC: docker images`, `EXEC: docker volume ls`.

## Rules
- Prefer modern CLI syntax: use `docker container ls` instead of legacy `docker ps` when appropriate.
- Destructive operations (`docker rm`, `docker rmi`, `docker system prune`, `docker stop`, `docker kill`) are classified as non-safe and require interactive user confirmation.