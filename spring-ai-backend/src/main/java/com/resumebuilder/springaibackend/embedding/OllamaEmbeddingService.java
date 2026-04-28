// author: jf
package com.resumebuilder.springaibackend.embedding;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.client.OpenAiRestClientSupport;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class OllamaEmbeddingService implements EmbeddingClient {

    private final ObjectMapper objectMapper;
    private final RestClient restClient;
    private final String baseUrl;
    private final String modelName;
    private final int timeoutSeconds;

    public OllamaEmbeddingService(
            ObjectMapper objectMapper,
            @Value("${app.embedding.ollama.base-url:${OLLAMA_EMBEDDING_BASE_URL:${OLLAMA_BASE_URL:http://127.0.0.1:11434}}}") String baseUrl,
            @Value("${app.embedding.ollama.model:${OLLAMA_EMBEDDING_MODEL:nomic-embed-text}}") String modelName,
            @Value("${app.embedding.ollama.timeout-seconds:${OLLAMA_EMBEDDING_TIMEOUT_SECONDS:45}}") Integer timeoutSeconds
    ) {
        this.objectMapper = objectMapper;
        this.baseUrl = normalizeBaseUrl(baseUrl);
        this.modelName = safeText(modelName).isBlank() ? "nomic-embed-text" : safeText(modelName);
        this.timeoutSeconds = Math.max(1, timeoutSeconds == null ? 45 : timeoutSeconds);
        this.restClient = RestClient.builder()
                .baseUrl(this.baseUrl)
                .requestFactory(requestFactory(this.timeoutSeconds))
                .build();
    }

    @Override
    public String getModelName() {
        return modelName;
    }

    @Override
    public List<List<Double>> embedTexts(List<String> texts) {
        List<String> normalizedTexts = texts == null
                ? List.of()
                : texts.stream().map(OllamaEmbeddingService::safeText).filter(StringUtils::hasText).toList();
        if (normalizedTexts.isEmpty()) {
            return List.of();
        }

        ensureModelAvailable();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", normalizedTexts);

        String rawResponse;
        try {
            rawResponse = restClient.post()
                    .uri("/api/embed")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(String.class);
        } catch (RestClientResponseException ex) {
            throw new IllegalStateException(
                    OpenAiRestClientSupport.buildResponseExceptionMessage(objectMapper, "Ollama Embedding 请求", endpoint("/api/embed"), ex),
                    ex
            );
        } catch (RestClientException ex) {
            throw new IllegalStateException("Ollama Embedding 请求失败: " + safeText(ex.getMessage()), ex);
        }

        List<List<Double>> embeddings = parseEmbeddings(rawResponse);
        if (embeddings.size() != normalizedTexts.size()) {
            throw new IllegalStateException("Embedding 返回数量与输入数量不一致");
        }
        return embeddings;
    }

    private void ensureModelAvailable() {
        String rawResponse;
        try {
            rawResponse = restClient.get()
                    .uri("/api/tags")
                    .retrieve()
                    .body(String.class);
        } catch (RestClientResponseException ex) {
            throw new IllegalStateException(
                    OpenAiRestClientSupport.buildResponseExceptionMessage(objectMapper, "检查 Ollama 模型", endpoint("/api/tags"), ex),
                    ex
            );
        } catch (RestClientException ex) {
            throw new IllegalStateException("无法连接 Ollama 服务: " + endpoint("/api/tags") + "，" + safeText(ex.getMessage()), ex);
        }

        if (!hasRequestedModel(rawResponse)) {
            throw new IllegalStateException("Ollama 未发现 embedding 模型 `" + modelName + "`，请先执行 `ollama pull " + modelName + "` 后重试");
        }
    }

    private boolean hasRequestedModel(String rawResponse) {
        try {
            JsonNode models = objectMapper.readTree(safeText(rawResponse)).path("models");
            if (!models.isArray()) {
                return false;
            }
            String requestedModel = normalizeModelName(modelName);
            for (JsonNode item : models) {
                String model = normalizeModelName(item.path("name").asText(""));
                if (requestedModel.equals(model)) {
                    return true;
                }
            }
            return false;
        } catch (Exception ex) {
            throw new IllegalStateException("解析 Ollama 模型列表失败: " + ex.getMessage(), ex);
        }
    }

    private List<List<Double>> parseEmbeddings(String rawResponse) {
        try {
            JsonNode root = objectMapper.readTree(safeText(rawResponse));
            JsonNode embeddingsNode = root.path("embeddings");
            if (embeddingsNode.isArray() && !embeddingsNode.isEmpty()) {
                return parseEmbeddingArray(embeddingsNode);
            }

            JsonNode embeddingNode = root.path("embedding");
            if (embeddingNode.isArray() && !embeddingNode.isEmpty()) {
                return List.of(parseVector(embeddingNode));
            }
            throw new IllegalStateException("Ollama /api/embed 未返回 embeddings");
        } catch (Exception ex) {
            throw new IllegalStateException("解析 Ollama Embedding 响应失败: " + ex.getMessage(), ex);
        }
    }

    private List<List<Double>> parseEmbeddingArray(JsonNode embeddingsNode) {
        List<List<Double>> embeddings = new ArrayList<>();
        for (JsonNode item : embeddingsNode) {
            embeddings.add(parseVector(item));
        }
        return embeddings;
    }

    private List<Double> parseVector(JsonNode vectorNode) {
        if (!vectorNode.isArray() || vectorNode.isEmpty()) {
            throw new IllegalStateException("Embedding 向量为空或格式非法");
        }
        List<Double> vector = new ArrayList<>();
        for (JsonNode item : vectorNode) {
            if (!item.isNumber()) {
                throw new IllegalStateException("Embedding 向量包含非数字值");
            }
            vector.add(item.asDouble());
        }
        return vector;
    }

    private String endpoint(String path) {
        return baseUrl + path;
    }

    private static String normalizeBaseUrl(String baseUrl) {
        String raw = safeText(baseUrl);
        return raw.isBlank() ? "http://127.0.0.1:11434" : raw.replaceAll("/+$", "");
    }

    private static String normalizeModelName(String rawName) {
        String safeName = safeText(rawName);
        return safeName.endsWith(":latest") ? safeName.substring(0, safeName.length() - ":latest".length()) : safeName;
    }

    private static SimpleClientHttpRequestFactory requestFactory(int timeoutSeconds) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(timeoutSeconds));
        factory.setReadTimeout(Duration.ofSeconds(timeoutSeconds));
        return factory;
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
