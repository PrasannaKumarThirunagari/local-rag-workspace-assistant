import argparse
from pathlib import Path

from ai_rag.config import load_config
from ai_rag.ingestion import index_workspace


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a configured workspace into ChromaDB.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        required=True,
        help="Name of the workspace to ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show config, do not index.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    app_config = load_config(config_path)

    ws = next((w for w in app_config.workspaces if w.name == args.workspace), None)
    if ws is None:
        print(f"Workspace '{args.workspace}' not found in {config_path}")
        available = ", ".join(w.name for w in app_config.workspaces) or "<none>"
        print(f"Available workspaces: {available}")
        return

    if args.dry_run:
        print(f"Workspace: {ws.name}")
        print("Root paths:")
        for p in ws.root_paths:
            print(f"  - {p}")
        print("\nInclude globs:", ws.include_globs or ["<none>"])
        print("Exclude globs:", ws.exclude_globs or ["<none>"])
        print(f"\nChroma: {app_config.chroma.persist_directory}")
        print(f"Embeddings: {app_config.embeddings.provider} / {app_config.embeddings.model}")
        return

    print(f"Ingesting workspace '{ws.name}'...")
    stats = index_workspace(app_config, ws)
    print(f"Done. Files: {stats['files']}, Chunks: {stats['chunks']}")


if __name__ == "__main__":
    main()

