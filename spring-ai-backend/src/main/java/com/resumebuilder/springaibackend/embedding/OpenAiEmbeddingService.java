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
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class OpenAiEmbeddingService implements EmbeddingClient {

    private final ObjectMapper objectMapper;
    private final RestClient restClient;
    private final String apiKey;
    private final String apiBaseUrl;
    private final String embeddingsPath;
    private final String modelName;

    public OpenAiEmbeddingService(
            ObjectMapper objectMapper,
            @Value("${spring.ai.openai.embedding.base-url:${OPENAI_EMBEDDING_BASE_URL:${OPENAI_CHAT_BASE_URL:${OPENAI_BASE_URL:https://api.openai.com}}}}") String baseUrl,
            @Value("${spring.ai.openai.embedding.api-key:${OPENAI_EMBEDDING_API_KEY:${OPENAI_CHAT_API_KEY:${OPENAI_API_KEY:}}}}") String apiKey,
            @Value("${spring.ai.openai.embedding.embeddings-path:${OPENAI_EMBEDDINGS_PATH:/v1/embeddings}}") String embeddingsPath,
            @Value("${spring.ai.openai.embedding.options.model:${OPENAI_EMBEDDING_MODEL:text-embedding-3-large}}") String modelName,
            @Value("${spring.ai.openai.embedding.timeout-seconds:${OPENAI_EMBEDDING_TIMEOUT_SECONDS:20}}") Integer timeoutSeconds
    ) {
        this.objectMapper = objectMapper;
        this.apiKey = safeText(apiKey);
        this.apiBaseUrl = OpenAiRestClientSupport.normalizeBaseUrl(baseUrl);
        this.embeddingsPath = OpenAiRestClientSupport.normalizeEndpointPath(
                this.apiBaseUrl,
                embeddingsPath,
                "/v1/embeddings"
        );
        this.modelName = safeText(modelName).isBlank() ? "text-embedding-3-large" : safeText(modelName);
        this.restClient = RestClient.builder()
                .baseUrl(this.apiBaseUrl)
                .requestFactory(requestFactory(timeoutSeconds))
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
                : texts.stream().map(OpenAiEmbeddingService::safeText).filter(StringUtils::hasText).toList();
        if (normalizedTexts.isEmpty()) {
            return List.of();
        }
        if (!StringUtils.hasText(apiKey)) {
            throw new IllegalStateException("OPENAI_EMBEDDING_API_KEY 或 OPENAI_API_KEY 未配置，无法生成 Embedding");
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", normalizedTexts);
        body.put("encoding_format", "float");

        String rawResponse;
        try {
            rawResponse = restClient.post()
                    .uri(embeddingsPath)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + apiKey)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(String.class);
        } catch (RestClientResponseException ex) {
            throw new IllegalStateException(
                    OpenAiRestClientSupport.buildResponseExceptionMessage(objectMapper, "生成 Embedding 请求", endpoint(), ex),
                    ex
            );
        } catch (RestClientException ex) {
            throw new IllegalStateException("生成 Embedding 请求失败: " + safeText(ex.getMessage()), ex);
        }
        return parseEmbeddings(rawResponse, normalizedTexts.size());
    }

    private String endpoint() {
        return apiBaseUrl + embeddingsPath;
    }

    private List<List<Double>> parseEmbeddings(String rawResponse, int expectedSize) {
        try {
            JsonNode root = objectMapper.readTree(safeText(rawResponse));
            JsonNode dataNode = root.path("data");
            if (!dataNode.isArray()) {
                throw new IllegalStateException("Embedding 响应缺少 data 数组");
            }

            List<List<Double>> embeddings = new ArrayList<>();
            for (int i = 0; i < expectedSize; i++) {
                embeddings.add(null);
            }

            for (JsonNode item : dataNode) {
                int index = item.path("index").canConvertToInt() ? item.path("index").asInt() : embeddings.size();
                JsonNode embeddingNode = item.path("embedding");
                if (!embeddingNode.isArray()) {
                    continue;
                }
                List<Double> vector = new ArrayList<>();
                for (JsonNode valueNode : embeddingNode) {
                    vector.add(valueNode.asDouble());
                }
                if (index >= 0 && index < embeddings.size()) {
                    embeddings.set(index, vector);
                } else {
                    embeddings.add(vector);
                }
            }

            List<List<Double>> normalized = embeddings.stream().filter(item -> item != null && !item.isEmpty()).toList();
            if (normalized.size() != expectedSize) {
                throw new IllegalStateException("Embedding 响应数量与输入文本数量不一致");
            }
            return normalized;
        } catch (Exception ex) {
            throw new IllegalStateException("解析 Embedding 响应失败: " + ex.getMessage(), ex);
        }
    }

    private static SimpleClientHttpRequestFactory requestFactory(Integer timeoutSeconds) {
        int seconds = Math.max(3, timeoutSeconds == null ? 20 : timeoutSeconds);
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(seconds));
        factory.setReadTimeout(Duration.ofSeconds(seconds));
        return factory;
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
