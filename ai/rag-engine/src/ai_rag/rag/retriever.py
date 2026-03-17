"""Retrieve relevant chunks from ChromaDB."""
from pathlib import Path

import chromadb
from chromadb.config import Settings

from ai_rag.config import AppConfig
from ai_rag.models import Chunk, DocumentMetadata, RetrievedChunk
from ai_rag.rag.embeddings import create_embedding_provider


def retrieve(
    app_config: AppConfig,
    query: str,
    top_k: int = 8,
    path_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Embed the query, search ChromaDB by cosine similarity, return ranked chunks.
    """
    embedder = create_embedding_provider(app_config.embeddings)
    query_embedding = embedder.embed([query])[0]

    client = chromadb.PersistentClient(
        path=str(app_config.chroma.persist_directory),
        settings=Settings(anonymized_telemetry=False),
    )

    try:
        collection = client.get_collection(name=app_config.chroma.collection_name)
    except Exception:
        return []

    n = collection.count()
    if n == 0:
        return []

    where = {"path": path_filter} if path_filter else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, n),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]  # cosine distance: 0 = identical

    out: list[RetrievedChunk] = []
    for i, (cid, text, meta, dist) in enumerate(zip(ids, docs, metas, distances)):
        score = 1.0 - dist  # convert distance to similarity
        meta = meta or {}
        chunk = Chunk(
            id=str(cid),
            document_id=meta.get("document_id", ""),
            text=text or "",
            start_line=meta.get("start_line") or None,
            end_line=meta.get("end_line") or None,
            heading=meta.get("heading") or None,
            symbol=meta.get("symbol") or None,
            path=meta.get("path") or None,
        )
        out.append(RetrievedChunk(chunk=chunk, score=float(score)))
    return out
