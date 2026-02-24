# DungeonMaster API Reference

This document provides a comprehensive reference for the public Python API of each module in DungeonMaster. For architectural overview and data flow, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Table of Contents

- [Core Modules](#core-modules)
  - [dungeonmaster.core.engine](#dungeonmastercoreengine)
  - [dungeonmaster.core.session](#dungeonmastercoresession)
  - [dungeonmaster.core.note_taker](#dungeonmastercorenote_taker)
- [AI Modules](#ai-modules)
  - [dungeonmaster.ai.orchestrator](#dungeonmasteraiorchestrator)
  - [dungeonmaster.ai.rag](#dungeonmasterairag)
  - [dungeonmaster.ai.providers.base](#dungeonmasteraiprovidersbase)
  - [dungeonmaster.ai.providers.ollama](#dungeonmasteraiprovidersollama)
  - [dungeonmaster.ai.providers.claude](#dungeonmasteraiprovidersclaude)
- [Data Modules](#data-modules)
  - [dungeonmaster.data.vault](#dungeonmasterdatavault)
  - [dungeonmaster.data.state](#dungeonmasterdatastate)
  - [dungeonmaster.data.watcher](#dungeonmasterdatawatcher)
- [Interfaces](#interfaces)
  - [dungeonmaster.interfaces.discord](#dungeonmasterinterfacesdiscord)
- [Configuration](#configuration)
  - [dungeonmaster.config](#dungeonmasterconfig)

---

## Core Modules

### dungeonmaster.core.engine

The central message-handling engine that orchestrates all components.

#### `Engine`

```python
class Engine:
    """
    Single entrypoint for handling a player message: load context (RAG, state, character),
    call orchestrator, optionally update scene from structured output, append notes.
    """

    def __init__(
        self,
        orchestrator: AIOrchestrator,
        rag: RAGStore | None,
        state_store: StateStore,
        session_manager: SessionManager,
        note_taker: NoteTaker | None = None,
    ) -> None:
        """
        Initialize the engine with all required components.

        Args:
            orchestrator: AI orchestrator for routing generation to providers.
            rag: RAG store for retrieving relevant rule chunks (optional).
            state_store: State store for scene and character data.
            session_manager: Manager for player conversation sessions.
            note_taker: Note taker for logging events to the vault (optional).
        """

    async def handle_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        task_type: str = "narrative",
    ) -> str:
        """
        Process one user message through the full pipeline.

        Steps:
        1. Add message to session history
        2. Query RAG for relevant rule chunks
        3. Load current scene and player character
        4. Build system prompt with context
        5. Generate AI response via orchestrator
        6. Parse and save any scene updates from response
        7. Log events to note taker

        Args:
            session_id: Unique identifier for the player session (e.g., Discord user ID).
            user_id: Player identifier for loading character sheet.
            content: The player's message content.
            task_type: Type of task - "narrative" for flavor text, "ruling" for rules.

        Returns:
            The AI-generated response text.
        """
```

---

### dungeonmaster.core.session

Per-player session management for conversation history.

#### `Turn`

```python
@dataclass
class Turn:
    """
    A single conversation turn with role and content.

    Attributes:
        role: The speaker - "user" for player, "assistant" for DM.
        content: The message content.
    """
    role: str
    content: str
```

#### `Session`

```python
@dataclass
class Session:
    """
    Per-player session holding conversation history and metadata.

    Attributes:
        session_id: Unique identifier (e.g., Discord user ID).
        turns: List of conversation turns.
        metadata: Optional key-value metadata.
    """
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, content: str) -> None:
        """
        Append a new turn to the conversation.

        Args:
            role: Speaker role - "user" or "assistant".
            content: Message content.
        """

    def get_recent_turns(self, max_turns: int = 20) -> list[Turn]:
        """
        Get the most recent turns for context window.

        Args:
            max_turns: Maximum number of turns to return.

        Returns:
            List of most recent Turn objects.
        """

    def to_messages(self, max_turns: int = 20) -> list[dict[str, str]]:
        """
        Format recent turns as message dictionaries.

        Args:
            max_turns: Maximum number of turns to include.

        Returns:
            List of dicts with "role" and "content" keys.
        """
```

#### `SessionManager`

```python
class SessionManager:
    """
    In-memory session store. One campaign = one manager instance.
    """

    def __init__(self) -> None:
        """Initialize an empty session store."""

    def get_or_create(self, session_id: str) -> Session:
        """
        Get an existing session or create a new one.

        Args:
            session_id: Unique session identifier.

        Returns:
            The Session object (existing or newly created).
        """

    def get(self, session_id: str) -> Session | None:
        """
        Get a session by ID without creating.

        Args:
            session_id: Unique session identifier.

        Returns:
            The Session if it exists, None otherwise.
        """
```

---

### dungeonmaster.core.note_taker

Session logging to Markdown files in the vault.

#### `NoteTaker`

```python
class NoteTaker:
    """
    Writes session events to vault notes/ directory as Markdown.
    Creates rolling or per-session note files.
    """

    def __init__(self, vault: Vault, note_id: str | None = None) -> None:
        """
        Initialize the note taker.

        Args:
            vault: Vault instance for file I/O.
            note_id: Optional note file identifier. Defaults to "session-YYYYMMDD".
        """

    def append(self, content: str) -> None:
        """
        Append content to the current note file.

        Args:
            content: Text content to append.
        """

    def note_event(self, role: str, content: str) -> None:
        """
        Record a timestamped event.

        Args:
            role: Event source - "player" or "dm".
            content: Event content.
        """
```

---

## AI Modules

### dungeonmaster.ai.orchestrator

Task-based routing to AI providers.

#### `AIOrchestrator`

```python
class AIOrchestrator:
    """
    Routes generation by task type: narrative (cheaper/faster) vs ruling (smarter).
    Falls back to available provider if preferred is not set.
    """

    def __init__(
        self,
        narrative_provider: BaseAIProvider | None = None,
        ruling_provider: BaseAIProvider | None = None,
    ) -> None:
        """
        Initialize with narrative and/or ruling providers.

        Args:
            narrative_provider: Provider for narrative/flavor text (e.g., Ollama).
            ruling_provider: Provider for rules/planning (e.g., Claude).
        """

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        task_type: str = "narrative",
        **kwargs: Any,
    ) -> GenerateResult:
        """
        Generate with the appropriate provider based on task type.

        Args:
            prompt: User prompt text.
            system: Optional system message for context.
            task_type: "narrative" or "ruling" to select provider.
            **kwargs: Additional provider-specific arguments.

        Returns:
            GenerateResult with text, model name, and raw response.
        """

    async def generate_narrative(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate using the narrative provider."""

    async def generate_ruling(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate using the ruling provider."""
```

---

### dungeonmaster.ai.rag

Retrieval-Augmented Generation for system-agnostic rules.

#### `RAGStore`

```python
class RAGStore:
    """
    Ingest Markdown/TXT from vault systems/, chunk, embed, store in ChromaDB.
    Retrieve relevant chunks for queries.
    """

    def __init__(
        self,
        vault: Vault,
        embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        top_k: int = 5,
        collection_name: str = "dungeonmaster_systems",
        chroma_client: Any = None,
    ) -> None:
        """
        Initialize the RAG store.

        Args:
            vault: Vault instance for file access.
            embed_fn: Async function to embed text (e.g., Ollama embeddings).
            chunk_size: Characters per chunk.
            chunk_overlap: Overlap between adjacent chunks.
            top_k: Default number of chunks to retrieve.
            collection_name: ChromaDB collection name.
            chroma_client: Optional pre-configured ChromaDB client.
        """

    async def ingest_path(self, path: Path) -> int:
        """
        Ingest one file: chunk, embed, add to ChromaDB.

        Args:
            path: Path to the file to ingest.

        Returns:
            Number of chunks added.
        """

    async def ingest_all(self) -> int:
        """
        Ingest all system files from the vault.

        Returns:
            Total number of chunks added across all files.
        """

    async def query(self, query_text: str, top_k: int | None = None) -> list[str]:
        """
        Retrieve most relevant chunks for a query.

        Args:
            query_text: Text to search for.
            top_k: Number of chunks to retrieve (uses default if None).

        Returns:
            List of chunk text strings, most relevant first.
        """

    def delete_by_source(self, source_path: str) -> None:
        """
        Remove all chunks from a specific source file.

        Args:
            source_path: Path string of the source file.
        """
```

#### `_chunk_text`

```python
def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Sliding-window text chunking by character count.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Characters shared between adjacent chunks.

    Returns:
        List of text chunks.
    """
```

---

### dungeonmaster.ai.providers.base

Abstract base class for AI providers.

#### `GenerateResult`

```python
@dataclass
class GenerateResult:
    """
    Result of a completion call.

    Attributes:
        text: Generated text content.
        model: Model identifier used.
        raw: Provider-specific raw response object.
    """
    text: str
    model: str
    raw: Any = None
```

#### `BaseAIProvider`

```python
class BaseAIProvider(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'ollama', 'claude')."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """
        Generate a completion.

        Args:
            prompt: User prompt text.
            model: Model to use (optional, uses default if not specified).
            system: Optional system message.
            **kwargs: Provider-specific arguments.

        Returns:
            GenerateResult with generated text.
        """

    async def is_available(self) -> bool:
        """
        Check if the provider is available.

        Returns:
            True if provider can be used, False otherwise.
        """
```

---

### dungeonmaster.ai.providers.ollama

Local LLM provider using Ollama.

#### `OllamaProvider`

```python
class OllamaProvider(BaseAIProvider):
    """Generate completions and embeddings via local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API URL.
            default_model: Default model for text generation.
            embedding_model: Model for embeddings.
        """

    @property
    def name(self) -> str:
        """Returns 'ollama'."""

    @property
    def default_model(self) -> str:
        """Default text generation model."""

    @property
    def embedding_model(self) -> str:
        """Embedding model name."""

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate completion via Ollama chat API."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """

    async def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
```

---

### dungeonmaster.ai.providers.claude

Anthropic Claude provider for advanced reasoning.

#### `ClaudeProvider`

```python
class ClaudeProvider(BaseAIProvider):
    """Generate completions via Anthropic Claude API."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key.
            default_model: Default Claude model.
        """

    @property
    def name(self) -> str:
        """Returns 'claude'."""

    @property
    def default_model(self) -> str:
        """Default Claude model name."""

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate completion via Claude Messages API."""

    async def is_available(self) -> bool:
        """Check if API key is configured."""
```

---

## Data Modules

### dungeonmaster.data.vault

Obsidian-compatible file storage abstraction.

#### `Vault`

```python
class Vault:
    """
    Unified vault root for all persistent content.

    Directory layout:
        systems/    - rulebooks (Markdown/TXT)
        notes/      - session notes
        characters/ - player character sheets
        npcs/       - NPC documents
        state/      - scene.json
        _index/     - internal (embeddings)
    """

    def __init__(self, root: str | Path) -> None:
        """
        Initialize vault at the given root path.

        Args:
            root: Root directory path for the vault.
        """

    @property
    def root(self) -> Path:
        """Vault root directory path."""

    def ensure_all_dirs(self) -> None:
        """Create all vault subdirectories if they don't exist."""

    # Path helpers
    def systems_dir(self) -> Path:
        """Path to systems/ directory."""

    def notes_dir(self) -> Path:
        """Path to notes/ directory."""

    def characters_dir(self) -> Path:
        """Path to characters/ directory."""

    def npcs_dir(self) -> Path:
        """Path to npcs/ directory."""

    def state_dir(self) -> Path:
        """Path to state/ directory."""

    def index_dir(self) -> Path:
        """Path to _index/ directory."""

    def scene_path(self) -> Path:
        """Path to state/scene.json."""

    def character_path(self, player_id: str) -> Path:
        """
        Path to a player's character sheet.

        Args:
            player_id: Player identifier (sanitized to safe filename).

        Returns:
            Path to characters/<player_id>.md
        """

    def npc_path(self, npc_id: str) -> Path:
        """
        Path to an NPC document.

        Args:
            npc_id: NPC identifier (sanitized to safe filename).

        Returns:
            Path to npcs/<npc_id>.md
        """

    def note_path(self, note_id: str) -> Path:
        """
        Path to a note file.

        Args:
            note_id: Note identifier.

        Returns:
            Path to notes/<note_id>.md
        """

    # Read/write methods
    def read_text(self, path: Path) -> str:
        """Read file as UTF-8 text."""

    def write_text(self, path: Path, content: str) -> None:
        """Write UTF-8 text, creating parent directories if needed."""

    def read_bytes(self, path: Path) -> bytes:
        """Read file as bytes."""

    def exists(self, path: Path) -> bool:
        """Check if path exists."""

    def list_system_files(self) -> list[Path]:
        """List all .md and .txt files under systems/ recursively."""
```

---

### dungeonmaster.data.state

Scene and character state management.

#### `Position`

```python
@dataclass
class Position:
    """
    Spatial position of an entity in the scene.

    Attributes:
        entity_id: Unique entity identifier.
        entity_type: Type - "player", "npc", or "object".
        x: X coordinate.
        y: Y coordinate.
        zone: Optional zone/area name.
    """
    entity_id: str
    entity_type: str
    x: float = 0.0
    y: float = 0.0
    zone: str = ""
```

#### `Location`

```python
@dataclass
class Location:
    """
    Current scene location.

    Attributes:
        name: Location name (e.g., "The Rusty Dagger").
        description: Short location description.
    """
    name: str = ""
    description: str = ""
```

#### `SceneState`

```python
@dataclass
class SceneState:
    """
    Current scene state for VTT/frontend sync.

    Attributes:
        scene_id: Unique scene identifier.
        location: Current location details.
        positions: List of entity positions.
        turn_order: Entity IDs in initiative order.
        timestamp: ISO 8601 timestamp.
    """
    scene_id: str = "default"
    location: Location = field(default_factory=Location)
    positions: list[Position] = field(default_factory=list)
    turn_order: list[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneState":
        """Create SceneState from dictionary."""
```

#### `StateStore`

```python
class StateStore:
    """Read/write scene state and character/NPC Markdown from the vault."""

    def __init__(self, vault: Vault) -> None:
        """
        Initialize state store with vault.

        Args:
            vault: Vault instance for file I/O.
        """

    def load_scene(self) -> SceneState:
        """
        Load scene.json, returning default SceneState if missing or invalid.

        Returns:
            Current SceneState.
        """

    def save_scene(self, scene: SceneState) -> None:
        """
        Write scene state to scene.json.

        Args:
            scene: SceneState to save.
        """

    def load_character(self, player_id: str) -> str:
        """
        Load a player's character sheet as Markdown.

        Args:
            player_id: Player identifier.

        Returns:
            Character sheet content, empty string if not found.
        """

    def save_character(self, player_id: str, content: str) -> None:
        """
        Write character sheet Markdown.

        Args:
            player_id: Player identifier.
            content: Markdown content.
        """

    def load_npc(self, npc_id: str) -> str:
        """
        Load an NPC document as Markdown.

        Args:
            npc_id: NPC identifier.

        Returns:
            NPC content, empty string if not found.
        """

    def save_npc(self, npc_id: str, content: str) -> None:
        """
        Write NPC document Markdown.

        Args:
            npc_id: NPC identifier.
            content: Markdown content.
        """
```

---

### dungeonmaster.data.watcher

File system watcher for vault changes.

#### `VaultWatcher`

```python
class VaultWatcher:
    """
    Watch vault directories for changes.

    Monitors systems/, characters/, and npcs/ for file changes.
    Callbacks are synchronous; use asyncio.run_coroutine_threadsafe
    for async operations from callbacks.
    """

    def __init__(
        self,
        vault: Vault,
        on_system_change: Callable[[str], None] | None = None,
        on_character_or_npc_change: Callable[[str], None] | None = None,
    ) -> None:
        """
        Initialize the file watcher.

        Args:
            vault: Vault instance.
            on_system_change: Callback for system file changes (for re-ingesting RAG).
            on_character_or_npc_change: Callback for character/NPC changes.
        """

    def start(self) -> None:
        """Start watching vault directories."""

    def stop(self) -> None:
        """Stop the watcher and clean up."""
```

#### `VaultWatcherHandler`

```python
class VaultWatcherHandler(FileSystemEventHandler):
    """Internal handler that dispatches to appropriate callbacks."""
```

---

## Interfaces

### dungeonmaster.interfaces.discord

Discord bot interface for player interaction.

#### `DiscordBot`

```python
class DiscordBot(commands.Bot):
    """
    Discord interface for DungeonMaster.

    Handles DMs from players and provides slash commands.
    Forwards messages to engine.handle_message for processing.
    """

    def __init__(
        self,
        token: str,
        engine_handle_message: EngineHandleMessage,
        dm_only: bool = True,
        command_prefix: str = "!",
        intents: discord.Intents | None = None,
    ) -> None:
        """
        Initialize Discord bot.

        Args:
            token: Discord bot token.
            engine_handle_message: Async callback to process messages.
            dm_only: If True, only respond to direct messages.
            command_prefix: Prefix for text commands (default: "!").
            intents: Discord intents (auto-configured if None).
        """

    def run_bot(self) -> None:
        """Blocking run. Use start() for async."""
```

#### Slash Commands

| Command | Description | Task Type |
|---------|-------------|-----------|
| `/start` | Start or resume session | narrative |
| `/action <action>` | Describe character action | narrative |
| `/say <text>` | Character dialogue | narrative |
| `/status <question>` | Ask for ruling/situation | ruling |
| `/notes` | Get session notes summary | ruling |

#### Type Alias

```python
EngineHandleMessage = Callable[[str, str, str, str], Awaitable[str]]
# Signature: async (session_id, user_id, content, task_type) -> reply_text
```

---

## Configuration

### dungeonmaster.config

Configuration loading with secrets and environment variable support.

#### `load_config`

```python
def load_config(
    path: str | Path | None = None,
    secrets_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Load configuration from YAML with secrets and env var substitution.

    Resolution order for ${VAR} placeholders:
    1. secrets.json values
    2. Environment variables
    3. Keep original placeholder if not found

    Args:
        path: Path to YAML config. If None, checks DUNGEONMASTER_CONFIG env var,
              then config/default.yaml.
        secrets_path: Path to secrets.json. If None, looks in project root.

    Returns:
        Configuration dictionary with all placeholders resolved.
    """
```

#### Configuration Structure

See [CONFIGURATION.md](CONFIGURATION.md) for full details.

```yaml
vault:
  path: data

ai:
  ollama:
    base_url: http://localhost:11434
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

---

## See Also

- [Architecture Overview](ARCHITECTURE.md) — System design and message flow
- [Vault and State](VAULT_AND_STATE.md) — Data layout and JSON schemas
- [Configuration Reference](CONFIGURATION.md) — Full config options
- [Contributing Guide](../CONTRIBUTING.md) — Development guidelines
