# author: jf
from app.api.schemas.rag import RagIngestRequest, RagIngestResponse, RagQueryRequest, RagQueryResponse, RagSource
from app.application.dto.rag_dto import (
    RagDocumentInputDto,
    RagIngestRequestDto,
    RagIngestResponseDto,
    RagQueryRequestDto,
    RagQueryResponseDto,
)


def rag_query_request_to_dto(request: RagQueryRequest) -> RagQueryRequestDto:
    return RagQueryRequestDto(query=request.query, top_k=request.topK)


def rag_query_response_from_dto(response: RagQueryResponseDto) -> RagQueryResponse:
    return RagQueryResponse(
        answer=response.answer,
        sources=[
            RagSource(sourceId=item.source_id, content=item.content, metadata=item.metadata)
            for item in response.sources
        ],
    )


def rag_ingest_request_to_dto(request: RagIngestRequest) -> RagIngestRequestDto:
    return RagIngestRequestDto(
        documents=[
            RagDocumentInputDto(
                source_id=document.sourceId,
                content=document.content,
                metadata=document.metadata,
            )
            for document in request.documents
        ]
    )


def rag_ingest_response_from_dto(response: RagIngestResponseDto) -> RagIngestResponse:
    return RagIngestResponse(inserted=response.inserted)
