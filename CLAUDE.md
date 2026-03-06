# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vault RAG is an MCP-compliant server that indexes, searches, and serves documents from Obsidian vaults, Joplin notebooks, and plain Markdown folders using semantic search (RAG) with ChromaDB and LlamaIndex. Version 0.5.0.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv sync              # production deps
uv sync --extra dev  # dev deps (pytest, black, ruff, mypy, bandit)

# Run server
vault-rag                          # both API + MCP servers
vault-rag --serve-api              # API only (port 8000)
vault-rag --serve-mcp              # MCP only (port 8081)
vault-rag --serve-mcp-stdio        # MCP over stdio

# Tests
pytest                             # all tests with coverage
pytest tests/test_config.py        # single test file
pytest -k "test_search"            # tests matching pattern
pytest -x --tb=short               # stop on first failure

# Code quality
black components/ shared/ vault_rag/
ruff check --fix components/ shared/ vault_rag/
mypy components/ shared/ vault_rag/
bandit -c pyproject.toml -r components/ shared/ vault_rag/
```

Pre-commit hooks run black, ruff, mypy, and bandit automatically.

## Architecture

**Entry point**: `vault_rag/main.py` — `run()` is the CLI script (`vault-rag` command).

**Initialization flow**: `shared/initializer.py` loads config, creates `VectorStore`, `QueryEngine`, and `VaultService`, then starts background indexing in a daemon thread.

**Core service**: `components/vault_service/main.py` (`VaultService`) is the central business logic hub. All server interfaces delegate to it. It handles querying, document retrieval, file listing, and re-indexing with Merkle-tree-based change detection (`shared/state_tracker.py`).

**Two server interfaces share one `VaultService`**:
- `components/api_app/` — FastAPI REST API (GET /files, GET /document, POST /query, POST /reindex)
- `components/mcp_app/` — MCP wrapper using `fastapi-mcp`, exposes same endpoints as MCP tools

**Component layer** (each in `components/` with own `tests/` subdir):
- `document_processing/` — Document loading (Standard/Obsidian/Joplin), two-stage node parsing (MarkdownNodeParser then SentenceSplitter), quality scoring, metadata extraction (folder, tags, fm_* fields)
- `vector_store/` — ChromaDB wrapper with pluggable embeddings, metadata filtering ($eq, $ne, $in, $nin, folder_prefix)
- `embedding_system/` — Factory for embedding providers: sentence_transformers, mlx_embeddings, openai_endpoint (with optional custom wrapper plugins)
- `agentic_retriever/` — LlamaIndex query engine; "agentic" mode uses LLM rewriting, "static" mode does fast deterministic context expansion
- `file_watcher/` — Watchdog-based live file monitoring with debouncing

**Shared utilities**: `shared/config.py` (Pydantic models for TOML config), `shared/initializer.py`, `shared/state_tracker.py` (Merkle tree for incremental indexing).

## Configuration

- `config/app.toml` — main config (paths, embedding model, retrieval mode, indexing params, prefix/glob filters)
- `config/prompts.toml` — LLM prompts for agentic mode
- Config is Pydantic-validated: see `shared/config.py` for all fields and defaults
- Two retrieval modes: `static` (no LLM needed, fast) and `agentic` (requires `[generation_model]` section)

## Code Style

- Python 3.11+, black (88 chars), ruff (E/F/W/B/SIM/I rules), mypy (strict on non-test code)
- Conventional commits: `feat(scope):`, `fix(scope):`, `docs:`, `test:`, `refactor:`
- Tests use pytest with pytest-asyncio, pyfakefs; coverage configured for `vault_rag/` and `components/`
- Test paths: `tests/` (root-level/integration) and `components/*/tests/` (unit tests per component)
