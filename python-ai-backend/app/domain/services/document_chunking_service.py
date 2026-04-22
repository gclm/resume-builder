# author: jf
from app.domain.models.rag_document import ExtractedDocument, RagChunk


class DocumentChunkingService:
    """
    Chunk one logical document with fixed window size and overlap.

    The FAQ-specific logical document split happens upstream. This service only receives
    one already-scoped logical document and turns it into one or more vector chunks.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = max(200, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size // 2))

    def chunk_document(self, document: ExtractedDocument) -> list[RagChunk]:
        normalized_content = self._normalize_content(document.content)
        if not normalized_content:
            return []

        title_raw = str(document.metadata.get("logicalDocumentTitleRaw") or "").strip()
        if title_raw and len(normalized_content) <= self.chunk_size:
            raw_chunks = [normalized_content]
        elif title_raw and normalized_content.startswith(f"{title_raw}\n\n"):
            prefix = f"{title_raw}\n\n"
            body = normalized_content[len(prefix) :].strip()
            if not body:
                raw_chunks = [normalized_content]
            else:
                body_window_size = max(1, self.chunk_size - len(prefix))
                body_overlap = max(0, min(self.chunk_overlap, body_window_size - 1))
                raw_chunks = [f"{prefix}{item}".strip() for item in self._chunk_text(body, body_window_size, body_overlap)]
        else:
            raw_chunks = self._chunk_text(normalized_content, self.chunk_size, self.chunk_overlap)

        chunk_count = len(raw_chunks)
        chunks: list[RagChunk] = []
        for index, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            chunks.append(
                RagChunk(
                    source_id=document.source_id,
                    content=chunk_text,
                    metadata={
                        **document.metadata,
                        "originalFilename": document.original_filename,
                        "originalContentType": document.original_content_type,
                        "sourceType": document.source_type,
                        "ingestSource": document.ingest_source,
                        "logicalDocumentChunkIndex": index,
                        "logicalDocumentChunkCount": chunk_count,
                    },
                )
            )
        return chunks

    @staticmethod
    def _chunk_text(content: str, window_size: int, overlap: int) -> list[str]:
        normalized_content = (content or "").strip()
        if not normalized_content:
            return []

        safe_window_size = max(1, window_size)
        safe_overlap = max(0, min(overlap, safe_window_size - 1))
        chunks: list[str] = []
        start = 0

        while start < len(normalized_content):
            end = min(start + safe_window_size, len(normalized_content))
            chunk_text = normalized_content[start:end].strip()
            if chunk_text:
                chunks.append(chunk_text)
            if end >= len(normalized_content):
                break
            start = max(end - safe_overlap, start + 1)
        return chunks

    @staticmethod
    def _normalize_content(content: str) -> str:
        return (content or "").replace("\r\n", "\n").replace("\r", "\n").strip()
