"""Chunk documents by type: code (function/class), markdown (headings), text (lines)."""
import hashlib
import re
from pathlib import Path

from ai_rag.models import Chunk, Document

_MAX_CHARS = 768
_OVERLAP_LINES = 2
_LINE_CHUNK_SIZE = 35


def _chunk_id(document_id: str, index: int, text_slice: str) -> str:
    h = hashlib.sha256(f"{document_id}:{index}:{text_slice[:64]}".encode()).hexdigest()[:24]
    return f"{document_id}_{h}"


def _chunk_text(doc: Document) -> list[Chunk]:
    """Line-based chunks for plain text and config."""
    lines = doc.text.splitlines()
    chunks: list[Chunk] = []
    i = 0
    chunk_idx = 0
    while i < len(lines):
        block = lines[i : i + _LINE_CHUNK_SIZE]
        text = "\n".join(block)
        if not text.strip():
            i += 1
            continue
        start = i + 1
        end = i + len(block)
        chunk_id = _chunk_id(doc.id, chunk_idx, text)
        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=doc.id,
                text=text,
                start_line=start,
                end_line=end,
            )
        )
        i += _LINE_CHUNK_SIZE - _OVERLAP_LINES
        chunk_idx += 1
    return chunks


def _chunk_markdown(doc: Document) -> list[Chunk]:
    """Chunk by heading; fallback to sliding window."""
    lines = doc.text.splitlines()
    chunks: list[Chunk] = []
    current_heading: str | None = None
    current_block: list[str] = []
    start_line = 0
    chunk_idx = 0

    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s", line):
            if current_block:
                text = "\n".join(current_block)
                if text.strip():
                    chunk_id = _chunk_id(doc.id, chunk_idx, text)
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            document_id=doc.id,
                            text=text,
                            start_line=start_line + 1,
                            end_line=i,
                            heading=current_heading,
                        )
                    )
                    chunk_idx += 1
            current_heading = line.strip().lstrip("#").strip()
            current_block = [line]
            start_line = i
        else:
            current_block.append(line)
            if len("\n".join(current_block)) > _MAX_CHARS:
                text = "\n".join(current_block)
                chunk_id = _chunk_id(doc.id, chunk_idx, text)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=doc.id,
                        text=text,
                        start_line=start_line + 1,
                        end_line=i + 1,
                        heading=current_heading,
                    )
                )
                chunk_idx += 1
                current_block = current_block[-_OVERLAP_LINES:]
                start_line = i - _OVERLAP_LINES + 1

    if current_block:
        text = "\n".join(current_block)
        if text.strip():
            chunk_id = _chunk_id(doc.id, chunk_idx, text)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=doc.id,
                    text=text,
                    start_line=start_line + 1,
                    end_line=len(lines),
                    heading=current_heading,
                )
            )

    return chunks if chunks else _chunk_text(doc)


# Regex for C#/C-style: class, method, namespace, etc.
_CODE_BLOCK = re.compile(
    r"^(\s*)((?:public|private|protected|internal)?\s*(?:static\s+)?"
    r"(?:async\s+)?(?:class|interface|struct|enum|namespace|void|string|int|bool|var)\s+\w+.*)$",
    re.MULTILINE | re.IGNORECASE,
)


def _chunk_code(doc: Document) -> list[Chunk]:
    """Chunk by logical block (class/method) with fallback to line-based."""
    lines = doc.text.splitlines()
    chunks: list[Chunk] = []
    chunk_idx = 0
    i = 0

    while i < len(lines):
        block: list[str] = []
        symbol: str | None = None
        j = i

        # Find next block start (class, method, etc.)
        for k in range(i, len(lines)):
            m = _CODE_BLOCK.match(lines[k])
            if m:
                symbol = m.group(2).strip()
                j = k
                break

        if symbol and j > i:
            # Emit chunk from i to j (before the matched line)
            block = lines[i:j]
            if block:
                text = "\n".join(block)
                if text.strip():
                    chunk_id = _chunk_id(doc.id, chunk_idx, text)
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            document_id=doc.id,
                            text=text,
                            start_line=i + 1,
                            end_line=j,
                            symbol=symbol if len(symbol) < 80 else symbol[:77] + "...",
                        )
                    )
                    chunk_idx += 1
            i = j
            continue

        # Accumulate up to _MAX_CHARS
        block = []
        size = 0
        end = i
        for k in range(i, min(i + 80, len(lines))):
            line = lines[k]
            block.append(line)
            size += len(line) + 1
            end = k + 1
            if size >= _MAX_CHARS:
                break
        if block:
            text = "\n".join(block)
            if text.strip():
                chunk_id = _chunk_id(doc.id, chunk_idx, text)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=doc.id,
                        text=text,
                        start_line=i + 1,
                        end_line=end,
                        symbol=symbol,
                    )
                )
                chunk_idx += 1
            i = end - _OVERLAP_LINES if end - _OVERLAP_LINES > i else end
        else:
            i += 1

    return chunks if chunks else _chunk_text(doc)


def chunk_document(doc: Document) -> list[Chunk]:
    """Chunk a document according to its type."""
    t = doc.metadata.doc_type
    if t == "code":
        return _chunk_code(doc)
    if t == "markdown":
        return _chunk_markdown(doc)
    return _chunk_text(doc)
