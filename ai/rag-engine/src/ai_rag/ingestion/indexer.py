"""Index documents into ChromaDB with embeddings."""
from pathlib import Path

import chromadb
from chromadb.config import Settings

from ai_rag.config import AppConfig, WorkspaceConfig
from ai_rag.ingestion.file_scanner import ScannedFile, scan_workspace
from ai_rag.ingestion.parsers import parse_file
from ai_rag.ingestion.chunker import chunk_document
from ai_rag.rag.embeddings import create_embedding_provider


def index_workspace(app_config: AppConfig, workspace: WorkspaceConfig) -> dict:
    """
    Scan, parse, chunk, embed, and index the workspace. Returns stats.
    """
    embedder = create_embedding_provider(app_config.embeddings)

    client = chromadb.PersistentClient(
        path=str(app_config.chroma.persist_directory),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=app_config.chroma.collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # For full rebuild, reset collection in safe batches (Chroma has a max delete batch size)
    n = collection.count()
    if n > 0:
        # Delete in chunks to avoid BatchSizeExceededError
        while True:
            existing = collection.get(limit=5000)
            ids = existing.get("ids") or []
            if not ids:
                break
            collection.delete(ids=ids)

    total_files = 0
    total_chunks = 0
    batch_size = 32
    batch_ids: list[str] = []
    batch_texts: list[str] = []
    batch_metas: list[dict] = []

    for scanned in scan_workspace(workspace):
        doc = parse_file(scanned.path, scanned.mtime)
        if doc is None:
            continue
        total_files += 1
        chunks = chunk_document(doc)
        path_str = str(scanned.path)

        for c in chunks:
            meta = {
                "path": path_str,
                "doc_type": doc.metadata.doc_type,
                "start_line": c.start_line or 0,
                "end_line": c.end_line or 0,
                "heading": c.heading or "",
                "symbol": c.symbol or "",
            }
            batch_ids.append(c.id)
            batch_texts.append(c.text)
            batch_metas.append(meta)
            total_chunks += 1

            if len(batch_ids) >= batch_size:
                embeddings = embedder.embed(batch_texts)
                collection.add(
                    ids=batch_ids,
                    documents=batch_texts,
                    embeddings=embeddings,
                    metadatas=batch_metas,
                )
                batch_ids, batch_texts, batch_metas = [], [], []

    if batch_ids:
        embeddings = embedder.embed(batch_texts)
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_metas,
        )

    return {"files": total_files, "chunks": total_chunks}
