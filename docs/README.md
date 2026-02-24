# DungeonMaster Documentation

Documentation for the DungeonMaster codebase: architecture, data layout, API reference, configuration, and logical flows.

## Contents

| Document | Description |
|----------|-------------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System overview, component diagram, message flow (sequence diagram), AI task routing, RAG pipeline, file watcher, and concurrency. |
| [**VAULT_AND_STATE.md**](VAULT_AND_STATE.md) | Vault directory layout, path conventions, scene JSON schema, character/NPC Markdown, and data flow between vault and engine. |
| [**API.md**](API.md) | Python API reference for all public modules, classes, and functions. |
| [**CONFIGURATION.md**](CONFIGURATION.md) | Comprehensive configuration reference: YAML options, secrets management, environment variables, and example configs. |

## Other Documentation

| Document | Description |
|----------|-------------|
| [**../README.md**](../README.md) | Project overview, quick start, Docker, and development setup. |
| [**../CONTRIBUTING.md**](../CONTRIBUTING.md) | Contributing guidelines, coding standards, testing, and PR process. |

## Diagrams Overview

All diagrams are written in [Mermaid](https://mermaid.js.org/) and render on GitHub and in many Markdown viewers.

### Architecture Diagrams (ARCHITECTURE.md)

- **System overview** — Interfaces, Core, AI, and Data layers and their connections.
- **Message flow** — Sequence from user message through engine, RAG, state, orchestrator, and back to the user.
- **AI task routing** — How `task_type` (narrative vs ruling) selects the provider.
- **RAG pipeline** — Ingest (chunk → embed → ChromaDB) and query (embed → retrieve top_k).
- **File watcher** — How filesystem events trigger re-ingestion on the event loop.
- **Component dependencies** — Module-level dependency graph.

### Data Diagrams (VAULT_AND_STATE.md)

- **Vault layout** — Directory tree and purpose of each path.
- **Vault ↔ engine data flow** — Who reads/writes which vault paths.

## Quick Links

- [Main README](../README.md) — Quick start, configuration, Docker.
- [Contributing Guide](../CONTRIBUTING.md) — Development setup and PR process.
- [Repository](https://github.com/StevenGann/DungeonMaster) — Source and issues.

## Getting Started with the Docs

1. **New to the project?** Start with [ARCHITECTURE.md](ARCHITECTURE.md) for a high-level overview.
2. **Setting up?** See [CONFIGURATION.md](CONFIGURATION.md) for all config options.
3. **Developing?** Check [../CONTRIBUTING.md](../CONTRIBUTING.md) for coding standards.
4. **Building integrations?** Reference [API.md](API.md) for the public Python API.
5. **Managing campaign data?** Read [VAULT_AND_STATE.md](VAULT_AND_STATE.md) for the vault structure.
