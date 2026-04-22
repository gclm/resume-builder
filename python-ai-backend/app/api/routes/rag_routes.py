# author: jf
from typing import BinaryIO
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.mappers.rag_mapper import (
    rag_ingest_request_to_dto,
    rag_ingest_response_from_dto,
    rag_query_request_to_dto,
    rag_query_response_from_dto,
    rag_upload_assets_to_dto,
    rag_upload_response_from_dto,
)
from app.api.schemas.rag import (
    RagIngestRequest,
    RagIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagUploadResponse,
)
from app.application.use_cases.ingest_rag_documents import ingest_rag_documents as ingest_rag_documents_use_case
from app.application.use_cases.run_rag_query import run_rag_query as run_rag_query_use_case
from app.application.use_cases.upload_and_ingest_rag_assets import (
    upload_and_ingest_rag_assets as upload_and_ingest_rag_assets_use_case,
)

router = APIRouter(prefix="/api/ai", tags=["ai-rag"])


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(request: RagQueryRequest) -> RagQueryResponse:
    return rag_query_response_from_dto(run_rag_query_use_case(rag_query_request_to_dto(request)))


@router.post("/rag/documents", response_model=RagIngestResponse)
def rag_ingest_documents(request: RagIngestRequest) -> RagIngestResponse:
    return rag_ingest_response_from_dto(
        ingest_rag_documents_use_case(rag_ingest_request_to_dto(request))
    )


@router.post("/rag/upload", response_model=RagUploadResponse)
async def rag_upload_assets(files: list[UploadFile] = File(...)) -> RagUploadResponse:
    trace_id = uuid4().hex[:8]
    _log_route(trace_id, "收到上传请求", file_count=len(files))

    # 路由层只负责 HTTP 入参接收和日志观察。
    # 文件读取、OCR、Embedding、pgvector 写入都是阻塞链路，必须整体移出事件循环，
    # 否则一次上传就会卡住同进程内其他 FastAPI 请求。
    try:
        return await run_in_threadpool(_handle_rag_upload_request, files, trace_id)
    except Exception as exc:
        _log_route(trace_id, "上传请求异常", error=str(exc))
        raise


def _handle_rag_upload_request(files: list[UploadFile], trace_id: str) -> RagUploadResponse:
    # 同步上传流水线的职责：
    # 1) 只登记文件名、content-type 和可读取的 file handle，不在路由层预读整批字节。
    # 2) 让 application use case 逐文件执行限流读取、解析、OCR、切块、向量化和入库。
    # 3) 保持现有前端响应契约，并记录成功/失败汇总日志。
    assets: list[tuple[str, str, BinaryIO]] = []
    for index, item in enumerate(files, start=1):
        file_name = item.filename or "upload.bin"
        content_type = item.content_type or "application/octet-stream"
        _log_route(trace_id, "登记上传文件", index=index, file_name=file_name, content_type=content_type)
        item.file.seek(0)
        assets.append((file_name, content_type, item.file))

    response_dto = upload_and_ingest_rag_assets_use_case(
        rag_upload_assets_to_dto(assets),
        trace_id=trace_id,
    )
    _log_route(
        trace_id,
        "上传请求处理完成",
        total_files=response_dto.total_files,
        succeeded_files=response_dto.succeeded_files,
        failed_files=response_dto.failed_files,
        inserted=response_dto.inserted,
    )
    return rag_upload_response_from_dto(response_dto)


def _log_route(trace_id: str, message: str, **extra: object) -> None:
    parts = [f"[知识库上传][trace={trace_id}][路由] {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)
