package com.resumebuilder.springaibackend.service;

import com.resumebuilder.springaibackend.config.AppProperties;
import com.resumebuilder.springaibackend.dto.RagDocumentInput;
import com.resumebuilder.springaibackend.dto.RagIngestRequest;
import com.resumebuilder.springaibackend.dto.RagQueryRequest;
import com.resumebuilder.springaibackend.dto.RagQueryResponse;
import com.resumebuilder.springaibackend.dto.RagSource;
import com.resumebuilder.springaibackend.cleaner.ResumeMarkdownCleaner;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;
import reactor.core.Disposable;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

@Service
// author: jf
public class AiGatewayService {

    private static final String RAG_SYSTEM_PROMPT = """
            你是一个有帮助的助手。
            请严格基于提供的上下文回答用户问题。
            如果上下文不足，请明确说明缺少哪些信息。
            请保持回答简洁、准确。
            """;

    private final ChatClient chatClient;
    private final VectorStore vectorStore;
    private final AppProperties appProperties;
    private final ResumeMarkdownCleaner resumeMarkdownCleaner;

    public AiGatewayService(
            ChatClient chatClient,
            VectorStore vectorStore,
            AppProperties appProperties,
            ResumeMarkdownCleaner resumeMarkdownCleaner
    ) {
        this.chatClient = chatClient;
        this.vectorStore = vectorStore;
        this.appProperties = appProperties;
        this.resumeMarkdownCleaner = resumeMarkdownCleaner;
    }

    public String chat(String message) {
        return chat(message, false);
    }

    public String chat(String message, boolean sanitizeOutput) {
        String content = chatClient.prompt().user(message.trim()).call().content();
        String safe = resumeMarkdownCleaner.safeContent(content);
        return sanitizeOutput ? resumeMarkdownCleaner.sanitizeResumeMarkdown(safe) : safe;
    }

    public Flux<String> streamChat(String message) {
        return chatClient.prompt().user(message.trim()).stream().content();
    }

    public Flux<String> streamChatWithSink(String message) {
        return streamChatWithSink(message, false);
    }

    public Flux<String> streamChatWithSink(String message, boolean sanitizeOutput) {
        Sinks.Many<String> sink = Sinks.many().unicast().onBackpressureBuffer();

        if (!sanitizeOutput) {
            Disposable disposable = chatClient.prompt()
                    .user(message.trim())
                    .stream()
                    .content()
                    .subscribe(
                            sink::tryEmitNext,
                            sink::tryEmitError,
                            sink::tryEmitComplete
                    );
            return sink.asFlux().doFinally(signalType -> disposable.dispose());
        }

        StringBuilder rawBuffer = new StringBuilder();
        int[] emittedLength = {0};

        Disposable disposable = chatClient.prompt()
                .user(message.trim())
                .stream()
                .content()
                .subscribe(
                        chunk -> {
                            rawBuffer.append(chunk);
                            String sanitized = resumeMarkdownCleaner.sanitizeResumeMarkdown(rawBuffer.toString());
                            int stableEnd = sanitized.lastIndexOf('\n');
                            if (stableEnd < 0) {
                                return;
                            }
                            int emitUntil = stableEnd + 1;
                            if (emitUntil > emittedLength[0]) {
                                sink.tryEmitNext(sanitized.substring(emittedLength[0], emitUntil));
                                emittedLength[0] = emitUntil;
                            }
                        },
                        sink::tryEmitError,
                        () -> {
                            String sanitized = resumeMarkdownCleaner.sanitizeResumeMarkdown(rawBuffer.toString());
                            if (sanitized.length() > emittedLength[0]) {
                                sink.tryEmitNext(sanitized.substring(emittedLength[0]));
                            }
                            sink.tryEmitComplete();
                        }
                );
        return sink.asFlux().doFinally(signalType -> disposable.dispose());
    }

    public int ingestDocuments(RagIngestRequest request) {
        List<Document> documents = request.documents().stream()
                .map(this::toDocument)
                .toList();

        vectorStore.add(documents);
        return documents.size();
    }

    public RagQueryResponse ragQuery(RagQueryRequest request) {
        String queryText = request.query().trim();
        int topK = request.topK() != null && request.topK() > 0 ? request.topK() : appProperties.getRagTopK();

        SearchRequest searchRequest = SearchRequest.builder()
                .query(queryText)
                .topK(topK)
                .build();

        List<Document> matches = vectorStore.similaritySearch(searchRequest);
        List<Document> nonNullMatches = matches == null ? List.of() : matches.stream().filter(Objects::nonNull).toList();

        String context = buildContext(nonNullMatches);
        String answer = resumeMarkdownCleaner.safeContent(
                chatClient.prompt()
                        .system(RAG_SYSTEM_PROMPT)
                        .user("问题：\n" + queryText + "\n\n上下文：\n" + context)
                        .call()
                        .content()
        );

        List<RagSource> sources = nonNullMatches.stream()
                .map(this::toRagSource)
                .toList();

        return new RagQueryResponse(answer, sources);
    }

    private Document toDocument(RagDocumentInput input) {
        Map<String, Object> metadata = new HashMap<>();
        if (input.metadata() != null) {
            metadata.putAll(input.metadata());
        }
        if (input.sourceId() != null && !input.sourceId().isBlank()) {
            metadata.put("sourceId", input.sourceId().trim());
        }
        return new Document(input.content().trim(), metadata);
    }

    private RagSource toRagSource(Document document) {
        Map<String, Object> metadata = document.getMetadata() == null
                ? Map.of()
                : Map.copyOf(document.getMetadata());

        Object sourceId = metadata.getOrDefault("sourceId", metadata.getOrDefault("source_id", ""));
        return new RagSource(String.valueOf(sourceId), resumeMarkdownCleaner.safeContent(document.getText()), metadata);
    }

    private String buildContext(List<Document> documents) {
        if (documents.isEmpty()) {
            return "未找到可用上下文。";
        }

        List<String> chunks = new ArrayList<>();
        for (int i = 0; i < documents.size(); i++) {
            Document document = documents.get(i);
            String sourceId = "";
            if (document.getMetadata() != null) {
                Object value = document.getMetadata().getOrDefault("sourceId", document.getMetadata().getOrDefault("source_id", ""));
                sourceId = String.valueOf(value);
            }

            String prefix = sourceId.isBlank() ? "[chunk-" + (i + 1) + "]" : "[" + sourceId + "]";
            chunks.add(prefix + " " + resumeMarkdownCleaner.safeContent(document.getText()));
        }

        return chunks.stream().collect(Collectors.joining("\n\n"));
    }

}
