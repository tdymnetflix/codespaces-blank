# Repository-local Hermes home

Hermes Agent and Hermes WebUI use this directory for repository-specific state,
including skills, memory, and configuration that should survive new GitHub
Actions runners.

Hermes curated memory is stored in:

- `memories/MEMORY.md` for project and environment knowledge
- `memories/USER.md` for user preferences and working style

The GitHub workflow enables Hermes's `memory` toolset and commits these files
after each run. The WebUI uses the same mounted Hermes home, so both interfaces
read and update the same memory.

Credential files, logs, caches, and token-like files are excluded by the root
`.gitignore`. Do not store API keys or passwords in any tracked file here.