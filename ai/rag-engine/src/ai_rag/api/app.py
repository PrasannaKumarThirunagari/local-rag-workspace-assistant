"""FastAPI HTTP API for RAG: /api/search and /api/ask."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Config path: project root (rag-engine/config/config.yaml)
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "config.yaml"

app = FastAPI(title="AI RAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    q: str = ""
    top_k: int = 8
    workspace: str = "file-explorer"


class SearchResponse(BaseModel):
    snippets: list[dict]


class AskRequest(BaseModel):
    question: str = ""
    top_k: int = 8
    path_filter: str | None = None
    workspace: str = "file-explorer"


class AskResponse(BaseModel):
    answer: str
    question: str


def _load_and_search(q: str, top_k: int, path_filter: str | None):
    from ai_rag.config import load_config
    from ai_rag.rag.retriever import retrieve

    cfg = load_config(_CONFIG_PATH)
    results = retrieve(cfg, query=q, top_k=top_k, path_filter=path_filter)
    return [
        {
            "path": rc.chunk.path,
            "start_line": rc.chunk.start_line,
            "end_line": rc.chunk.end_line,
            "text": rc.chunk.text[:500],
            "score": rc.score,
        }
        for rc in results
    ]


def _load_and_ask(question: str, top_k: int, path_filter: str | None):
    from ai_rag.config import load_config
    from ai_rag.rag.qa_service import answer_question

    cfg = load_config(_CONFIG_PATH)
    answer = answer_question(cfg, question=question, top_k=top_k, path_filter=path_filter)
    return answer.text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def api_search(req: SearchRequest):
    q = (req.q or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query is required")
    snippets = _load_and_search(q, top_k=req.top_k, path_filter=None)
    return SearchResponse(snippets=snippets)


@app.post("/api/ask", response_model=AskResponse)
def api_ask(req: AskRequest):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    answer = _load_and_ask(question, top_k=req.top_k, path_filter=req.path_filter)
    return AskResponse(question=question, answer=answer)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
