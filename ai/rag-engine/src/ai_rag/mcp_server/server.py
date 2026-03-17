"""MCP server exposing RAG tools: rag.search, rag.ask, rag.ingest."""
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ai-rag",
    json_response=True,
)

# Project root is 3 levels up from this file
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "config.yaml"


def _load_config():
    from ai_rag.config import load_config
    return load_config(_CONFIG_PATH)


def _get_workspace(name: str):
    cfg = _load_config()
    ws = next((w for w in cfg.workspaces if w.name == name), None)
    if not ws:
        raise ValueError(f"Workspace '{name}' not found. Available: {[w.name for w in cfg.workspaces]}")
    return cfg, ws


@mcp.tool()
def rag_search(
    workspace_name: str = "file-explorer",
    query: str = "",
    top_k: int = 8,
) -> str:
    """Search the indexed workspace for relevant snippets. Returns retrieved chunks with paths and scores."""
    if not query.strip():
        return "Please provide a non-empty query."
    from ai_rag.rag.retriever import retrieve
    app_config, _ = _get_workspace(workspace_name)
    results = retrieve(app_config, query=query, top_k=top_k)
    if not results:
        return "No snippets found. Run rag.ingest first."
    lines = []
    for i, rc in enumerate(results, 1):
        path = rc.chunk.path or "unknown"
        sl, el = rc.chunk.start_line or 0, rc.chunk.end_line or 0
        lines.append(f"[{i}] {path}:{sl}-{el} (score={rc.score:.3f})\n{rc.chunk.text[:500]}...")
    return "\n\n---\n\n".join(lines)


@mcp.tool()
def rag_ask(
    workspace_name: str = "file-explorer",
    question: str = "",
    top_k: int = 8,
) -> str:
    """Ask a question; returns an LLM-generated answer with citations. Requires Ollama running."""
    if not question.strip():
        return "Please provide a non-empty question."
    from ai_rag.rag.qa_service import answer_question
    app_config, _ = _get_workspace(workspace_name)
    answer = answer_question(app_config, question=question, top_k=top_k)
    return answer.text


@mcp.tool()
def rag_ingest(
    workspace_name: str = "file-explorer",
) -> str:
    """Ingest the workspace: scan, chunk, embed, and index into ChromaDB."""
    from ai_rag.ingestion import index_workspace
    app_config, ws = _get_workspace(workspace_name)
    stats = index_workspace(app_config, ws)
    return f"Ingestion complete. Files: {stats['files']}, Chunks: {stats['chunks']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
