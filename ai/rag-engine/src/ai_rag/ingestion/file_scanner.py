"""Walks workspace root paths and yields matching files."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ai_rag.config import WorkspaceConfig


@dataclass
class ScannedFile:
    path: Path
    relative_path: str
    mtime: float


def _matches_any_glob(rel_path: Path, globs: list[str]) -> bool:
    """True if relative path matches any glob (supports **)."""
    s = rel_path.as_posix()
    for g in globs:
        if Path(s).match(g):
            return True
    return False


def scan_workspace(workspace: WorkspaceConfig) -> Iterator[ScannedFile]:
    """
    Walk workspace root paths and yield files matching include_globs and not matching exclude_globs.
    Paths are resolved relative to each root.
    """
    include = workspace.include_globs or ["**/*"]
    exclude = workspace.exclude_globs or []

    for root in workspace.root_paths:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                continue
            rel_path = Path(rel)
            if not _matches_any_glob(rel_path, include):
                continue
            if _matches_any_glob(rel_path, exclude):
                continue
            try:
                mtime = p.stat().st_mtime
            except OSError:
                mtime = 0.0
            yield ScannedFile(path=p, relative_path=rel, mtime=mtime)
