"""CLI to ask questions against the indexed workspace."""
import argparse
from pathlib import Path

from ai_rag.config import load_config
from ai_rag.rag.qa_service import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question using RAG.")
    parser.add_argument("question", nargs="+", help="Question to ask")
    parser.add_argument("--config", default="config/config.yaml", help="Config path")
    parser.add_argument("--top-k", type=int, default=8, help="Number of chunks to retrieve")
    parser.add_argument("--path", default=None, help="Filter by file path (substring)")
    args = parser.parse_args()

    question = " ".join(args.question)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    app_config = load_config(config_path)
    answer = answer_question(
        app_config,
        question=question,
        top_k=args.top_k,
        path_filter=args.path,
    )

    print(answer.text)
    if answer.snippets:
        print("\n--- Retrieved snippets ---")
        for i, rc in enumerate(answer.snippets[:5], 1):
            path = rc.chunk.path or "?"
            lines = f"{rc.chunk.start_line}-{rc.chunk.end_line}" if rc.chunk.start_line else ""
            print(f"  [{i}] {path}:{lines} (score={rc.score:.3f})")


if __name__ == "__main__":
    main()
