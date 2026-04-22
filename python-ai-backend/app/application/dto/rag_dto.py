# author: jf
from dataclasses import dataclass, field
from typing import Any, BinaryIO


# RAG 查询入参 DTO。
@dataclass(slots=True)
class RagQueryRequestDto:
    query: str
    top_k: int | None = None


# RAG 查询结果里的单个来源。
@dataclass(slots=True)
class RagSourceDto:
    source_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


# RAG 查询响应 DTO。
@dataclass(slots=True)
class RagQueryResponseDto:
    answer: str
    sources: list[RagSourceDto] = field(default_factory=list)


# 旧的纯文档入库 DTO。
@dataclass(slots=True)
class RagDocumentInputDto:
    content: str
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RagIngestRequestDto:
    documents: list[RagDocumentInputDto] = field(default_factory=list)


@dataclass(slots=True)
class RagIngestResponseDto:
    inserted: int


# 统一上传接口的单个文件输入。
@dataclass(slots=True)
class RagUploadAssetDto:
    file_name: str
    content_type: str
    file_bytes: bytes | None = None
    file_stream: BinaryIO | None = None


# 统一上传接口的单个文件处理结果。
@dataclass(slots=True)
class RagUploadFileResultDto:
    file_name: str
    content_type: str
    source_type: str
    ingest_source: str
    chunk_count: int
    inserted_count: int
    status: str
    error_message: str | None = None


@dataclass(slots=True)
class RagUploadResponseDto:
    total_files: int
    succeeded_files: int
    failed_files: int
    inserted: int
    files: list[RagUploadFileResultDto] = field(default_factory=list)
