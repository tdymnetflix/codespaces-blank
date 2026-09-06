# Repository-local Hermes home

Hermes Agent and Hermes WebUI use this directory for repository-specific state,
including skills, memory, and configuration that should survive new GitHub
Actions runners.

Credential files, logs, caches, and token-like files are excluded by the root
`.gitignore`. Do not store API keys or passwords in any tracked file here.