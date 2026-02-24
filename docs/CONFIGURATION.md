# DungeonMaster Configuration Reference

This document provides a comprehensive reference for all configuration options in DungeonMaster.

## Table of Contents

- [Configuration Sources](#configuration-sources)
- [Secrets Management](#secrets-management)
- [Configuration Options](#configuration-options)
  - [Vault Configuration](#vault-configuration)
  - [AI Configuration](#ai-configuration)
  - [RAG Configuration](#rag-configuration)
  - [Discord Configuration](#discord-configuration)
- [Environment Variables](#environment-variables)
- [Example Configurations](#example-configurations)

---

## Configuration Sources

DungeonMaster loads configuration from multiple sources with the following precedence (highest first):

1. **Environment variables** — Override specific config values
2. **secrets.json** — API keys and tokens (not committed to version control)
3. **YAML config file** — Full configuration structure

### Config File Resolution

The YAML config file is found in this order:

1. Path specified via `DUNGEONMASTER_CONFIG` environment variable
2. `config/default.yaml` in the current working directory
3. `../config/default.yaml` relative to the working directory
4. Falls back to built-in defaults if no file is found

### Example

```bash
# Use a specific config file
export DUNGEONMASTER_CONFIG=/path/to/my-config.yaml
python -m dungeonmaster.main

# Or rely on default location
cd DungeonMaster
python -m dungeonmaster.main  # Uses config/default.yaml
```

---

## Secrets Management

Sensitive values (API keys, tokens) can be stored in `secrets.json` in the project root. This file should be in `.gitignore` and never committed.

### secrets.json Format

```json
{
  "DISCORD_BOT_TOKEN": "your-discord-bot-token-here",
  "ANTHROPIC_API_KEY": "your-anthropic-api-key-here"
}
```

### Setup

1. Copy the example file:
   ```bash
   cp secrets.example.json secrets.json
   ```

2. Edit `secrets.json` with your actual API keys

3. Ensure `secrets.json` is in `.gitignore` (it should be by default)

### Resolution Order for Placeholders

When the config contains `${VAR_NAME}` placeholders:

1. Check `secrets.json` for the key
2. Check environment variables
3. Keep the original placeholder (logs a warning)

---

## Configuration Options

### Vault Configuration

The vault is the directory containing all campaign data (Obsidian-compatible).

```yaml
vault:
  path: data  # Relative to cwd or absolute path
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `vault.path` | string | `"data"` | Root directory for the vault. Can be relative or absolute. |

**Environment Override:** `VAULT_PATH`

```bash
export VAULT_PATH=/home/user/campaigns/my-campaign
```

### Vault Directory Structure

The vault path will contain:

```
<vault_path>/
├── systems/      # Rulebooks (Markdown/TXT) → RAG ingestion
├── notes/        # Session notes (auto-generated)
├── characters/   # Player character sheets (Markdown)
├── npcs/         # NPC documents (Markdown)
├── state/        # scene.json (current scene state)
└── _index/       # ChromaDB vector store (internal)
```

---

### AI Configuration

Configure AI providers for narrative generation and rule adjudication.

```yaml
ai:
  ollama:
    base_url: http://localhost:11434
    narrative_model: llama3.2
    embedding_model: nomic-embed-text
  claude:
    api_key: ${ANTHROPIC_API_KEY}
    ruling_model: claude-3-5-sonnet-20241022
```

#### Ollama Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ai.ollama.base_url` | string | `"http://localhost:11434"` | Ollama API URL |
| `ai.ollama.narrative_model` | string | `"llama3.2"` | Model for narrative/flavor text |
| `ai.ollama.embedding_model` | string | `"nomic-embed-text"` | Model for RAG embeddings |

**Notes:**
- Ollama must be running locally (or accessible at the specified URL)
- Install models with: `ollama pull llama3.2` and `ollama pull nomic-embed-text`
- For Docker: Use `http://host.docker.internal:11434` to reach host Ollama

#### Claude Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ai.claude.api_key` | string | `""` | Anthropic API key (use `${ANTHROPIC_API_KEY}` placeholder) |
| `ai.claude.ruling_model` | string | `"claude-3-5-sonnet-20241022"` | Model for rules/rulings |

**Environment Override:** `ANTHROPIC_API_KEY`

**Notes:**
- Claude is optional; if not configured, all tasks use the Ollama narrative model
- Get an API key at [console.anthropic.com](https://console.anthropic.com/)
- Claude is used for `/status` commands and rules adjudication

#### Task Type Routing

| Task Type | Default Provider | Use Case |
|-----------|------------------|----------|
| `narrative` | Ollama | Flavor text, descriptions, `/action`, `/say` |
| `ruling` | Claude (fallback: Ollama) | Rules questions, `/status`, `/notes` |

---

### RAG Configuration

Configure Retrieval-Augmented Generation for system-agnostic rules.

```yaml
rag:
  chunk_size: 512
  chunk_overlap: 64
  top_k: 5
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `rag.chunk_size` | int | `512` | Characters per text chunk |
| `rag.chunk_overlap` | int | `64` | Overlap between adjacent chunks |
| `rag.top_k` | int | `5` | Number of chunks to retrieve per query |

**Tuning Guidelines:**

- **`chunk_size`**: Larger chunks provide more context but may include irrelevant text. Start with 512 and adjust.
- **`chunk_overlap`**: Ensures phrases spanning chunk boundaries are captured. 64–128 is typical.
- **`top_k`**: More chunks = more context for the AI, but also higher token usage. 3–7 is a good range.

**How RAG Works:**

1. Files in `vault/systems/` (`.md`, `.txt`) are chunked on startup
2. Chunks are embedded using Ollama's embedding model
3. Embeddings are stored in ChromaDB at `vault/_index/chroma/`
4. On each message, the query is embedded and top-k similar chunks are retrieved
5. Retrieved chunks are injected into the system prompt

---

### Discord Configuration

Configure the Discord bot interface.

```yaml
discord:
  token: ${DISCORD_BOT_TOKEN}
  dm_only: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `discord.token` | string | `""` | Discord bot token (use `${DISCORD_BOT_TOKEN}` placeholder) |
| `discord.dm_only` | bool | `true` | If true, only respond to direct messages (not server channels) |

**Environment Override:** `DISCORD_BOT_TOKEN`

### Setting Up a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" → "Add Bot"
4. Copy the token and add it to `secrets.json` or set `DISCORD_BOT_TOKEN`
5. Enable these Privileged Gateway Intents:
   - Message Content Intent
   - Direct Messages
6. Go to "OAuth2" → "URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Read Message History`, `Use Slash Commands`
7. Use the generated URL to invite the bot to your server

### Available Slash Commands

| Command | Description | Task Type |
|---------|-------------|-----------|
| `/start` | Start or resume session | narrative |
| `/action <action>` | Describe character action | narrative |
| `/say <text>` | Character dialogue | narrative |
| `/status <question>` | Ask for ruling/situation | ruling |
| `/notes` | Get session notes summary | ruling |

---

## Environment Variables

All environment variables that affect configuration:

| Variable | Description | Config Override |
|----------|-------------|-----------------|
| `DUNGEONMASTER_CONFIG` | Path to YAML config file | N/A (meta) |
| `VAULT_PATH` | Vault root directory | `vault.path` |
| `DISCORD_BOT_TOKEN` | Discord bot token | `discord.token` |
| `ANTHROPIC_API_KEY` | Anthropic/Claude API key | `ai.claude.api_key` |

### Using Environment Variables

```bash
# Linux/macOS
export DISCORD_BOT_TOKEN="your-token-here"
export ANTHROPIC_API_KEY="your-key-here"
python -m dungeonmaster.main

# Windows PowerShell
$env:DISCORD_BOT_TOKEN = "your-token-here"
$env:ANTHROPIC_API_KEY = "your-key-here"
python -m dungeonmaster.main

# Windows CMD
set DISCORD_BOT_TOKEN=your-token-here
set ANTHROPIC_API_KEY=your-key-here
python -m dungeonmaster.main
```

---

## Example Configurations

### Minimal (Ollama Only)

For local development with Ollama only (no Claude):

```yaml
vault:
  path: data

ai:
  ollama:
    base_url: http://localhost:11434
    narrative_model: llama3.2
    embedding_model: nomic-embed-text

rag:
  chunk_size: 512
  chunk_overlap: 64
  top_k: 5

discord:
  token: ${DISCORD_BOT_TOKEN}
  dm_only: true
```

### Production (Ollama + Claude)

Full setup with Claude for rulings:

```yaml
vault:
  path: /var/lib/dungeonmaster/campaigns/main

ai:
  ollama:
    base_url: http://localhost:11434
    narrative_model: llama3.2
    embedding_model: nomic-embed-text
  claude:
    api_key: ${ANTHROPIC_API_KEY}
    ruling_model: claude-3-5-sonnet-20241022

rag:
  chunk_size: 768
  chunk_overlap: 96
  top_k: 7

discord:
  token: ${DISCORD_BOT_TOKEN}
  dm_only: true
```

### Docker

For running in Docker with Ollama on the host:

```yaml
vault:
  path: /data  # Maps to host directory via volume

ai:
  ollama:
    base_url: http://host.docker.internal:11434
    narrative_model: llama3.2
    embedding_model: nomic-embed-text
  claude:
    api_key: ${ANTHROPIC_API_KEY}
    ruling_model: claude-3-5-sonnet-20241022

rag:
  chunk_size: 512
  chunk_overlap: 64
  top_k: 5

discord:
  token: ${DISCORD_BOT_TOKEN}
  dm_only: true
```

### Alternative Models

Using different Ollama models:

```yaml
ai:
  ollama:
    base_url: http://localhost:11434
    # Use Mistral for narrative
    narrative_model: mistral:7b
    # Use different embedding model
    embedding_model: mxbai-embed-large
  claude:
    api_key: ${ANTHROPIC_API_KEY}
    # Use Claude 3 Opus for complex rulings
    ruling_model: claude-3-opus-20240229
```

---

## See Also

- [Architecture Overview](ARCHITECTURE.md) — System design and component responsibilities
- [API Reference](API.md) — Python API documentation
- [Vault and State](VAULT_AND_STATE.md) — Data layout and JSON schemas
- [Contributing Guide](../CONTRIBUTING.md) — Development guidelines
