# author: jf
from threading import Lock
from typing import Any


class PgVectorStoreAdapter:
    _documents_by_url: dict[str, list[dict[str, Any]]] = {}
    _lock = Lock()

    def __init__(self, connection_url: str) -> None:
        self.connection_url = (connection_url or "").strip()
        self.pgvector_available = False
        try:
            import pgvector  # noqa: F401

            self.pgvector_available = True
        except Exception:
            self.pgvector_available = False

    def _storage_key(self) -> str:
        return self.connection_url or "__default__"

    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        inserted = 0
        with self._lock:
            store = self._documents_by_url.setdefault(self._storage_key(), [])
            for raw in documents:
                if not isinstance(raw, dict):
                    continue
                content = str(raw.get("content") or "").strip()
                if not content:
                    continue
                source_id = str(raw.get("source_id") or raw.get("sourceId") or "").strip()
                if not source_id:
                    source_id = f"doc-{len(store) + 1}"
                metadata = raw.get("metadata")
                safe_metadata = metadata if isinstance(metadata, dict) else {}
                store.append(
                    {
                        "source_id": source_id,
                        "content": content,
                        "metadata": dict(safe_metadata),
                    }
                )
                inserted += 1
        return inserted

    def similarity_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        safe_query = (query or "").strip()
        safe_top_k = max(1, top_k)
        with self._lock:
            documents = list(self._documents_by_url.get(self._storage_key(), []))

        if not documents:
            return []

        query_terms = [token.lower() for token in safe_query.split() if token.strip()]
        if not query_terms:
            ranked = list(enumerate(documents))
        else:
            scored: list[tuple[int, int, dict[str, Any]]] = []
            for index, item in enumerate(documents):
                search_text = f"{item.get('source_id', '')} {item.get('content', '')}".lower()
                score = sum(1 for token in query_terms if token in search_text)
                scored.append((score, index, item))
            scored.sort(key=lambda row: (-row[0], row[1]))
            ranked = [(index, item) for score, index, item in scored if score > 0]
            if not ranked:
                ranked = list(enumerate(documents))

        results: list[dict[str, Any]] = []
        for _, item in ranked[:safe_top_k]:
            metadata = item.get("metadata")
            safe_metadata = metadata if isinstance(metadata, dict) else {}
            merged_metadata = {
                **safe_metadata,
                "topK": safe_top_k,
                "engine": "pgvector",
                "pgvectorAvailable": self.pgvector_available,
            }
            results.append(
                {
                    "source_id": str(item.get("source_id") or ""),
                    "content": str(item.get("content") or ""),
                    "metadata": merged_metadata,
                }
            )
        return results
