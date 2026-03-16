Act as an expert AI engineer and solution architect.

I want to design and implement a **fully local, free AI project** with the following capabilities:

1. **Local document ingestion**
   - Select and ingest files from my local system (code, markdown, text, docs, etc.).
   - Parse and chunk these documents in a way that is optimal for retrieval (semantic chunks, not arbitrary splits).
   - Store all vector embeddings in **ChromaDB** running locally (no external services).

2. **Retrieval-Augmented Generation (RAG)**
   - Use a **local, open-source LLM** (no paid SaaS APIs) to answer questions about the ingested files.
   - Implement high-quality RAG:
     - Good chunking and metadata (file path, line ranges, timestamps).
     - Hybrid search if possible (semantic + keyword).
     - Re-ranking or scoring to reduce irrelevant context.
   - Focus strongly on **minimizing hallucinations** by:
     - Restricting answers to retrieved context.
     - Citing source files and line ranges.
     - Returning "I don’t know / not in documents" when confidence is low.

3. **Search and UX**
   - Provide a simple but powerful UI or CLI to:
     - Search across documents (by content and metadata).
     - Ask natural-language questions and get grounded answers.
     - Show which files/snippets were used to answer.
   - Reuse the existing workspace-explorer UX ideas where helpful (folders, files, viewer).

4. **Architecture and tooling**
   - Use **MCP (Model Context Protocol)** and **Agents** where appropriate to:
     - Orchestrate tools (file access, ChromaDB operations, search).
     - Structure the system into clear roles (e.g., retriever agent, router agent, summarizer agent).
   - Keep everything **local and free**:
     - Propose specific local LLMs, embedding models, and runtimes (e.g., GGUF + llama.cpp/ollama or similar).
     - Explain hardware considerations and trade-offs.

5. **Robustness and maintainability**
   - Handle incremental updates when files change (re-indexing strategies).
   - Discuss how to test RAG quality and guard against hallucinations.
   - Consider performance for medium-sized codebases and document sets.

Your task:
- Propose the **best feasible and accurate overall solution/architecture** for this project using RAG, ChromaDB, MCP, and local agents.
- Then, based on that solution, **create a new markdown file in the same folder** (you choose a clear filename) that contains a **detailed, step-by-step implementation plan**, including:
  - Tech stack and tools (with specific model suggestions).
  - System architecture diagram (described in text; I can convert to visuals later).
  - Data flow: ingestion → indexing → retrieval → answer generation.
  - Folder structure and key modules/classes.
  - How MCP tools and agents are defined and interact.
  - How to run and test the system end-to-end.

Write the plan so that a senior engineer can follow it directly to implement the project.
