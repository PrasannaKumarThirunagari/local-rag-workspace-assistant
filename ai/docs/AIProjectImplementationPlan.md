# Local RAG + ChromaDB + MCP AI Project — Implementation Plan

This document describes a concrete, end‑to‑end implementation plan for a **fully local, free** Retrieval‑Augmented Generation (RAG) system that:

- Ingests files from your machine.
- Indexes them into **ChromaDB** with rich metadata.
- Uses a **local LLM** for question‑answering.
- Minimizes hallucinations via good retrieval, grounding, and answer constraints.
- Uses **MCP tools** and **agents** to keep the system modular and scriptable.

---

## 1. High‑Level Architecture

### 1.1 Components

- **Ingestion & Indexer service (Python)**
  - Scans configured folders.
  - Parses and chunks documents.
  - Creates embeddings and writes to **ChromaDB**.
  - Handles incremental re‑indexing.

- **RAG / QA service (Python)**
  - Exposes a simple HTTP or MCP tool interface:
    - `/ask` (question → answer + citations).
    - `/search` (question → ranked snippets).
  - Talks to **ChromaDB** for retrieval.
  - Talks to a **local LLM runtime** (e.g., Ollama or llama.cpp server).

- **Local LLM runtime**
  - Example: **Ollama** with a mid‑size model such as:
    - `llama3:8b` or `mistral:7b` (general code/docs).
  - Runs on your GPU/CPU; no external calls.

- **ChromaDB**
  - Embedded (SQLite) or server mode.
  - One collection per “workspace” (e.g., `genzeon-project`).

- **MCP Server**
  - Wraps the RAG / QA and ingestion APIs as MCP tools:
    - `rag.search`, `rag.ask`, `rag.ingest`, `rag.reindex`.
  - Allows tools to be orchestrated by agents (Cursor, other MCP clients).

- **Client(s)**
  - Your existing **ASP.NET MVC file explorer** (if you choose to integrate).
  - Cursor / IDE agents via MCP.
  - Optional CLI.

### 1.2 Data Flow Overview

1. **Ingestion**
   - User selects or configures root folders.
   - Ingestion service walks the filesystem, applies type‑specific parsing.
   - Text is **chunked** with overlap and metadata.
   - Embeddings are computed and stored in ChromaDB.

2. **Query (RAG)**
   - User asks a question (via CLI, IDE, or MVC UI).
   - RAG service:
     - Embeds the query.
     - Issues a similarity (and optionally keyword) search against ChromaDB.
     - Builds a **context window** with top‑k passages.
     - Calls the local LLM with a strict, citation‑focused prompt.
     - Returns answer + citations (file path, line ranges).

3. **Feedback & Iteration**
   - Users inspect cited snippets.
   - If hallucinations occur, adjust:
     - Chunk size, retrieval parameters, LLM prompt, or max context.

---

## 2. Technology Choices

### 2.1 Core Stack (All Local & Free)

- **Language**: Python 3.11+
- **Vector DB**: [ChromaDB](https://docs.trychroma.com/)
- **LLM runtime**: [Ollama](https://ollama.com/) (simplest local setup)
  - Models: `llama3:8b` (default), optionally `mistral:7b` for comparison.
- **Embeddings**:
  - `nomic-embed-text` (locally via Ollama) or
  - `all-MiniLM-L6-v2` via `sentence-transformers`.
- **MCP server**:
  - Custom MCP server in Python using the official MCP protocol implementation.

### 2.2 Optional Libraries

- `langchain` or `llama-index` as orchestration layer for RAG (optional).
- `uvicorn` + `FastAPI` for a simple HTTP API surface.
- `watchdog` for filesystem watching (incremental re‑index).

---

## 3. Repository & Folder Structure

Example structure within a new `ai-rag-engine` folder (can live beside `AI_File_Explorer_MVC`):

```text
ai-rag-engine/
  README.md
  pyproject.toml / requirements.txt
  config/
    config.example.yaml
  src/
    ai_rag/
      __init__.py
      config.py
      models.py          # DTOs for documents, chunks, queries, answers
      ingestion/
        __init__.py
        file_scanner.py  # walks file tree
        parsers.py       # type-specific parsers
        chunker.py
        indexer.py       # writes to Chroma
      rag/
        __init__.py
        embeddings.py
        retriever.py
        prompts.py
        qa_service.py
      mcp_server/
        __init__.py
        server.py        # MCP tool definitions
  scripts/
    ingest_workspace.py
    ask_cli.py
```

You can keep your **ASP.NET MVC** app unchanged and later call the Python APIs or MCP tools from it if desired.

---

## 4. Data Model & Chunking Strategy

### 4.1 Document & Chunk Schema

- **Document metadata**
  - `id`: stable hash of path + mtime.
  - `path`: absolute or workspace‑relative path.
  - `type`: `code`, `markdown`, `text`, `config`, etc.
  - `language` / `extension`.
  - `modified_at`.

- **Chunk metadata**
  - `chunk_id`: unique stable id.
  - `document_id`.
  - `start_line`, `end_line`.
  - `heading` (for markdown) or `symbol` (for code, e.g., class/function name).
  - `tags`: e.g., `["controller", "view", "config"]`.

### 4.2 Chunking Rules

- **Code files**
  - Chunk by **function / class**, with:
    - Max ~512–768 tokens.
    - Overlap of 2–3 lines between chunks.
  - Use a lightweight parser (e.g., `tree-sitter` or regex/indentation heuristics).

- **Markdown / docs**
  - Chunk by **heading** plus paragraphs under it.
  - Fallback: sliding window of ~500 characters with 100–150 character overlap.

- **Plain text / config**
  - Line‑based chunks of 20–40 lines.

Rationale: semantic chunks anchored on logical boundaries reduce hallucination risk and improve citations.

---

## 5. Ingestion & Indexing Service

### 5.1 Configuration

Create `config/config.yaml` with:

- `workspaces`:
  - `name`: e.g., `genzeon-project`.
  - `root_paths`: list of folders to scan.
  - `include_globs`: `["**/*.cs", "**/*.cshtml", "**/*.md", "**/*.json"]`.
  - `exclude_globs`: `["**/bin/**", "**/obj/**", "**/.git/**"]`.
- `chroma`:
  - `persist_directory`: path on disk.
  - `collection_name`: `genzeon-project`.
- `embeddings`:
  - `provider`: `ollama|sentence-transformers`.

### 5.2 File Scanning

- Implement `file_scanner.py`:
  - Walk `root_paths`.
  - Apply include/exclude rules.
  - Yield file metadata.

### 5.3 Parsing & Chunking

- `parsers.py`:
  - `parse_file(path) -> ParsedDocument` with raw text and type.
  - Type detection: extension, simple heuristics (e.g., `.cshtml` → `razor`).

- `chunker.py`:
  - Functions like `chunk_code(doc)`, `chunk_markdown(doc)`, `chunk_text(doc)`.
  - Return list of `Chunk` objects, each with text + metadata.

### 5.4 Embedding & Indexing

- `embeddings.py`:
  - Abstraction: `embed_texts(list[str]) -> list[list[float]]`.
  - Implementation:
    - Ollama: HTTP POST to `http://localhost:11434/api/embeddings` with `model: "nomic-embed-text"` (or similar).

- `indexer.py`:
  - For each chunk:
    - Compute embedding.
    - Write to Chroma collection with metadata.
  - Support:
    - **Full rebuild**.
    - **Incremental update**: compare file `mtime` to last indexed time; re‑index changed files only.

---

## 6. Retrieval & RAG Service

### 6.1 Retrieval

- `retriever.py`:
  - `retrieve(query, k=8) -> list[Chunk]`:
    - Embed query.
    - Query Chroma with:
      - Cosine similarity.
      - Optional filtering by file type, path, tags.
    - Optionally implement **re-ranking**:
      - Re‑rank top‑k by lexical overlap with the query.

### 6.2 Prompting for Minimal Hallucination

- `prompts.py`:
  - System prompt template:

    - Instruct the model to:
      - Only answer using provided context.
      - Cite file paths and line ranges.
      - Say “I don’t know” when context is insufficient.

- Example pseudo‑prompt:

> You are a helpful assistant that answers questions **only** using the provided context.
> If the answer is not contained in the context, say:
> "I don’t know based on the indexed documents."
> Always include a "Sources:" section listing `path:line_start-line_end` for the snippets you used.

### 6.3 QA Service

- `qa_service.py`:
  - `answer_question(question, workspace) -> { answer, snippets }`
  - Steps:
    1. Call `retriever.retrieve(question)`.
    2. Build a context string with:
       - Snippets labeled with `path`, `start_line`, `end_line`.
    3. Call local LLM (Ollama `/api/generate`) with system + user prompt.
    4. Return:
       - `answer` (LLM text).
       - `snippets` (metadata from retrieval) for UI citation.

---

## 7. MCP Server & Tools

### 7.1 Tools to Expose

Implement a Python MCP server with tools like:

- `rag.ingest`:
  - Args: `workspaceName`, optional `paths`.
  - Runs full or incremental indexing.

- `rag.search`:
  - Args: `workspaceName`, `query`, `topK`.
  - Returns raw retrieved snippets (no generation).

- `rag.ask`:
  - Args: `workspaceName`, `question`.
  - Returns structured answer + citations.

### 7.2 Agent Patterns

- **Retriever agent**:
  - Uses `rag.search` to get context for other tools.

- **Explainer / summarizer agent**:
  - Uses `rag.ask` to summarize or explain code/files.

Integrate these into Cursor or other MCP‑aware clients so that:

- The IDE can ask, “Explain this file” or “Where is X configured?” using your local RAG engine rather than internet.

---

## 8. ASP.NET MVC Integration (Optional)

If you want your existing **file explorer UI** to use this RAG stack:

1. Run the Python RAG service as an HTTP server on `localhost`.
2. In your ASP.NET app:
   - Add an API client (`HttpClient`) to call:
     - `GET /search?q=...` → show results in the middle pane.
     - `POST /ask` with `question` + current folder/file → show RAG answer and citations in a panel or popover.
3. Wire the **“Summarize with AI”** button to:
   - Send the current file path + optional question (e.g., “Summarize this file”) to the RAG service.
   - Display the result alongside the file viewer.

---

## 9. End‑to‑End Setup Steps

1. **Environment**
   - Install Python 3.11+.
   - Install Ollama and pull at least one model (`ollama pull llama3:8b`).
   - Create a virtualenv and install project dependencies.

2. **ChromaDB setup**
   - Decide on embedded vs server mode; start Chroma if using server.
   - Configure `persist_directory` and `collection_name`.

3. **Implement ingestion**
   - Build `file_scanner.py`, `parsers.py`, `chunker.py`, `embeddings.py`, `indexer.py`.
   - Test `scripts/ingest_workspace.py` on a small folder.

4. **Implement retrieval & QA**
   - Build `retriever.py`, `prompts.py`, `qa_service.py`.
   - Test `scripts/ask_cli.py "How is X configured?"`.

5. **Implement MCP server**
   - Implement tools `rag.ingest`, `rag.search`, `rag.ask`.
   - Register the MCP server in your MCP client (e.g., Cursor).

6. **Integrate with UI (optional)**
   - Add minimal HTTP endpoints in the ASP.NET app that proxy queries to the Python RAG service or call it directly.
   - Wire search and “Summarize with AI” to those endpoints.

7. **Testing & Hardening**
   - Create a **test corpus** with known answers.
   - Measure:
     - Recall@k (are the right snippets retrieved?).
     - Hallucination rate (answers not grounded in any cited snippet).
   - Adjust:
     - Chunk sizes, retrieval `k`, prompt strictness.

---

## 10. Next Steps

With this plan in place, the next concrete move is to:

1. Create the `ai-rag-engine` Python project with the outlined structure.
2. Implement ingestion and indexing for a small subset of your workspace.
3. Implement `rag.ask` and verify grounded answers on a few real questions.
4. Once stable, integrate with your ASP.NET MVC explorer and Cursor via MCP.

This keeps everything local, free, and extensible while giving you a robust, low‑hallucination RAG engine tailored to your own files and workflows.

