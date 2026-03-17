"""Type-specific parsers: read files and produce Document objects."""
import hashlib
from pathlib import Path

from ai_rag.models import Document, DocumentMetadata


_TYPE_BY_EXT: dict[str, tuple[str, str]] = {
    ".cs": ("code", "csharp"),
    ".cshtml": ("code", "razor"),
    ".md": ("markdown", "markdown"),
    ".json": ("config", "json"),
    ".yaml": ("config", "yaml"),
    ".yml": ("config", "yaml"),
    ".txt": ("text", "plain"),
    ".py": ("code", "python"),
    ".js": ("code", "javascript"),
    ".ts": ("code", "typescript"),
}


def _document_id(path: Path, mtime: float) -> str:
    key = f"{path.resolve().as_posix()}:{mtime}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def parse_file(path: Path, mtime: float | None = None) -> Document | None:
    """
    Read a file and return a Document. Returns None if unreadable or unsupported.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return None

    stat = path.stat() if mtime is None else None
    mtime = mtime if mtime is not None else (stat.st_mtime if stat else 0.0)

    ext = path.suffix.lower()
    doc_type, language = _TYPE_BY_EXT.get(ext, ("text", "plain"))

    doc_id = _document_id(path, mtime)
    meta = DocumentMetadata(
        path=path,
        doc_type=doc_type,
        language=language,
        modified_at=mtime,
    )
    return Document(id=doc_id, text=text, metadata=meta)
