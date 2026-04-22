# author: jf
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.rag_exceptions import (
    EmbeddingError,
    FileParseError,
    FileTooLargeError,
    ImageOcrError,
    UnsupportedFileTypeError,
    VectorStoreError,
)


def register_error_handlers(app: FastAPI) -> None:
    # 这些 handler 只处理“请求级失败”。
    # 如果是批量上传里的单文件失败，use case 会把错误写到 files[]，不会走这里。
    @app.exception_handler(UnsupportedFileTypeError)
    async def handle_unsupported_file_type(_: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileParseError)
    async def handle_file_parse_error(_: Request, exc: FileParseError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileTooLargeError)
    async def handle_file_too_large(_: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": str(exc)})

    @app.exception_handler(ImageOcrError)
    async def handle_image_ocr_error(_: Request, exc: ImageOcrError) -> JSONResponse:
        # OCR/Embedding 这类上游依赖错误，按 502 暴露更贴近网关/上游失败语义。
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(EmbeddingError)
    async def handle_embedding_error(_: Request, exc: EmbeddingError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(VectorStoreError)
    async def handle_vector_store_error(_: Request, exc: VectorStoreError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
