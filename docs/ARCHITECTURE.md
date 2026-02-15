# DungeonMaster Architecture

This document describes the high-level architecture, component responsibilities, and main data and message flows.

## Design Principles

- **One instance, one campaign** — A single DungeonMaster process serves one campaign. Players interact via private channels (e.g. Discord DMs).
- **Interface-agnostic core** — The engine exposes a single message-handling API; Discord and future UIs are adapters.
- **System-agnostic AI** — Rules and lore come from ingested documents (RAG); no game system is hardcoded.
- **Obsidian-friendly vault** — All persistent content lives in a directory layout you can open in Obsidian.

---

## System Overview

```mermaid
flowchart TB
    subgraph Interfaces
        Discord[Discord Bot]
        Future[Web / CLI / etc.]
    end

    subgraph Core
        Engine[Engine]
        SessionMgr[Session Manager]
        NoteTaker[Note Taker]
    end

    subgraph AI
        Orchestrator[AI Orchestrator]
        RAG[RAG Store]
        Ollama[Ollama Provider]
        Claude[Claude Provider]
    end

    subgraph Data
        Vault[Vault]
        StateStore[State Store]
        Watcher[File Watcher]
    end

    Discord --> Engine
    Future --> Engine
    Engine --> SessionMgr
    Engine --> NoteTaker
    Engine --> Orchestrator
    Engine --> RAG
    Engine --> StateStore
    Orchestrator --> Ollama
    Orchestrator --> Claude
    RAG --> Vault
    StateStore --> Vault
    Watcher --> Vault
    Watcher -.->|re-ingest| RAG
```

| Layer | Responsibility |
|-------|----------------|
| **Interfaces** | Translate platform events (e.g. Discord DM) into `(session_id, user_id, content)` and send replies back. |
| **Core** | Engine orchestrates each message: session history, RAG/state context, AI call, scene/notes updates. Session Manager holds in-memory conversation; Note Taker appends to vault Markdown. |
| **AI** | Orchestrator routes by task type (narrative vs ruling). RAG retrieves relevant rule chunks from ChromaDB. Providers (Ollama, Claude) perform completion and embeddings. |
| **Data** | Vault is the single root for all paths. State Store reads/writes scene JSON and character/NPC Markdown. File Watcher triggers re-ingest or refresh on vault changes. |

---

## Message Flow (Request to Response)

When a player sends a message (e.g. via Discord DM), the following flow runs:

```mermaid
sequenceDiagram
    participant User
    participant Discord as Discord Bot
    participant Engine
    participant Session as Session Manager
    participant RAG
    participant State as State Store
    participant Orch as AI Orchestrator
    participant LLM as LLM Provider
    participant Notes as Note Taker

    User->>Discord: DM or slash command
    Discord->>Engine: handle_message(session_id, user_id, content)

    Engine->>Session: get_or_create(session_id)
    Engine->>Session: add_turn("user", content)

    Engine->>RAG: query(content, top_k=5)
    RAG-->>Engine: relevant rule chunks

    Engine->>State: load_scene()
    State-->>Engine: SceneState
    Engine->>State: load_character(user_id)
    State-->>Engine: character Markdown

    Note over Engine: Builds system prompt (scene + character + RAG chunks)

    Engine->>Session: to_messages(max_turns)
    Session-->>Engine: recent conversation

    Engine->>Orch: generate(prompt, system, task_type)
    Orch->>LLM: generate (narrative or ruling model)
    LLM-->>Orch: GenerateResult
    Orch-->>Engine: reply text

    Engine->>Session: add_turn("assistant", reply)

    alt Reply contains JSON scene block
        Engine->>State: save_scene(parsed SceneState)
    end

    Engine->>Notes: note_event("player", content)
    Engine->>Notes: note_event("dm", reply)

    Engine-->>Discord: return reply
    Discord-->>User: send message
```

---

## AI Task Routing

The orchestrator chooses which provider (and thus which model) to use based on `task_type`:

```mermaid
flowchart LR
    subgraph Input
        Msg[User message]
        Type[task_type]
    end

    subgraph Orchestrator
        Route{task_type?}
        Narrative[Ollama narrative model]
        Ruling[Claude ruling model]
    end

    subgraph Output
        Reply[Reply text]
    end

    Msg --> Route
    Type --> Route
    Route -->|narrative| Narrative
    Route -->|ruling| Ruling
    Narrative --> Reply
    Ruling --> Reply
```

- **narrative** — Flavor text, descriptions, in-world response. Typically a faster/cheaper model (e.g. Ollama).
- **ruling** — Rules questions, planning, adjudication. Typically a stronger model (e.g. Claude).

Slash commands map as follows: `/action`, `/say`, and plain DM text use narrative; `/status`, `/notes` use ruling.

---

## RAG Pipeline

Rulebooks and source documents in the vault are chunked, embedded, and stored for retrieval:

```mermaid
flowchart LR
    subgraph Ingest
        Files[systems/*.md, *.txt]
        Chunk[Chunk text]
        Embed[Embed via Ollama]
        Chroma[ChromaDB]
    end

    subgraph Query
        Q[User query]
        QEmbed[Embed query]
        Retrieve[Retrieve top_k]
        Chunks[Chunk texts]
    end

    Files --> Chunk
    Chunk --> Embed
    Embed --> Chroma
    Q --> QEmbed
    QEmbed --> Retrieve
    Chroma --> Retrieve
    Retrieve --> Chunks
```

- **Ingest**: `VaultWatcher` or startup triggers `RAGStore.ingest_path` / `ingest_all`. Text is split with a sliding window (chunk_size, overlap), embedded with the configured embedding model, and upserted into ChromaDB (persisted under `vault/_index/chroma`).
- **Query**: On each `handle_message`, the engine calls `RAGStore.query(message_content, top_k=5)`. Retrieved chunks are injected into the system prompt so the model can cite rules without hardcoding.

---

## File Watcher and Re-ingestion

```mermaid
flowchart TB
    subgraph External
        Obsidian[Obsidian / editor]
        FS[Filesystem]
    end

    subgraph DungeonMaster
        Watcher[VaultWatcher]
        Callback[on_system_change]
        Loop[Event loop]
        RAG[RAGStore]
    end

    Obsidian -->|edit| FS
    FS -->|inotify / events| Watcher
    Watcher -->|path| Callback
    Callback -->|run_coroutine_threadsafe| Loop
    Loop -->|delete_by_source + ingest_path| RAG
```

- **systems/** — A change (create/edit/delete) triggers re-ingestion for that path: existing chunks from that source are removed, then the file is re-chunked and re-embedded.
- **characters/**, **npcs/** — Changes can be wired to refresh in-memory state or notify the engine (e.g. "character sheet updated"); the current implementation focuses on system re-ingest.

---

## Component Dependencies (Simplified)

```mermaid
flowchart TD
    Main[main.py]
    Config[config]
    Vault[data.vault]
    State[data.state]
    Watcher[data.watcher]
    RAG[ai.rag]
    Orch[ai.orchestrator]
    Providers[ai.providers]
    Engine[core.engine]
    Session[core.session]
    NoteTaker[core.note_taker]
    Discord[interfaces.discord]

    Main --> Config
    Main --> Vault
    Main --> State
    Main --> Watcher
    Main --> RAG
    Main --> Orch
    Main --> Providers
    Main --> Engine
    Main --> Session
    Main --> NoteTaker
    Main --> Discord

    Engine --> Orch
    Engine --> RAG
    Engine --> State
    Engine --> Session
    Engine --> NoteTaker

    RAG --> Vault
    State --> Vault
    Watcher --> Vault
    Orch --> Providers
    Discord --> Engine
```

---

## Concurrency and Threading

- **Main thread** runs the asyncio event loop: Discord bot, engine `handle_message`, RAG query/ingest, orchestrator.
- **Watcher** runs in a background thread (watchdog `Observer`). When a file changes, it invokes a sync callback; the callback uses `asyncio.run_coroutine_threadsafe(reingest(), loop)` to schedule async re-ingest on the main loop.

---

## Related Documentation

- [Vault and state](VAULT_AND_STATE.md) — Directory layout, scene JSON schema, character/NPC Markdown.
- [README](../README.md) — Quick start, configuration, Docker.
