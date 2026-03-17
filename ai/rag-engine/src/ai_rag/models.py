from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class DocumentMetadata:
    path: Path
    doc_type: str
    language: Optional[str] = None
    modified_at: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    id: str
    text: str
    metadata: DocumentMetadata


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    heading: Optional[str] = None
    symbol: Optional[str] = None
    path: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Query:
    text: str
    workspace: str
    top_k: int = 8


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class Answer:
    question: str
    text: str
    snippets: List[RetrievedChunk]