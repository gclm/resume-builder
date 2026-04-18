# author: jf
from typing import Any, Protocol


class VectorStorePort(Protocol):
    def add_documents(self, documents: list[dict[str, Any]]) -> int: ...

    def similarity_search(self, query: str, top_k: int) -> list[dict[str, Any]]: ...
