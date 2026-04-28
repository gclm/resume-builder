// author: jf
package com.resumebuilder.springaibackend.embedding;

import java.util.List;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class EmbeddingService implements EmbeddingClient {

    private final String provider;
    private final OpenAiEmbeddingService openAiEmbeddingService;
    private final OllamaEmbeddingService ollamaEmbeddingService;
    private final int dimensions;

    public EmbeddingService(
            @Value("${app.embedding.provider:${EMBEDDING_PROVIDER:openai}}") String provider,
            @Value("${app.embedding.dimensions:${EMBEDDING_DIMENSIONS:0}}") Integer configuredDimensions,
            OpenAiEmbeddingService openAiEmbeddingService,
            OllamaEmbeddingService ollamaEmbeddingService
    ) {
        this.provider = normalizeProvider(provider);
        this.openAiEmbeddingService = openAiEmbeddingService;
        this.ollamaEmbeddingService = ollamaEmbeddingService;
        this.dimensions = resolveDimensions(configuredDimensions, this.provider, activeClient().getModelName());
    }

    @Override
    public String getModelName() {
        return activeClient().getModelName();
    }

    @Override
    public List<List<Double>> embedTexts(List<String> texts) {
        return activeClient().embedTexts(texts);
    }

    public int getDimensions() {
        return dimensions;
    }

    private EmbeddingClient activeClient() {
        if ("ollama".equals(provider)) {
            return ollamaEmbeddingService;
        }
        return openAiEmbeddingService;
    }

    private static String normalizeProvider(String rawProvider) {
        String safeProvider = rawProvider == null ? "" : rawProvider.trim().toLowerCase(Locale.ROOT);
        if ("ollama".equals(safeProvider)) {
            return "ollama";
        }
        return "openai";
    }

    private static int resolveDimensions(Integer configuredDimensions, String provider, String modelName) {
        if (configuredDimensions != null && configuredDimensions > 0) {
            return configuredDimensions;
        }

        String normalizedModel = normalizeModelName(modelName);
        if ("openai".equals(provider)) {
            return inferOpenAiDimensions(normalizedModel);
        }
        if ("ollama".equals(provider)) {
            return inferOllamaDimensions(normalizedModel);
        }
        return 0;
    }

    private static int inferOpenAiDimensions(String modelName) {
        return switch (modelName) {
            case "text-embedding-3-large" -> 3072;
            case "text-embedding-3-small", "text-embedding-ada-002" -> 1536;
            default -> 0;
        };
    }

    private static int inferOllamaDimensions(String modelName) {
        if ("nomic-embed-text".equals(modelName)) {
            return 768;
        }
        if ("mxbai-embed-large".equals(modelName) || "bge-m3".equals(modelName)) {
            return 1024;
        }
        if (modelName.startsWith("all-minilm")) {
            return 384;
        }
        return 0;
    }

    private static String normalizeModelName(String modelName) {
        String safeModelName = modelName == null ? "" : modelName.trim().toLowerCase(Locale.ROOT);
        return safeModelName.endsWith(":latest")
                ? safeModelName.substring(0, safeModelName.length() - ":latest".length())
                : safeModelName;
    }
}
