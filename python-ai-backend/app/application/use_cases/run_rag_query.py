# author: jf
from app.application.dto.rag_dto import RagQueryRequestDto, RagQueryResponseDto, RagSourceDto
from app.bootstrap.container import build_rag_retriever, resolve_settings


def run_rag_query(request: RagQueryRequestDto) -> RagQueryResponseDto:
    settings = resolve_settings()
    retriever = build_rag_retriever(settings)
    top_k = request.top_k or settings.app_rag_top_k
    answer, raw_sources = retriever.query(query=request.query.strip(), top_k=top_k)
    return RagQueryResponseDto(
        answer=answer,
        sources=[
            RagSourceDto(
                source_id=str(item.get("source_id") or ""),
                content=str(item.get("content") or ""),
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            )
            for item in raw_sources
        ],
    )
