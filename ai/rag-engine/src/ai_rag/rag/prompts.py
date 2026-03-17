"""Prompt templates for grounded, citation-focused answers."""

SYSTEM_PROMPT = """You are a helpful assistant that answers questions **only** using the provided context from indexed code and documentation.

Rules:
- Answer **only** from the context below. Do not use external knowledge.
- If the answer is not in the context, say: "I don't know based on the indexed documents."
- Always include a "Sources:" section listing the file paths and line ranges (path:start_line-end_line) for each snippet you used.
- Be concise. Cite specific code or text from the context."""

USER_PROMPT_TEMPLATE = """Context from indexed documents:

{context}

---

Question: {question}

Provide your answer using only the context above. Include a Sources section at the end."""


def build_context(snippets: list[tuple[str, str, int, int]]) -> str:
    """Format snippets for the prompt. Each tuple: (path, text, start_line, end_line)."""
    parts = []
    for i, (path, text, start, end) in enumerate(snippets, 1):
        header = f"[{i}] {path}:{start}-{end}"
        parts.append(f"{header}\n```\n{text}\n```")
    return "\n\n".join(parts)


def build_user_prompt(question: str, snippets: list[tuple[str, str, int, int]]) -> str:
    context = build_context(snippets)
    return USER_PROMPT_TEMPLATE.format(context=context, question=question)
