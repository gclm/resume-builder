# author: jf
from typing import Any

from pydantic import BaseModel, Field


# 查询接口 request schema。
class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topK: int | None = Field(default=None, ge=1, le=20)


# 查询结果里的来源对象。
class RagSource(BaseModel):
    sourceId: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource]


class RagDocumentInput(BaseModel):
    sourceId: str | None = None
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIngestRequest(BaseModel):
    documents: list[RagDocumentInput] = Field(min_length=1)


class RagIngestResponse(BaseModel):
    inserted: int


# 统一上传接口里的单文件结果。
class RagUploadFileResult(BaseModel):
    fileName: str
    contentType: str
    sourceType: str
    ingestSource: str
    chunkCount: int
    insertedCount: int
    status: str
    errorMessage: str | None = None


class RagUploadResponse(BaseModel):
    totalFiles: int
    succeededFiles: int
    failedFiles: int
    inserted: int
    files: list[RagUploadFileResult]
