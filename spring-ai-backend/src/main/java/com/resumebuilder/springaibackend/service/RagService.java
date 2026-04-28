// author: jf
package com.resumebuilder.springaibackend.service;

import com.resumebuilder.springaibackend.cleaner.ResumeMarkdownCleaner;
import com.resumebuilder.springaibackend.chunking.RagChunkingService;
import com.resumebuilder.springaibackend.config.AppProperties;
import com.resumebuilder.springaibackend.dto.RagDocumentInput;
import com.resumebuilder.springaibackend.dto.RagIngestRequest;
import com.resumebuilder.springaibackend.dto.RagQueryRequest;
import com.resumebuilder.springaibackend.dto.RagQueryResponse;
import com.resumebuilder.springaibackend.dto.RagSource;
import com.resumebuilder.springaibackend.dto.RagUploadFileResult;
import com.resumebuilder.springaibackend.dto.RagUploadResponse;
import com.resumebuilder.springaibackend.embedding.EmbeddingService;
import com.resumebuilder.springaibackend.parser.RagDocumentParserService;
import com.resumebuilder.springaibackend.vector.PgVectorRagRepository;
import com.resumebuilder.springaibackend.vector.PgVectorRagRepository.StoredRagChunk;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Service
public class RagService {

    private static final String RAG_SYSTEM_PROMPT = """
            你是服务简历优化与面试准备的知识库问答助手。
            请严格基于提供的上下文回答用户问题。
            如果上下文不足，请明确说明缺少哪些信息。
            回答要简洁、准确，并优先保留对求职和面试有价值的细节。
            """;

    private final ChatClient chatClient;
    private final AppProperties appProperties;
    private final ResumeMarkdownCleaner resumeMarkdownCleaner;
    private final RagDocumentParserService documentParserService;
    private final RagChunkingService ragChunkingService;
    private final EmbeddingService embeddingService;
    private final PgVectorRagRepository ragRepository;

    public RagService(
            ChatClient chatClient,
            AppProperties appProperties,
            ResumeMarkdownCleaner resumeMarkdownCleaner,
            RagDocumentParserService documentParserService,
            RagChunkingService ragChunkingService,
            EmbeddingService embeddingService,
            PgVectorRagRepository ragRepository
    ) {
        this.chatClient = chatClient;
        this.appProperties = appProperties;
        this.resumeMarkdownCleaner = resumeMarkdownCleaner;
        this.documentParserService = documentParserService;
        this.ragChunkingService = ragChunkingService;
        this.embeddingService = embeddingService;
        this.ragRepository = ragRepository;
    }

    public int ingestDocuments(RagIngestRequest request) {
        List<RagDocumentInput> documents = request.documents() == null ? List.of() : request.documents();
        int inserted = 0;
        for (int i = 0; i < documents.size(); i++) {
            RagDocumentInput input = documents.get(i);
            String content = safeText(input.content());
            if (!StringUtils.hasText(content)) {
                continue;
            }
            String sourceId = StringUtils.hasText(input.sourceId()) ? input.sourceId().trim() : "doc-" + (i + 1);
            Map<String, Object> metadata = input.metadata() == null ? Map.of() : input.metadata();
            RagDocumentParserService.ParsedRagDocument document = new RagDocumentParserService.ParsedRagDocument(
                    sourceId,
                    sourceId + ".txt",
                    "text/plain",
                    "document",
                    "text_document",
                    content
            );
            inserted += storeDocument(document, metadata);
        }
        return inserted;
    }

    public RagUploadResponse uploadFiles(List<MultipartFile> files) {
        List<MultipartFile> safeFiles = files == null ? List.of() : files;
        if (safeFiles.isEmpty()) {
            throw new IllegalArgumentException("至少需要上传一个文件");
        }

        List<RagUploadFileResult> results = new ArrayList<>();
        int inserted = 0;
        for (MultipartFile file : safeFiles) {
            String fileName = safeFileName(file);
            String contentType = StringUtils.hasText(file.getContentType())
                    ? file.getContentType().trim()
                    : "application/octet-stream";
            String sourceType = detectSourceType(fileName);
            String ingestSource = "image".equals(sourceType) ? "image_ocr_text" : "text_document";

            try {
                // 上传流水线的业务边界：
                // controller 只接收 multipart，service 负责逐文件解析、OCR、切块，并交给 Spring AI VectorStore 向量化入库。
                // 单个文件失败时返回 failed 结果，不影响同批次其他文件继续入库。
                RagDocumentParserService.ParsedRagDocument document = documentParserService.parse(
                        file,
                        appProperties.getRagMaxFileSizeMb()
                );
                int insertedCount = storeDocument(document, Map.of());
                inserted += insertedCount;
                int chunkCount = insertedCount;
                results.add(new RagUploadFileResult(
                        fileName,
                        contentType,
                        document.sourceType(),
                        document.ingestSource(),
                        chunkCount,
                        insertedCount,
                        "success",
                        null
                ));
            } catch (Exception ex) {
                results.add(new RagUploadFileResult(
                        fileName,
                        contentType,
                        sourceType,
                        ingestSource,
                        0,
                        0,
                        "failed",
                        safeText(ex.getMessage())
                ));
            }
        }

        int succeededFiles = (int) results.stream().filter(item -> "success".equals(item.status())).count();
        return new RagUploadResponse(
                safeFiles.size(),
                succeededFiles,
                safeFiles.size() - succeededFiles,
                inserted,
                results
        );
    }

    public RagQueryResponse ragQuery(RagQueryRequest request) {
        String queryText = safeText(request.query());
        int topK = request.topK() != null && request.topK() > 0 ? request.topK() : appProperties.getRagTopK();
        List<RagSource> sources = searchSources(queryText, topK);
        String context = buildContext(sources);
        String answer = resumeMarkdownCleaner.safeContent(
                chatClient.prompt()
                        .system(RAG_SYSTEM_PROMPT)
                        .user("问题：\n" + queryText + "\n\n上下文：\n" + context)
                        .call()
                        .content()
        );
        return new RagQueryResponse(answer, sources);
    }

    public List<RagSource> searchSources(String query, int topK) {
        String safeQuery = safeText(query);
        if (!StringUtils.hasText(safeQuery)) {
            return List.of();
        }
        return ragRepository.similaritySearch(safeQuery, embeddingService.getModelName(), Math.max(1, topK));
    }

    public String buildContext(List<RagSource> sources) {
        List<RagSource> safeSources = sources == null ? List.of() : sources;
        if (safeSources.isEmpty()) {
            return "未找到可用上下文。";
        }
        List<String> chunks = new ArrayList<>();
        for (int i = 0; i < safeSources.size(); i++) {
            RagSource source = safeSources.get(i);
            String sourceId = safeText(source.sourceId());
            String prefix = sourceId.isBlank() ? "[chunk-" + (i + 1) + "]" : "[" + sourceId + "]";
            chunks.add(prefix + " " + resumeMarkdownCleaner.safeContent(source.content()));
        }
        return String.join("\n\n", chunks);
    }

    private int storeDocument(RagDocumentParserService.ParsedRagDocument document, Map<String, Object> extraMetadata) {
        List<RagChunkingService.RagChunk> chunks = ragChunkingService.chunk(
                document,
                appProperties.getRagChunkSize(),
                appProperties.getRagChunkOverlap()
        );
        if (chunks.isEmpty()) {
            throw new IllegalArgumentException("文件未切分出有效 chunk");
        }

        List<StoredRagChunk> storedChunks = new ArrayList<>();
        for (int i = 0; i < chunks.size(); i++) {
            RagChunkingService.RagChunk chunk = chunks.get(i);
            Map<String, Object> metadata = new LinkedHashMap<>();
            if (extraMetadata != null) {
                metadata.putAll(extraMetadata);
            }
            metadata.put("originalFilename", document.originalFilename());
            metadata.put("originalContentType", document.originalContentType());
            metadata.put("sourceType", document.sourceType());
            metadata.put("ingestSource", document.ingestSource());
            metadata.put("chunkIndex", chunk.chunkIndex());
            storedChunks.add(new StoredRagChunk(
                    document.sourceId(),
                    chunk.chunkIndex(),
                    document.originalFilename(),
                    document.originalContentType(),
                    document.sourceType(),
                    document.ingestSource(),
                    chunk.content(),
                    metadata
            ));
        }
        return ragRepository.saveChunks(storedChunks, embeddingService.getModelName());
    }

    private static String detectSourceType(String fileName) {
        String lower = safeText(fileName).toLowerCase(Locale.ROOT);
        return lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".webp")
                ? "image"
                : "document";
    }

    private static String safeFileName(MultipartFile file) {
        String original = file == null ? "" : safeText(file.getOriginalFilename());
        return original.isBlank() ? "upload.bin" : original;
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
