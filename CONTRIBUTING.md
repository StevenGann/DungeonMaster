# Contributing to DungeonMaster

Thank you for your interest in contributing to DungeonMaster! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/DungeonMaster.git
   cd DungeonMaster
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/StevenGann/DungeonMaster.git
   ```

## Development Environment

### Prerequisites

- **Python 3.10–3.12** (3.14 not yet supported due to ChromaDB/pydantic compatibility)
- **Ollama** (optional, for local models) — [https://ollama.ai](https://ollama.ai)
- **Git** for version control

### Setup

1. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

2. **Install the package in development mode** with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Configure secrets** for local development:
   - Copy `secrets.example.json` to `secrets.json`
   - Fill in your API keys (Discord bot token, Anthropic API key)
   - Alternatively, set environment variables: `DISCORD_BOT_TOKEN`, `ANTHROPIC_API_KEY`

4. **Verify the installation**:
   ```bash
   python -c "import dungeonmaster; print(dungeonmaster.__version__)"
   ```

### IDE Setup

We recommend VS Code with the following extensions:
- **Python** (Microsoft)
- **Ruff** (for linting/formatting)
- **Python Docstring Generator** (for consistent docstrings)

## Project Structure

```
DungeonMaster/
├── config/                 # Configuration files
│   └── default.yaml        # Default YAML configuration
├── data/                   # Vault root (Obsidian-compatible)
│   ├── systems/            # Rulebooks (Markdown/TXT)
│   ├── notes/              # Session notes
│   ├── characters/         # Player character sheets
│   ├── npcs/               # NPC documents
│   ├── state/              # Scene state (JSON)
│   └── _index/             # ChromaDB (internal)
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md     # System architecture
│   ├── VAULT_AND_STATE.md  # Data layout and schemas
│   └── README.md           # Documentation index
├── docker/                 # Docker configuration
├── src/dungeonmaster/      # Source code
│   ├── ai/                 # AI providers, orchestrator, RAG
│   ├── core/               # Engine, session, note-taking
│   ├── data/               # Vault, state, file watcher
│   └── interfaces/         # Discord bot (and future UIs)
├── tests/                  # Test suite
├── pyproject.toml          # Project metadata and dependencies
└── requirements.txt        # Legacy requirements file
```

### Module Overview

| Module | Purpose |
|--------|---------|
| `dungeonmaster.ai` | AI providers (Ollama, Claude), orchestrator (task routing), RAG store |
| `dungeonmaster.core` | Engine (message handling), session management, note-taking |
| `dungeonmaster.data` | Vault (file I/O), state store (scene/characters), file watcher |
| `dungeonmaster.interfaces` | User interfaces (Discord bot) |
| `dungeonmaster.config` | Configuration loading (YAML + env vars + secrets) |
| `dungeonmaster.main` | Application entrypoint |

## Coding Standards

### Style Guide

- Follow **PEP 8** for Python code style
- Use **type hints** for all function signatures
- Maximum line length: **100 characters** (enforced by Ruff)
- Use **double quotes** for strings (project convention)

### Linting and Formatting

We use **Ruff** for linting and formatting:

```bash
# Check for issues
ruff check src tests

# Auto-fix issues
ruff check --fix src tests

# Check formatting
ruff format --check src tests

# Auto-format
ruff format src tests
```

All code must pass linting before being merged.

### Docstrings

All public modules, classes, and functions must have docstrings:

```python
def calculate_damage(base: int, modifier: float) -> int:
    """
    Calculate total damage with modifiers.

    Args:
        base: Base damage value before modifiers.
        modifier: Multiplier to apply to base damage.

    Returns:
        Final damage value (minimum 0).

    Raises:
        ValueError: If base damage is negative.
    """
    if base < 0:
        raise ValueError("Base damage cannot be negative")
    return max(0, int(base * modifier))
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `SessionManager`, `RAGStore`)
- **Functions/methods**: `snake_case` (e.g., `handle_message`, `load_scene`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CHUNK_SIZE`)
- **Private members**: Prefix with underscore (e.g., `_client`, `_sessions`)

### Async/Await

- Use `async def` for I/O-bound operations (network, file I/O)
- Prefer `asyncio` over threading for concurrency
- Exception: File watcher uses threads with `run_coroutine_threadsafe` for cross-thread async scheduling

## Testing

### Running Tests

```bash
# Run all tests
pytest tests -v

# Run with coverage
pytest tests --cov=src/dungeonmaster --cov-report=term-missing

# Run specific test file
pytest tests/test_engine.py -v

# Run tests matching a pattern
pytest tests -v -k "session"
```

### Windows Notes

On Windows, RAG tests may hang due to pytest-timeout's thread method. To skip RAG tests:

```bash
pytest tests -v --ignore=tests/test_rag.py
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_<module>.py`
- Use `pytest` fixtures from `conftest.py`
- Use `pytest-asyncio` for async tests (already configured)

Example test:

```python
import pytest
from dungeonmaster.core.session import Session, SessionManager


class TestSession:
    def test_add_turn(self):
        session = Session(session_id="test-1")
        session.add_turn("user", "Hello")
        assert len(session.turns) == 1
        assert session.turns[0].role == "user"
        assert session.turns[0].content == "Hello"

    def test_to_messages_limits(self):
        session = Session(session_id="test-2")
        for i in range(30):
            session.add_turn("user", f"Message {i}")
        messages = session.to_messages(max_turns=10)
        assert len(messages) == 10
```

### Test Coverage

We aim for **80%+ test coverage**. Check coverage reports and add tests for uncovered code paths when contributing new features.

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** following the coding standards

4. **Run tests and linting**:
   ```bash
   pytest tests -v
   ruff check src tests
   ruff format --check src tests
   ```

5. **Commit with a clear message**:
   ```bash
   git commit -m "Add feature: brief description of changes"
   ```

### Submitting

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request** on GitHub against the `main` branch

3. **Fill out the PR template** with:
   - Description of changes
   - Related issue numbers (if any)
   - Testing performed
   - Screenshots (if UI changes)

### Review Process

- All PRs require at least one approving review
- CI must pass (tests, linting, Docker build)
- Respond to feedback promptly and make requested changes
- Squash commits if requested before merging

## Reporting Issues

### Bug Reports

When reporting a bug, include:

1. **Environment**: Python version, OS, relevant package versions
2. **Steps to reproduce**: Clear, minimal steps to trigger the bug
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Error messages**: Full stack traces if available
6. **Configuration**: Relevant config (redact secrets!)

### Feature Requests

For feature requests, include:

1. **Use case**: Why is this feature needed?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches you've thought of
4. **Additional context**: Mockups, examples, references

---

Thank you for contributing to DungeonMaster! Your efforts help make this project better for everyone.
