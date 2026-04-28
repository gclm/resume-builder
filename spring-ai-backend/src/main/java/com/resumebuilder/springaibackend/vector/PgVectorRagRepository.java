// author: jf
package com.resumebuilder.springaibackend.vector;

import com.resumebuilder.springaibackend.dto.RagSource;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.ai.vectorstore.filter.FilterExpressionBuilder;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Repository;

@Repository
public class PgVectorRagRepository {

    private final VectorStore ragVectorStore;

    public PgVectorRagRepository(@Qualifier("ragVectorStore") VectorStore ragVectorStore) {
        this.ragVectorStore = ragVectorStore;
    }

    public int saveChunks(List<StoredRagChunk> chunks, String embeddingModelName) {
        if (chunks == null || chunks.isEmpty()) {
            return 0;
        }

        String safeEmbeddingModel = safeText(embeddingModelName);
        List<Document> documents = new ArrayList<>(chunks.size());
        for (StoredRagChunk chunk : chunks) {
            documents.add(Document.builder()
                    .id(buildDocumentId(chunk))
                    .text(chunk.content())
                    .metadata(buildMetadata(chunk, safeEmbeddingModel))
                    .build());
        }
        ragVectorStore.add(documents);
        return documents.size();
    }

    public List<RagSource> similaritySearch(String query, String embeddingModelName, int topK) {
        String safeQuery = safeText(query);
        if (safeQuery.isBlank()) {
            return List.of();
        }

        int safeTopK = Math.max(1, topK);
        String safeEmbeddingModel = safeText(embeddingModelName);
        SearchRequest.Builder requestBuilder = SearchRequest.builder()
                .query(safeQuery)
                .topK(safeTopK)
                .similarityThresholdAll();
        if (!safeEmbeddingModel.isBlank()) {
            FilterExpressionBuilder filterBuilder = new FilterExpressionBuilder();
            requestBuilder.filterExpression(filterBuilder.eq("embeddingModel", safeEmbeddingModel).build());
        }

        List<Document> documents = ragVectorStore.similaritySearch(requestBuilder.build());
        List<RagSource> sources = new ArrayList<>(documents.size());
        for (Document document : documents) {
            Map<String, Object> metadata = document.getMetadata() == null
                    ? new LinkedHashMap<>()
                    : new LinkedHashMap<>(document.getMetadata());
            metadata.put("topK", safeTopK);
            metadata.put("engine", "spring-ai-pgvector");
            metadata.put("pgvectorAvailable", true);
            if (!safeEmbeddingModel.isBlank()) {
                metadata.put("embeddingModel", safeEmbeddingModel);
            }
            Double similarity = resolveSimilarity(document, metadata);
            if (similarity != null) {
                metadata.put("similarity", similarity);
            }
            sources.add(new RagSource(
                    resolveSourceId(document, metadata),
                    safeText(document.getText()),
                    metadata
            ));
        }
        return sources;
    }

    private Map<String, Object> buildMetadata(StoredRagChunk chunk, String embeddingModelName) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        if (chunk.metadata() != null) {
            metadata.putAll(chunk.metadata());
        }
        metadata.put("sourceId", chunk.sourceId());
        metadata.put("originalFilename", chunk.originalFilename());
        metadata.put("originalContentType", chunk.originalContentType());
        metadata.put("sourceType", chunk.sourceType());
        metadata.put("ingestSource", chunk.ingestSource());
        metadata.put("chunkIndex", chunk.chunkIndex());
        metadata.put("embeddingModel", embeddingModelName);
        return metadata;
    }

    private static String buildDocumentId(StoredRagChunk chunk) {
        return safeText(chunk.sourceId()) + "-" + chunk.chunkIndex();
    }

    private static Double resolveSimilarity(Document document, Map<String, Object> metadata) {
        if (document.getScore() != null) {
            return document.getScore();
        }
        Object distance = metadata.get("distance");
        if (distance instanceof Number number) {
            return 1.0D - number.doubleValue();
        }
        return null;
    }

    private static String resolveSourceId(Document document, Map<String, Object> metadata) {
        Object sourceId = metadata.get("sourceId");
        String safeSourceId = sourceId == null ? "" : sourceId.toString().trim();
        return safeSourceId.isBlank() ? safeText(document.getId()) : safeSourceId;
    }

    private static String safeText(String value) {
        return value == null ? "" : value.trim();
    }

    public record StoredRagChunk(
            String sourceId,
            int chunkIndex,
            String originalFilename,
            String originalContentType,
            String sourceType,
            String ingestSource,
            String content,
            Map<String, Object> metadata
    ) {
    }
}
