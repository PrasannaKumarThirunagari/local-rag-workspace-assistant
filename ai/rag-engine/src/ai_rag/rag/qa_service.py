"""RAG QA: retrieve chunks, build prompt, call LLM."""
import httpx

from ai_rag.config import AppConfig
from ai_rag.models import Answer, RetrievedChunk
from ai_rag.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from ai_rag.rag.retriever import retrieve


def _call_ollama(prompt: str, system: str, model: str, base_url: str) -> str:
    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "system": system,
                "prompt": prompt,
                "stream": False,
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()


def answer_question(
    app_config: AppConfig,
    question: str,
    top_k: int = 8,
    path_filter: str | None = None,
) -> Answer:
    """
    Retrieve relevant chunks, build context, call Ollama, return answer + snippets.
    """
    snippets_list = retrieve(
        app_config,
        query=question,
        top_k=top_k,
        path_filter=path_filter,
    )

    if not snippets_list:
        return Answer(
            question=question,
            text="I don't know based on the indexed documents. (No relevant snippets found. Run ingestion first?)",
            snippets=[],
        )

    formatted = [
        (
            rc.chunk.path or "unknown",
            rc.chunk.text,
            rc.chunk.start_line or 0,
            rc.chunk.end_line or 0,
        )
        for rc in snippets_list
    ]

    user_prompt = build_user_prompt(question, formatted)

    llm = app_config.llm
    model = llm.model if llm else "llama3.2:3b"
    base_url = llm.base_url if llm else "http://localhost:11434"

    try:
        answer_text = _call_ollama(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
            model=model,
            base_url=base_url,
        )
    except httpx.ConnectError:
        answer_text = (
            "Cannot connect to Ollama. Start Ollama and pull a model: "
            "ollama pull llama3.2:3b"
        )
    except Exception as e:
        answer_text = f"Error calling LLM: {e}"

    return Answer(
        question=question,
        text=answer_text,
        snippets=snippets_list,
    )
