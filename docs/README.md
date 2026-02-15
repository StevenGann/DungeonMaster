# DungeonMaster Documentation

Documentation for the DungeonMaster codebase: architecture, data layout, and logical flows.

## Contents

| Document | Description |
|----------|-------------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System overview, component diagram, message flow (sequence diagram), AI task routing, RAG pipeline, file watcher, and concurrency. |
| [**VAULT_AND_STATE.md**](VAULT_AND_STATE.md) | Vault directory layout, path conventions, scene JSON schema, character/NPC Markdown, and data flow between vault and engine. |

## Diagrams Overview

- **System overview** — Interfaces, Core, AI, and Data layers and their connections.
- **Message flow** — Sequence from user message through engine, RAG, state, orchestrator, and back to the user.
- **AI task routing** — How `task_type` (narrative vs ruling) selects the provider.
- **RAG pipeline** — Ingest (chunk → embed → ChromaDB) and query (embed → retrieve top_k).
- **File watcher** — How filesystem events trigger re-ingestion on the event loop.
- **Vault layout** — Directory tree and purpose of each path.
- **Vault ↔ engine data flow** — Who reads/writes which vault paths.

All diagrams are in [Mermaid](https://mermaid.js.org/) and render on GitHub and in many Markdown viewers.

## Quick Links

- [Main README](../README.md) — Quick start, configuration, Docker.
- [Repository](https://github.com/StevenGann/DungeonMaster) — Source and issues.
