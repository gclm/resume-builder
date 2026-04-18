# author: jf
from typing import Any

from app.application.ports.vector_store_port import VectorStorePort


class RagRetrieverService:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self.vector_store = vector_store
        self.llamaindex_available = False
        try:
            from llama_index.core import Document  # noqa: F401

            self.llamaindex_available = True
        except Exception:
            self.llamaindex_available = False

    def query(self, query: str, top_k: int) -> tuple[str, list[dict[str, Any]]]:
        sources = self.vector_store.similarity_search(query=query, top_k=top_k)
        safe_query = (query or "").strip()
        prefix = "LlamaIndex" if self.llamaindex_available else "RAG"
        if sources:
            answer = f"{prefix} answer for: {safe_query}"
        else:
            answer = f"{prefix} answer for: {safe_query}. Context is insufficient."
        return answer, sources

    def ingest_documents(self, documents: list[dict[str, Any]]) -> int:
        return self.vector_store.add_documents(documents)
