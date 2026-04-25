# author: jf
import re
from typing import Any

from app.application.ports.vector_store_port import VectorStorePort


class RagRetrieverService:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self.vector_store = vector_store
        # 避免在请求链路构建阶段做重量级 import 探测，防止阻塞“结束并评分”流。
        self.llamaindex_available = False

    def query(self, query: str, top_k: int) -> tuple[str, list[dict[str, Any]]]:
        sources = self.vector_store.similarity_search(query=query, top_k=top_k)
        return self.build_answer_from_sources(sources), sources

    def ingest_documents(self, documents: list[dict[str, Any]]) -> int:
        return self.vector_store.add_documents(documents)

    def build_answer_from_sources(self, sources: list[dict[str, Any]]) -> str:
        # 这里把检索命中的原始片段压缩成可直接注入 prompt 的摘要，
        # 避免继续返回“RAG answer for ...”这类占位文本污染面试上下文。
        if not isinstance(sources, list) or not sources:
            return ""

        sections: list[str] = []
        seen_signatures: set[str] = set()
        for index, item in enumerate(sources, start=1):
            if not isinstance(item, dict):
                continue

            metadata = item.get("metadata")
            safe_metadata = metadata if isinstance(metadata, dict) else {}
            source_id = str(item.get("source_id") or "").strip()
            source_name = str(
                safe_metadata.get("originalFilename")
                or safe_metadata.get("sourceName")
                or source_id
                or f"片段{index}"
            ).strip()
            content = self._normalize_content(item.get("content"))
            if not content:
                continue

            signature = f"{source_name}:{content[:120]}"
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            similarity_text = self._format_similarity(safe_metadata.get("similarity"))
            prefix_parts = [f"[参考片段{len(sections) + 1}] 来源:{source_name}"]
            if similarity_text:
                prefix_parts.append(f"相似度:{similarity_text}")
            sections.append(f"{' | '.join(prefix_parts)}\n{content}")
            if len(sections) >= 4:
                break

        return "\n\n".join(sections)

    def _normalize_content(self, raw_value: Any) -> str:
        content = re.sub(r"\s+", " ", str(raw_value or "")).strip()
        if not content:
            return ""
        if len(content) <= 260:
            return content
        return f"{content[:257]}..."

    @staticmethod
    def _format_similarity(raw_value: Any) -> str:
        try:
            similarity = float(raw_value)
        except (TypeError, ValueError):
            return ""
        if similarity <= 0:
            return ""
        return f"{similarity:.2f}"
