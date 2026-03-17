from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml


@dataclass
class WorkspaceConfig:
    name: str
    root_paths: List[Path]
    include_globs: List[str] = field(default_factory=list)
    exclude_globs: List[str] = field(default_factory=list)


@dataclass
class ChromaConfig:
    persist_directory: Path
    collection_name: str


@dataclass
class EmbeddingsConfig:
    provider: str = "ollama"  # or "sentence-transformers"
    model: str = "nomic-embed-text"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"


@dataclass
class AppConfig:
    workspaces: List[WorkspaceConfig]
    chroma: ChromaConfig
    embeddings: EmbeddingsConfig
    llm: "LLMConfig" = field(default_factory=lambda: LLMConfig())


def load_config(path: Path) -> AppConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    workspaces = [
        WorkspaceConfig(
            name=w["name"],
            root_paths=[Path(p) for p in w.get("root_paths", [])],
            include_globs=w.get("include_globs", []),
            exclude_globs=w.get("exclude_globs", []),
        )
        for w in data.get("workspaces", [])
    ]

    chroma_raw = data.get("chroma", {})
    chroma = ChromaConfig(
        persist_directory=Path(chroma_raw.get("persist_directory", "./chroma")),
        collection_name=chroma_raw.get("collection_name", "default"),
    )

    emb_raw = data.get("embeddings", {})
    embeddings = EmbeddingsConfig(
        provider=emb_raw.get("provider", "ollama"),
        model=emb_raw.get("model", "nomic-embed-text"),
        extra=emb_raw.get("extra", {}),
    )

    llm_raw = data.get("llm", {})
    llm = LLMConfig(
        provider=llm_raw.get("provider", "ollama"),
        model=llm_raw.get("model", "llama3.2:3b"),
        base_url=llm_raw.get("base_url", "http://localhost:11434"),
    )

    return AppConfig(
        workspaces=workspaces,
        chroma=chroma,
        embeddings=embeddings,
        llm=llm,
    )