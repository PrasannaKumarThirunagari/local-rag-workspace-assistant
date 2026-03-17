## Overview

This repository implements a **local file‑aware workspace assistant** composed of:

- An **ASP.NET Core MVC web app** that provides a 3‑pane file explorer UI and an “Summarize with AI” experience.
- A **Python RAG engine** that ingests selected folders, indexes them in **ChromaDB**, and answers questions using a **local LLM via Ollama**.
- An optional **MCP server** surface so tools/agents (e.g. Cursor) can call the RAG engine as standard MCP tools.

All components are designed to run fully locally on your machine (no external cloud dependencies), using Ollama for model hosting and an embedded ChromaDB for vector storage.

---

## Components and Responsibilities

### 1. ASP.NET Core MVC Application (`WebAppMvc`)

**Purpose:** Rich file explorer UI for the solution, integrating AI summarization of individual files without full page reloads.

- **UI Layout**
  - 3‑pane explorer implemented in `Views/Home/Index.cshtml`:
    - **Left (Folders, ~30%)**: Tree view of directories rooted at the solution directory.
    - **Middle (Files, ~30%)**: File list for the selected folder.
    - **Right (Viewer, ~40%)**: Read‑only preview of the selected file plus the AI summary panel.
  - Tailwind‑style utility classes (compiled by the template) give a modern, light theme.
  - Client‑side behavior implemented using **vanilla JavaScript** in the same view:
    - Folder expand/collapse and selection.
    - File selection and content loading.
    - Search box that filters folders, files, and in‑viewer content with debounced AJAX search to the MVC backend.
    - Session‑based persistence of scroll positions and expanded folders (`sessionStorage`).

- **Controllers**
  - `HomeController`:
    - `Index` – populates the root folder tree, file list, and initial file content using the file system service.
    - `Search` (GET `/Home/Search`) – server‑side search over file contents and returns matching folders/files as JSON. The client JS renders search results in both folder and file panes.
    - `FolderData` (GET `/Home/FolderData`) – returns the file list for a specific folder (JSON), used by AJAX when clicking folders.
    - `FileContent` (GET `/Home/FileContent`) – returns file name + contents for the selected file (JSON), used to update the viewer.
    - `AskRag` (POST `/Home/AskRag`) – calls the Python RAG HTTP API via `IRagService` and returns `{ success, answer }` JSON for the “Summarize with AI” button.

- **Services**
  - `IFileSystemService` / `FileSystemService`:
    - Enumerates the folder tree from the solution root (with configurable max depth).
    - Returns file lists per folder.
    - Loads file contents for the viewer.
    - Provides text search across files for the `Search` endpoint.
  - `IRagService` / `RagService`:
    - Typed wrapper over `HttpClient` that calls the Python RAG API.
    - Reads `Rag:BaseUrl` from `appsettings.json` (default `http://localhost:8000`).
    - `AskAsync(question, pathFilter, topK)` → POST `/api/ask` on the Python API and returns the answer text or `null` on failure.

- **Client‑Side AI Integration**
  - The “Summarize with AI” button in `Index.cshtml`:
    - Reads the currently selected file path from `sessionStorage` (`explorer.viewer.filePath`).
    - Constructs a natural language question like “Summarize X.cs concisely. What does it do?”
    - Sends a `FormData` POST to `/Home/AskRag` with `question` and optional `filePath`.
    - Shows a sticky **AI Summary** panel with streaming states:
      - “Asking AI…” while waiting.
      - Either the returned answer or an error message if the RAG service is unavailable.

**Communication:**  
MVC ↔ RAG API via HTTP calls from `RagService` to `http://localhost:8000/api/ask` (and, if desired later, `/api/search`).

---

### 2. Python RAG Engine (`ai/rag-engine`)

**Purpose:** Ingest selected workspace folders, build a semantic index in ChromaDB, and power question‑answering and semantic search for both the MVC app and MCP tools.

#### 2.1 Structure

- `config/config.yaml`
  - Defines one or more **workspaces**; currently `file-explorer`:
    - `root_paths`: which folders to scan (e.g. `C:/Genzeon Project/GIT REPO`).
    - `include_globs`: file patterns to include (`**/*.cs`, `**/*.cshtml`, `**/*.md`, `**/*.json`).
    - `exclude_globs`: patterns to skip (`**/bin/**`, `**/obj/**`, `**/.git/**`, `**/.vs/**`).
  - `chroma`: persist directory (e.g. `C:/Genzeon Project/ai/chroma`) and collection name (`file-explorer`).
  - `embeddings`: provider (`sentence-transformers` or `ollama`), model name (`all-MiniLM-L6-v2` by default).
  - `llm`: Ollama model name (`llama3.2:3b`) and base URL (`http://localhost:11434`) for RAG answers.

- `src/ai_rag/config.py`
  - Maps the YAML config into strongly typed dataclasses (`WorkspaceConfig`, `ChromaConfig`, `EmbeddingsConfig`, `LLMConfig`, `AppConfig`).  
  - Responsible for loading and normalizing paths.

- `src/ai_rag/models.py`
  - `DocumentMetadata`, `Document`, `Chunk`, `Query`, `RetrievedChunk`, `Answer` dataclasses.  
  - Chunks carry path, start/end lines, heading/symbol metadata for later citation.

#### 2.2 Ingestion Pipeline (`src/ai_rag/ingestion`)

- **`file_scanner.py`**
  - Walks configured `root_paths` and yields `ScannedFile` records:
    - `path`, `relative_path`, `mtime`.
  - Applies `include_globs`/`exclude_globs` to decide which files to index.

- **`parsers.py`**
  - Reads files and infers document type by extension.
  - Produces `Document` objects with stable IDs based on path + mtime.

- **`chunker.py`**
  - Converts each `Document` into multiple `Chunk` objects:
    - **Code**: class/method‑aware chunking with size and overlap constraints.
    - **Markdown**: heading‑based chunks, with fallback sliding windows.
    - **Text/config**: fixed line‑based windows.
  - Each chunk is tagged with `start_line`, `end_line`, `heading` or `symbol`, and `path`.

- **`rag/embeddings.py`**
  - Embedding provider abstraction:
    - `OllamaEmbeddings` – calls Ollama `/api/embeddings` if configured.
    - `SentenceTransformerEmbeddings` – uses `sentence-transformers` (`all-MiniLM-L6-v2` by default).

- **`ingestion/indexer.py`**
  - Orchestrates full ingestion for a workspace:
    1. Creates a `chromadb.PersistentClient` at `persist_directory`.
    2. Gets or creates the Chroma collection for this workspace.
    3. **Full rebuild**: deletes existing items from the collection in safe batches, avoiding Chroma’s delete batch size limits.
    4. For each scanned file:
       - Parses into a `Document`.
       - Chunks into `Chunk`s.
       - Embeds batches of chunk texts via the configured embedding provider.
       - Adds `(id, document, embedding, metadata)` records to Chroma.
  - Returns simple statistics: number of files and chunks indexed.

- **Scripts**
  - `scripts/ingest_workspace.py` – CLI entry point:
    - `--workspace file-explorer` – run full ingestion for that workspace.
    - `--dry-run` – print config details without indexing.

#### 2.3 Retrieval and QA (`src/ai_rag/rag`)

- **`retriever.py`**
  - Given an `AppConfig` and a query string:
    - Embeds the query.
    - Issues a Chroma `query` against the workspace collection, with optional `path_filter` for file‑scoped questions.
    - Returns ranked `RetrievedChunk` objects (cosine similarity → score).

- **`prompts.py`**
  - System and user prompt templates designed to minimize hallucination:
    - Model is instructed to **only** answer from provided context.
    - Required to cite sources (`path:start_line-end_line`).
    - Encouraged to say “I don’t know based on the indexed documents” if context is insufficient.
  - Helper functions to format context snippets for the LLM.

- **`qa_service.py`**
  - `answer_question(app_config, question, top_k, path_filter)`:
    - Uses `retriever.retrieve` to get top‑k relevant chunks.
    - Formats them into a prompt with citations.
    - Calls Ollama `/api/generate` with the configured model.
    - Returns a structured `Answer` (question, text, and snippets).

- **Scripts**
  - `scripts/ask_cli.py` – command‑line helper to test RAG:
    - Example: `python scripts/ask_cli.py "Where is HomeController defined?"`.

---

### 3. Python HTTP API (`src/ai_rag/api/app.py`, `scripts/run_api.py`)

**Purpose:** Provide a simple JSON HTTP interface for the MVC app (and other clients) without exposing the internal RAG implementation.

- Built with **FastAPI** and **Uvicorn**.
- CORS enabled for local usage.
- Configuration path resolved to `rag-engine/config/config.yaml`.

**Endpoints:**

- `GET /health`  
  - Basic health probe: returns `{"status": "ok"}`.

- `POST /api/search`  
  Request body (`SearchRequest`):

  ```json
  { "q": "HomeController", "top_k": 8 }
  ```

  Response (`SearchResponse`):

  ```json
  {
    "snippets": [
      {
        "path": "C:/Genzeon Project/GIT REPO/.../HomeController.cs",
        "start_line": 10,
        "end_line": 40,
        "text": "partial code snippet...",
        "score": 0.87
      }
    ]
  }
  ```

- `POST /api/ask`  
  Request body (`AskRequest`):

  ```json
  {
    "question": "Summarize HomeController.cs. What does it do?",
    "top_k": 8,
    "path_filter": "C:/Genzeon Project/GIT REPO/.../HomeController.cs"
  }
  ```

  Response (`AskResponse`):

  ```json
  {
    "question": "...",
    "answer": "High-level technical summary with citations."
  }
  ```

- `scripts/run_api.py` – convenience script:

  ```bash
  python scripts/run_api.py
  # Runs on http://localhost:8000
  ```

**Communication:**  
MVC’s `RagService` calls `/api/ask`; other clients can use `/api/search` for pure retrieval use cases.

---

### 4. MCP Server (`src/ai_rag/mcp_server/server.py`)

**Purpose:** Expose the RAG engine as MCP tools so MCP‑capable clients (e.g. Cursor) can call it as a standard toolset.

- Built using the **MCP Python SDK** (`mcp.server.fastmcp.FastMCP`).
- Tools:
  - `rag_search(workspace_name, query, top_k)` – mirrors the `/api/search` behavior.
  - `rag_ask(workspace_name, question, top_k)` – mirrors the `/api/ask` behavior.
  - `rag_ingest(workspace_name)` – triggers ingestion for a workspace.

- `scripts/run_mcp_server.py` – runs the MCP server over stdio for IDE integration.

**Communication:**  
MCP client ↔ MCP server via stdio transport. MCP server internally uses the same ingestion/retrieval/QA services as the HTTP API.

---

## End‑to‑End Flow

1. **Ingestion**
   - You run:

     ```bash
     cd ai/rag-engine
     .venv\Scripts\python scripts\ingest_workspace.py --workspace file-explorer
     ```

   - The Python ingestion pipeline scans configured `root_paths` (e.g. `GIT REPO`), parses and chunks files, embeds chunks, and writes vectors + metadata into ChromaDB at `ai/chroma`.

2. **API Startup**
   - You start the HTTP API:

     ```bash
     .venv\Scripts\python scripts\run_api.py
     ```

   - FastAPI + Uvicorn bind to `http://0.0.0.0:8000` and serve `/health`, `/api/search`, `/api/ask`.

3. **User Interaction in MVC UI**
   - User navigates the folder tree and selects a file.
   - MVC app loads file contents via `/Home/FileContent` and displays them.
   - When the user clicks **Summarize with AI**:
     - Browser posts `question` + `filePath` to `/Home/AskRag`.
     - `HomeController.AskRag` calls `IRagService.AskAsync`, which calls the Python API `/api/ask`.

4. **RAG Answer Generation**
   - Python API’s `/api/ask`:
     - Loads config and connects to ChromaDB.
     - Uses `retriever.retrieve` with optional `path_filter` to get top‑k relevant chunks.
     - Formats context with citations and calls Ollama LLM.
     - Returns an answer string to the MVC app.
   - MVC app’s JS fills the **AI Summary** panel with the answer and any error message if applicable.

---

## Operational Notes

- **Persistence:**  
  ChromaDB data under `ai/chroma` is persistent across restarts; stopping the API or MVC app does not delete the index.

- **Performance considerations:**  
  The first call that uses embeddings or the LLM can be slower due to model loading. Subsequent calls are much faster.

- **Scoping:**  
  By adjusting `root_paths`, `include_globs`, and `exclude_globs` in `config.yaml`, you control exactly which files and subfolders are visible to the RAG engine (e.g. only `GIT REPO` and its descendants).

