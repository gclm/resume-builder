-- author: jf
-- 手工执行：用于知识库 chunk 与向量存储。
-- 当前 Python 后端已经改成真实写入 PostgreSQL + pgvector。
-- 这里将 embedding 列定义为不固定维度的 vector，
-- 以兼容 text-embedding-3-small(1536) 与 text-embedding-3-large(3072)。
-- 默认检索走精确 cosine search；如后续固定到单一模型，可再按模型维度补 ANN 索引。
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_document_chunks (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    original_content_type VARCHAR(255) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    ingest_source VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model VARCHAR(128) NOT NULL DEFAULT '',
    embedding_dimensions INTEGER NOT NULL DEFAULT 0,
    embedding vector NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(128) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER NOT NULL DEFAULT 0;

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding TYPE vector
    USING embedding::vector;

UPDATE rag_document_chunks
SET embedding_model = 'text-embedding-3-small'
WHERE COALESCE(embedding_model, '') = '';

UPDATE rag_document_chunks
SET embedding_dimensions = vector_dims(embedding)
WHERE COALESCE(embedding_dimensions, 0) <= 0;

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding_model DROP DEFAULT;

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding_dimensions DROP DEFAULT;

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_source_id
    ON rag_document_chunks (source_id);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_created_at
    ON rag_document_chunks (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_metadata
    ON rag_document_chunks
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_profile
    ON rag_document_chunks (embedding_model, embedding_dimensions);
