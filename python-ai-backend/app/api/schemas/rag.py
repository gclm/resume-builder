# author: jf
from typing import Any

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topK: int | None = Field(default=None, ge=1, le=20)


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

