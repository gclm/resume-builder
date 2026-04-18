# author: jf
from fastapi import APIRouter

from app.api.mappers.rag_mapper import (
    rag_ingest_request_to_dto,
    rag_ingest_response_from_dto,
    rag_query_request_to_dto,
    rag_query_response_from_dto,
)
from app.api.schemas.rag import RagIngestRequest, RagIngestResponse, RagQueryRequest, RagQueryResponse
from app.application.use_cases.ingest_rag_documents import ingest_rag_documents as ingest_rag_documents_use_case
from app.application.use_cases.run_rag_query import run_rag_query as run_rag_query_use_case

router = APIRouter(prefix="/api/ai", tags=["ai-rag"])


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(request: RagQueryRequest) -> RagQueryResponse:
    return rag_query_response_from_dto(run_rag_query_use_case(rag_query_request_to_dto(request)))


@router.post("/rag/documents", response_model=RagIngestResponse)
def rag_ingest_documents(request: RagIngestRequest) -> RagIngestResponse:
    return rag_ingest_response_from_dto(
        ingest_rag_documents_use_case(rag_ingest_request_to_dto(request))
    )
