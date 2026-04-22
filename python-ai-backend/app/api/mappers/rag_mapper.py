# author: jf
from typing import BinaryIO

from app.api.schemas.rag import (
    RagIngestRequest,
    RagIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagSource,
    RagUploadFileResult,
    RagUploadResponse,
)
from app.application.dto.rag_dto import (
    RagDocumentInputDto,
    RagIngestRequestDto,
    RagIngestResponseDto,
    RagQueryRequestDto,
    RagQueryResponseDto,
    RagUploadAssetDto,
    RagUploadResponseDto,
)


def rag_query_request_to_dto(request: RagQueryRequest) -> RagQueryRequestDto:
    # API 层 camelCase / 校验模型 转成应用层 snake_case DTO。
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


def rag_upload_assets_to_dto(files: list[tuple[str, str, BinaryIO]]) -> list[RagUploadAssetDto]:
    # Route 层只保留元数据和可读取的文件流，避免在进入 use case 前整批读满内存。
    return [
        RagUploadAssetDto(file_name=file_name, content_type=content_type, file_stream=file_stream)
        for file_name, content_type, file_stream in files
    ]


def rag_upload_response_from_dto(response: RagUploadResponseDto) -> RagUploadResponse:
    # 应用层统一使用 snake_case，返回给前端前再映射回现有前端契约。
    return RagUploadResponse(
        totalFiles=response.total_files,
        succeededFiles=response.succeeded_files,
        failedFiles=response.failed_files,
        inserted=response.inserted,
        files=[
            RagUploadFileResult(
                fileName=item.file_name,
                contentType=item.content_type,
                sourceType=item.source_type,
                ingestSource=item.ingest_source,
                chunkCount=item.chunk_count,
                insertedCount=item.inserted_count,
                status=item.status,
                errorMessage=item.error_message,
            )
            for item in response.files
        ],
    )
