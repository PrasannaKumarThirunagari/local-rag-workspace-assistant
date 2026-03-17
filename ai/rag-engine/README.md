# local-rag-workspace-assistant – RAG Engine

Python backend for a local RAG engine: ingest workspace files, index into ChromaDB, search, and ask questions with citations.

## Layout

- `src/ai_rag/`
  - `config.py` – load YAML config (workspaces, chroma, embeddings, llm).
  - `models.py` – dataclasses for documents, chunks, answers.
  - `ingestion/` – file scanner, parsers, chunker, indexer.
  - `rag/` – embeddings, retriever, prompts, QA service.
  - `mcp_server/` – MCP tools: `rag.search`, `rag.ask`, `rag.ingest`.
- `scripts/`
  - `ingest_workspace.py` – index workspace.
  - `ask_cli.py` – ask questions via RAG.
  - `run_mcp_server.py` – run MCP server (stdio).
  - `run_api.py` – run HTTP API (port 8000) for MVC integration.

## Setup

```bash
cd ai/rag-engine
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -e .
```

## Config

Edit `config/config.yaml`:
- `workspaces` – root paths, include/exclude globs.
- `chroma` – persist path, collection name.
- `embeddings` – `ollama` (nomic-embed-text) or `sentence-transformers` (all-MiniLM-L6-v2).
- `llm` – Ollama model and URL for `rag.ask`.

## Ingestion

```bash
python scripts/ingest_workspace.py --workspace file-explorer
python scripts/ingest_workspace.py --workspace file-explorer --dry-run  # config only
```

## HTTP API (for MVC integration)

```bash
python scripts/run_api.py
```

Endpoints:
- `POST /api/ask` – `{ "question": "...", "path_filter": "...", "top_k": 8 }`
- `POST /api/search` – `{ "q": "...", "top_k": 8 }`
- `GET /health` – health check

The MVC app calls this API when you click "Summarize with AI". Set `Rag:BaseUrl` in `appsettings.json` if needed.

## Search (no LLM)

```bash
python scripts/ask_cli.py "Where is HomeController defined?"
```

Requires Ollama for full answers. If Ollama is not running, you’ll get a connection error, but `rag.search` (snippets only) still works.

## MCP Server

Run with stdio for Cursor/IDE integration:

```bash
python scripts/run_mcp_server.py
```

Or as a module:

```bash
python -m ai_rag.mcp_server.server
```

Add to your MCP config (e.g. Cursor):

```json
{
  "mcpServers": {
    "ai-rag": {
      "command": "path/to/.venv/Scripts/python",
      "args": ["path/to/scripts/run_mcp_server.py"]
    }
  }
}
```

Tools: `rag_search`, `rag_ask`, `rag_ingest`.
