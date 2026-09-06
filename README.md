# Hermes Agent GitHub Workspace

This repository is a small integration layer that gives [Hermes Agent](https://github.com/NousResearch/hermes-agent) two ways to work on the same codebase:

1. **GitHub Issues:** trusted collaborators can ask Hermes to inspect, edit, test, and commit repository changes through GitHub Actions.
2. **Hermes WebUI:** a browser interface runs locally in Docker and provides interactive Hermes sessions.

The GitHub workflow is inspired by [IssueClaw](https://github.com/Free-AI-Things/issueclaw). The WebUI is provided by [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui).

## How It Works

### GitHub Issue agent

The workflow in `.github/workflows/hermes.yml` runs when a trusted user opens an Issue or adds a comment. It:

1. Checks out the repository with full Git history.
2. Installs the latest Hermes Agent release using `uv`.
3. Passes the Issue title, body, and latest comment to Hermes.
4. Gives Hermes the terminal toolset so it can inspect files, make changes, and run checks.
5. Commits changes using the GitHub Actions bot identity.
6. Posts the result back to the Issue.

Hermes memory is stored in `.hermes/memories/MEMORY.md` and
`.hermes/memories/USER.md`. The workflow commits those files so memory survives
the temporary GitHub runner.

Runs are serialized per Issue so two comments cannot edit the repository simultaneously. Each run is limited to 30 minutes and 30 agent turns.

### Local WebUI

The WebUI is a persistent Docker service, separate from GitHub Actions. `docker-compose.yml` uses the upstream `ghcr.io/nesquena/hermes-webui:latest` image, mounts Hermes state from `~/.hermes`, and mounts this repository at `/workspace`.

## GitHub Setup

1. Add an `OPENROUTER_API_KEY` repository secret under **Settings -> Secrets and variables -> Actions**.
2. Optionally add a repository variable called `HERMES_MODEL`. The default is `openrouter/anthropic/claude-sonnet-4`.
3. Enable GitHub Actions.
4. Open an Issue using the **Hermes task** template.

Only repository owners, members, and collaborators can trigger the workflow. The workflow grants `contents: write` and `issues: write`, allowing Hermes to commit and reply. Review generated commits and workflow logs before merging higher-risk changes.

## Run the WebUI

```bash
cp .env.example .env
docker compose up -d
```

Open [http://localhost:8787](http://localhost:8787). Stop the service with:

```bash
docker compose down
```

The default port binding is localhost-only. To expose it through a reverse proxy or tunnel, set `HERMES_WEBUI_BIND` in `.env` and configure a strong `HERMES_WEBUI_PASSWORD`. Never expose the WebUI publicly without authentication and HTTPS.

## Temporary Cloudflare Link

For development, `cloudflared` can forward the local WebUI to a temporary public URL:

```bash
./bin/cloudflared tunnel --url http://127.0.0.1:8787
```

The current generated URL is recorded in [CLOUDFLARE_TUNNEL_URL.md](CLOUDFLARE_TUNNEL_URL.md). Quick Tunnel URLs are public, unauthenticated, temporary, and stop working when `cloudflared` exits. Do not use this mode for production or sensitive work.

## Cloudflare AI Proxy

[`scripts/cf-proxy.py`](scripts/cf-proxy.py) is a localhost-only OpenAI-compatible proxy for Cloudflare Workers AI. It fetches the account list from the Bitbucket raw URL at startup, keeps credentials in memory, and rotates accounts when Cloudflare returns HTTP `429`:

```bash
python3 scripts/cf-proxy.py
```

Hermes can use `http://127.0.0.1:8788/v1` as an OpenAI-compatible base URL. Set `CF_CREDENTIALS_URL` to use another source. For a private Bitbucket source, provide `BITBUCKET_USERNAME` and `BITBUCKET_APP_PASSWORD` through the environment; never put them in the repository. The proxy does not save the downloaded credential file.

The optional local fallback path `credentials/cloudflare.txt` is ignored by `.gitignore`. Do not expose port `8788` publicly.

Run [`scripts/change-model`](scripts/change-model) to configure Hermes to use the proxy and the Cloudflare `@cf/zai-org/glm-4.7-flash` model:

```bash
bash scripts/change-model
```

This stores the model configuration under the repository-local `.hermes` home. Override `CF_MODEL` or `CF_PROXY_URL` when needed. The script leaves Hermes secret and PII redaction enabled.

## Repository Files

| File | Purpose |
| --- | --- |
| `.github/workflows/hermes.yml` | Issue and comment trigger for the GitHub agent |
| `.github/ISSUE_TEMPLATE/hermes-task.md` | Structured prompt template for Hermes tasks |
| `docker-compose.yml` | Local Hermes WebUI service |
| `.env.example` | Local Compose configuration template |
| `AGENTS.md` | Instructions Hermes should follow while changing the repository |
| `CLOUDFLARE_TUNNEL_URL.md` | Current temporary development URL |
| `scripts/cf-proxy.py` | Local Cloudflare Workers AI proxy with 429 account rotation |
| `scripts/change-model` | Configures Hermes to use the local Cloudflare proxy |

Secrets, `.hermes` state, the local `cloudflared` binary, and `.env` are excluded by `.gitignore`.