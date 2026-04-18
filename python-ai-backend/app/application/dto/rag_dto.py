# author: jf
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RagQueryRequestDto:
    query: str
    top_k: int | None = None


@dataclass(slots=True)
class RagSourceDto:
    source_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RagQueryResponseDto:
    answer: str
    sources: list[RagSourceDto] = field(default_factory=list)


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
