# DungeonMaster

AI-powered Dungeon Master for TTRPGs (D&D, Pathfinder, homebrew, etc.). One instance runs a single campaign; players interact by **private messaging** the DM (e.g. Discord DMs). Content lives in an **Obsidian-compatible** vault (Markdown + JSON state); the AI is **modular** (Ollama, Claude, etc.) and **system-agnostic** (ingests your rulebooks and infers from them).

## Features

- **Modular interfaces** — Discord bot first; other UIs (web, CLI) can be added
- **System-agnostic** — Add rulebooks/source docs (Markdown/TXT) to the vault; no hardcoded rules
- **Note-taking** — Session notes written to the vault as Markdown
- **Modular AI** — Ollama (local) and Claude (API) supported; narrative vs ruling routing; parallel use possible
- **Obsidian-compatible** — All generated/edited content in a single vault (systems, notes, characters, NPCs, state)
- **Filesystem-aware** — Watches vault for changes and re-ingests or refreshes behavior
- **Stateful** — Character sheets and NPCs as Markdown; current scene as JSON for VTT/frontend sync

## Requirements

- Python 3.10–3.12 (3.14 not yet supported due to ChromaDB/pydantic)
- [Ollama](https://ollama.ai) (local models and embeddings) — optional if using only API providers
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Optional: Anthropic API key for Claude (rulings)

## Quick start

1. **Clone and install**

   ```bash
   git clone https://github.com/your-org/DungeonMaster.git
   cd DungeonMaster
   pip install -e ".[dev]"
   ```

2. **Configure**

   - Copy `config/default.yaml` or set env vars: `DISCORD_BOT_TOKEN`, `ANTHROPIC_API_KEY` (optional).
   - Set vault path: `VAULT_PATH` or `vault.path` in config (default: `data`).

3. **Vault layout**

   - `data/systems/` — Put rulebooks/source docs here (`.md`, `.txt`).
   - `data/characters/` — Player character sheets (Markdown); created/updated by you or the DM.
   - `data/state/scene.json` — Current scene (who/what/where); written by the DM.

4. **Run**

   ```bash
   python -m dungeonmaster.main
   ```

   Or with explicit config:

   ```bash
   DUNGEONMASTER_CONFIG=config/default.yaml DISCORD_BOT_TOKEN=your_token python -m dungeonmaster.main
   ```

5. **Discord**

   - Invite the bot with DM permissions. Players **DM the bot** to play.
   - Slash commands: `/start`, `/action`, `/say`, `/status`, `/notes`.

## Docker

```bash
cd DungeonMaster
export DISCORD_BOT_TOKEN=your_token
docker compose -f docker/docker-compose.yml up --build
```

Mount your vault: the compose file mounts `../data` at `/data`. Set `VAULT_PATH=/data` (or equivalent) so the app uses it. For local Ollama, point the app at the host (e.g. `http://host.docker.internal:11434`).

## Project layout

```
DungeonMaster/
├── config/default.yaml    # Config (env vars for secrets)
├── data/                  # Vault root (Obsidian-friendly)
│   ├── systems/           # Rulebooks
│   ├── notes/             # Session notes
│   ├── characters/        # Player sheets
│   ├── npcs/              # NPCs
│   ├── state/scene.json   # Current scene (JSON)
│   └── _index/            # ChromaDB (internal)
├── src/dungeonmaster/
│   ├── main.py            # Entrypoint
│   ├── config.py          # YAML + env
│   ├── core/              # Engine, session, note_taker
│   ├── ai/                # Orchestrator, RAG, providers (ollama, claude)
│   ├── data/              # Vault, state, watcher
│   └── interfaces/        # Discord bot
├── tests/
├── docker/
└── .github/workflows/ci.yml
```

## Development

- **Tests:** `pytest tests -v` (use Python 3.10–3.12 for full suite; RAG tests are skipped on 3.14)
- **Coverage:** `pytest tests --cov=src/dungeonmaster --cov-report=term-missing`
- **Lint:** `ruff check src tests && ruff format --check src tests`

CI runs on push/PR via GitHub Actions (test matrix: Python 3.10–3.12, plus ruff lint/format).

## Configuration

| Env / config           | Description                          |
|------------------------|--------------------------------------|
| `DISCORD_BOT_TOKEN`    | Discord bot token                    |
| `ANTHROPIC_API_KEY`    | Claude API key (optional)            |
| `VAULT_PATH`           | Override vault root path             |
| `DUNGEONMASTER_CONFIG` | Path to YAML config file             |

In `config/default.yaml` you can set Ollama URL, model names, RAG chunk size, and `discord.dm_only`.

## License

MIT.
