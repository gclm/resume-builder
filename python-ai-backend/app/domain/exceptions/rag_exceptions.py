# author: jf


class RagIngestError(Exception):
    # 统一上传 / 入库链路的基类异常。
    # API 层会根据子类把它们映射到不同 HTTP 状态码。
    """Base error for RAG ingestion failures."""


class UnsupportedFileTypeError(RagIngestError):
    """Raised when upload contains an unsupported file type."""


class FileTooLargeError(RagIngestError):
    """Raised when upload exceeds the configured size limit."""


class FileParseError(RagIngestError):
    """Raised when a file cannot be parsed into text."""


class ImageOcrError(RagIngestError):
    """Raised when OCR provider cannot extract markdown from an image."""


class EmbeddingError(RagIngestError):
    """Raised when embedding provider cannot vectorize extracted chunks."""


class VectorStoreError(RagIngestError):
    """Raised when pgvector storage or retrieval fails."""
