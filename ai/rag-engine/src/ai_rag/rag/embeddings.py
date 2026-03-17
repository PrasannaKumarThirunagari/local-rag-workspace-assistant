"""Embedding provider: Ollama or sentence-transformers."""
from typing import Protocol

from ai_rag.config import EmbeddingsConfig


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


def create_embedding_provider(config: EmbeddingsConfig) -> EmbeddingProvider:
    if config.provider == "ollama":
        return OllamaEmbeddings(config)
    if config.provider == "sentence-transformers":
        return SentenceTransformerEmbeddings(config)
    raise ValueError(f"Unknown embeddings provider: {config.provider}")


class OllamaEmbeddings:
    def __init__(self, config: EmbeddingsConfig):
        self.model = config.model
        self.base_url = config.extra.get("base_url", "http://localhost:11434")

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        result: list[list[float]] = []
        with httpx.Client(timeout=60.0) as client:
            for t in texts:
                r = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": t},
                )
                r.raise_for_status()
                data = r.json()
                result.append(data["embedding"])
        return result


class SentenceTransformerEmbeddings:
    def __init__(self, config: EmbeddingsConfig):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(config.model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]
