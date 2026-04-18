# author: jf
from app.application.dto.rag_dto import RagIngestRequestDto, RagIngestResponseDto
from app.bootstrap.container import build_rag_retriever


def ingest_rag_documents(request: RagIngestRequestDto) -> RagIngestResponseDto:
    retriever = build_rag_retriever()
    inserted = retriever.ingest_documents(
        [
            {
                "source_id": (item.source_id or "").strip(),
                "content": item.content.strip(),
                "metadata": item.metadata or {},
            }
            for item in request.documents
        ]
    )
    return RagIngestResponseDto(inserted=inserted)
