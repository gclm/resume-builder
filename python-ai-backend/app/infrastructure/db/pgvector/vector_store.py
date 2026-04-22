# author: jf
from __future__ import annotations

from typing import Any

from app.application.ports.embedding_port import EmbeddingPort
from app.domain.exceptions.rag_exceptions import EmbeddingError, VectorStoreError

_TABLE_NAME = "rag_document_chunks"


class PgVectorStoreAdapter:
    def __init__(
        self,
        connection_url: str,
        embedding_client: EmbeddingPort | None = None,
        embedding_model_name: str = "",
        connect_timeout_seconds: int = 8,
    ) -> None:
        self.connection_url = (connection_url or "").strip()
        self.embedding_client = embedding_client
        self.embedding_model_name = (embedding_model_name or "").strip()
        self.connect_timeout_seconds = self._normalize_connect_timeout(connect_timeout_seconds)

    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        normalized_documents = self._normalize_documents(documents)
        if not normalized_documents:
            _log_pgvector("add_documents 无有效文档，直接返回 0")
            return 0
        embeddings = self._embed_texts([item["content"] for item in normalized_documents])
        return self._insert_documents(normalized_documents, embeddings)

    def add_documents_with_embeddings(
        self,
        documents: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        normalized_documents = self._normalize_documents(documents)
        if not normalized_documents:
            _log_pgvector("add_documents_with_embeddings 无有效文档，直接返回 0")
            return 0
        if len(normalized_documents) != len(embeddings):
            raise VectorStoreError("documents 与 embeddings 数量不一致，无法写入 pgvector")
        normalized_embeddings = [self._normalize_embedding(item) for item in embeddings]
        return self._insert_documents(normalized_documents, normalized_embeddings)

    def similarity_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        safe_query = (query or "").strip()
        if not safe_query:
            return []

        query_embeddings = self._embed_texts([safe_query])
        if not query_embeddings:
            return []

        query_embedding = query_embeddings[0]
        query_dimensions = len(query_embedding)
        safe_top_k = max(1, top_k)
        query_vector = self._to_vector_literal(query_embedding)

        psycopg, dict_row, _ = self._load_db_modules()
        sql_lines = [
            "SELECT",
            "    source_id,",
            "    content,",
            "    metadata,",
            "    embedding_model,",
            "    embedding_dimensions,",
            "    1 - (embedding <=> %s::vector) AS similarity",
            f"FROM {_TABLE_NAME}",
            "WHERE embedding_dimensions = %s",
        ]
        params: list[Any] = [query_vector, query_dimensions]
        if self.embedding_model_name:
            sql_lines.append("  AND embedding_model = %s")
            params.append(self.embedding_model_name)
        sql_lines.extend(
            [
                "ORDER BY embedding <=> %s::vector",
                "LIMIT %s",
            ]
        )
        params.extend([query_vector, safe_top_k])

        _log_pgvector(
            "开始执行相似度检索",
            top_k=safe_top_k,
            query_dimensions=query_dimensions,
            connect_timeout_seconds=self.connect_timeout_seconds,
        )
        statement_timeout_ms = int(self.connect_timeout_seconds * 1000)
        try:
            with psycopg.connect(
                self._require_connection_url(),
                row_factory=dict_row,
                connect_timeout=self.connect_timeout_seconds,
            ) as connection:
                with connection.cursor() as cursor:
                    # connect_timeout 只限制建连，语句级超时用于限制已连接后的查询阻塞。
                    # PostgreSQL 的 SET/SET LOCAL 在这里不接受绑定参数占位符，
                    # 否则 psycopg 会把它转换为 `$1` 并触发语法错误。
                    cursor.execute(f"SET LOCAL statement_timeout = {statement_timeout_ms}")
                    cursor.execute("\n".join(sql_lines), params)
                    rows = cursor.fetchall()
        except Exception as exc:
            _log_pgvector("相似度检索失败", error=str(exc))
            raise VectorStoreError(
                f"pgvector 检索失败（connect_timeout={self.connect_timeout_seconds}s）: {exc}"
            ) from exc

        _log_pgvector("相似度检索完成", row_count=len(rows))
        results: list[dict[str, Any]] = []
        for row in rows:
            metadata = row.get("metadata")
            safe_metadata = metadata if isinstance(metadata, dict) else {}
            results.append(
                {
                    "source_id": str(row.get("source_id") or ""),
                    "content": str(row.get("content") or ""),
                    "metadata": {
                        **safe_metadata,
                        "topK": safe_top_k,
                        "engine": "pgvector",
                        "pgvectorAvailable": True,
                        "embeddingModel": str(row.get("embedding_model") or ""),
                        "embeddingDimensions": int(row.get("embedding_dimensions") or 0),
                        "similarity": float(row.get("similarity") or 0.0),
                    },
                }
            )
        return results

    def _insert_documents(
        self,
        documents: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        if len(documents) != len(embeddings):
            raise VectorStoreError("documents 与 embeddings 数量不一致，无法写入 pgvector")

        psycopg, _, Jsonb = self._load_db_modules()
        params: list[tuple[Any, ...]] = []
        for document, embedding in zip(documents, embeddings, strict=True):
            params.append(
                (
                    document["source_id"],
                    document["chunk_index"],
                    document["original_filename"],
                    document["original_content_type"],
                    document["source_type"],
                    document["ingest_source"],
                    document["content"],
                    Jsonb(document["metadata"]),
                    self._to_vector_literal(embedding),
                    self.embedding_model_name,
                    len(embedding),
                )
            )

        sql = f"""
        INSERT INTO {_TABLE_NAME} (
            source_id,
            chunk_index,
            original_filename,
            original_content_type,
            source_type,
            ingest_source,
            content,
            metadata,
            embedding,
            embedding_model,
            embedding_dimensions
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
        """
        _log_pgvector(
            "开始写入 pgvector",
            document_count=len(params),
            connect_timeout_seconds=self.connect_timeout_seconds,
        )
        try:
            with psycopg.connect(
                self._require_connection_url(),
                connect_timeout=self.connect_timeout_seconds,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.executemany(sql, params)
                connection.commit()
        except Exception as exc:
            _log_pgvector("写入 pgvector 失败", error=str(exc))
            raise VectorStoreError(
                f"pgvector 写入失败（connect_timeout={self.connect_timeout_seconds}s）: {exc}"
            ) from exc

        _log_pgvector("写入 pgvector 完成", inserted_count=len(params))
        return len(params)

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.embedding_client is None:
            raise EmbeddingError("未配置 Embedding 客户端，无法执行向量化")
        return [self._normalize_embedding(item) for item in self.embedding_client.embed_texts(texts)]

    def _normalize_documents(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(documents):
            if not isinstance(raw, dict):
                continue
            content = str(raw.get("content") or "").strip()
            if not content:
                continue
            source_id = str(raw.get("source_id") or raw.get("sourceId") or "").strip() or f"doc-{index + 1}"
            metadata = raw.get("metadata")
            safe_metadata = metadata if isinstance(metadata, dict) else {}
            chunk_index = self._to_int(safe_metadata.get("chunkIndex"), index)
            original_filename = str(safe_metadata.get("originalFilename") or source_id)
            original_content_type = str(safe_metadata.get("originalContentType") or "text/plain")
            source_type = str(safe_metadata.get("sourceType") or "document")
            ingest_source = str(safe_metadata.get("ingestSource") or "text_document")
            normalized.append(
                {
                    "source_id": source_id,
                    "chunk_index": chunk_index,
                    "original_filename": original_filename,
                    "original_content_type": original_content_type,
                    "source_type": source_type,
                    "ingest_source": ingest_source,
                    "content": content,
                    "metadata": {
                        **safe_metadata,
                        "originalFilename": original_filename,
                        "originalContentType": original_content_type,
                        "sourceType": source_type,
                        "ingestSource": ingest_source,
                        "chunkIndex": chunk_index,
                    },
                }
            )
        return normalized

    @staticmethod
    def _normalize_embedding(raw_embedding: Any) -> list[float]:
        if not isinstance(raw_embedding, (list, tuple)) or not raw_embedding:
            raise VectorStoreError("Embedding 数据为空或格式非法")
        try:
            return [float(value) for value in raw_embedding]
        except (TypeError, ValueError) as exc:
            raise VectorStoreError(f"Embedding 数据格式非法: {exc}") from exc

    @staticmethod
    def _to_vector_literal(values: list[float]) -> str:
        return "[" + ",".join(f"{float(value):.12g}" for value in values) + "]"

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_connect_timeout(raw_timeout: int) -> int:
        try:
            normalized = int(raw_timeout)
        except (TypeError, ValueError):
            return 8
        return max(1, normalized)

    def _require_connection_url(self) -> str:
        if not self.connection_url:
            raise VectorStoreError("PGVECTOR_DATASOURCE_URL 未配置，无法连接 pgvector")
        return self.connection_url

    @staticmethod
    def _load_db_modules():
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb
        except ImportError as exc:
            raise VectorStoreError("缺少 psycopg 依赖，无法访问 PostgreSQL + pgvector") from exc
        return psycopg, dict_row, Jsonb


def _log_pgvector(message: str, **extra: object) -> None:
    parts = [f"[知识库上传][PgVector] {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)
