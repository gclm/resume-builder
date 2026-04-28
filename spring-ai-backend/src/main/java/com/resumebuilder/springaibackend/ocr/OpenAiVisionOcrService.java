// author: jf
package com.resumebuilder.springaibackend.ocr;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.client.OpenAiRestClientSupport;
import java.time.Duration;
import java.util.Base64;
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
public class OpenAiVisionOcrService {

    private static final String OCR_PROMPT = """
            你是严格的 OCR 文字提取助手。
            请只提取图片中清晰可见的文字内容。
            不要猜测、补全或编造缺失内容。
            只返回纯文本，不要返回代码块、列表标记或任何额外说明。
            """;

    private final ObjectMapper objectMapper;
    private final RestClient restClient;
    private final String apiKey;
    private final String apiBaseUrl;
    private final String completionsPath;
    private final String modelName;
    private final String detail;

    public OpenAiVisionOcrService(
            ObjectMapper objectMapper,
            @Value("${spring.ai.openai.vision.base-url:${OPENAI_VISION_BASE_URL:${OPENAI_BASE_URL:https://api.openai.com}}}") String baseUrl,
            @Value("${spring.ai.openai.vision.api-key:${OPENAI_VISION_API_KEY:${OPENAI_API_KEY:}}}") String apiKey,
            @Value("${spring.ai.openai.vision.chat-completions-path:${OPENAI_VISION_CHAT_COMPLETIONS_PATH:/v1/chat/completions}}") String completionsPath,
            @Value("${spring.ai.openai.vision.model:${OPENAI_VISION_MODEL:gpt-4.1}}") String modelName,
            @Value("${spring.ai.openai.vision.detail:${OPENAI_VISION_DETAIL:high}}") String detail,
            @Value("${spring.ai.openai.vision.timeout-seconds:${OPENAI_VISION_TIMEOUT_SECONDS:40}}") Integer timeoutSeconds
    ) {
        this.objectMapper = objectMapper;
        this.apiKey = safeText(apiKey);
        this.apiBaseUrl = OpenAiRestClientSupport.normalizeBaseUrl(baseUrl);
        this.completionsPath = OpenAiRestClientSupport.normalizeEndpointPath(
                this.apiBaseUrl,
                completionsPath,
                "/v1/chat/completions"
        );
        this.modelName = safeText(modelName).isBlank() ? "gpt-4.1" : safeText(modelName);
        this.detail = safeText(detail).isBlank() ? "high" : safeText(detail);
        this.restClient = RestClient.builder()
                .baseUrl(this.apiBaseUrl)
                .requestFactory(requestFactory(timeoutSeconds))
                .build();
    }

    public String extractMarkdown(byte[] imageBytes, String fileName, String contentType) {
        if (imageBytes == null || imageBytes.length == 0) {
            throw new IllegalArgumentException("图片文件不能为空");
        }
        if (!StringUtils.hasText(apiKey)) {
            throw new IllegalStateException("OPENAI_VISION_API_KEY 或 OPENAI_API_KEY 未配置，无法执行图片 OCR");
        }

        Map<String, Object> imageUrl = new LinkedHashMap<>();
        imageUrl.put("url", toDataUrl(imageBytes, fileName, contentType));
        imageUrl.put("detail", detail);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("messages", List.of(Map.of(
                "role", "user",
                "content", List.of(
                        Map.of("type", "text", "text", OCR_PROMPT),
                        Map.of("type", "image_url", "image_url", imageUrl)
                )
        )));

        String rawResponse;
        try {
            rawResponse = restClient.post()
                    .uri(completionsPath)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + apiKey)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(String.class);
        } catch (RestClientResponseException ex) {
            throw new IllegalStateException(
                    OpenAiRestClientSupport.buildResponseExceptionMessage(objectMapper, "图片 OCR 请求", endpoint(), ex),
                    ex
            );
        } catch (RestClientException ex) {
            throw new IllegalStateException("图片 OCR 请求失败: " + safeText(ex.getMessage()), ex);
        }

        String extractedText = parseContent(rawResponse);
        if (!StringUtils.hasText(extractedText)) {
            throw new IllegalStateException("图片 OCR 未返回可入库文本");
        }
        return extractedText;
    }

    private String parseContent(String rawResponse) {
        try {
            JsonNode root = objectMapper.readTree(safeText(rawResponse));
            String chatContent = parseChatCompletionsContent(root);
            if (StringUtils.hasText(chatContent)) {
                return chatContent;
            }
            return parseResponsesContent(root);
        } catch (Exception ex) {
            throw new IllegalStateException("解析图片 OCR 响应失败: " + ex.getMessage(), ex);
        }
    }

    private String parseChatCompletionsContent(JsonNode root) {
        StringBuilder builder = new StringBuilder();
        JsonNode choices = root.path("choices");
        if (!choices.isArray() || choices.isEmpty()) {
            return "";
        }
        JsonNode content = choices.get(0).path("message").path("content");
        if (content.isTextual()) {
            return content.asText("").trim();
        }
        if (content.isArray()) {
            appendContentArrayText(builder, content);
            return builder.toString().trim();
        }
        return "";
    }

    private String parseResponsesContent(JsonNode root) {
        String outputText = safeText(root.path("output_text").asText(""));
        if (StringUtils.hasText(outputText)) {
            return outputText;
        }

        StringBuilder builder = new StringBuilder();
        JsonNode output = root.path("output");
        if (!output.isArray()) {
            return "";
        }
        for (JsonNode outputItem : output) {
            appendText(builder, outputItem.path("text").asText(""));
            JsonNode content = outputItem.path("content");
            if (content.isArray()) {
                appendContentArrayText(builder, content);
            }
        }
        return builder.toString().trim();
    }

    private void appendContentArrayText(StringBuilder builder, JsonNode content) {
        for (JsonNode item : content) {
            JsonNode textNode = item.path("text");
            if (textNode.isTextual()) {
                appendText(builder, textNode.asText(""));
            } else if (textNode.isObject()) {
                appendText(builder, textNode.path("value").asText(""));
            }
        }
    }

    private void appendText(StringBuilder builder, String text) {
        String safeText = safeText(text);
        if (!safeText.isBlank()) {
            if (!builder.isEmpty()) {
                builder.append('\n');
            }
            builder.append(safeText);
        }
    }

    private String endpoint() {
        return apiBaseUrl + completionsPath;
    }

    private static String toDataUrl(byte[] imageBytes, String fileName, String contentType) {
        String mediaType = guessMediaType(fileName, contentType);
        return "data:" + mediaType + ";base64," + Base64.getEncoder().encodeToString(imageBytes);
    }

    private static String guessMediaType(String fileName, String contentType) {
        String normalizedType = safeText(contentType).toLowerCase();
        if (!normalizedType.isBlank()) {
            return normalizedType;
        }
        String normalizedName = safeText(fileName).toLowerCase();
        if (normalizedName.endsWith(".png")) {
            return "image/png";
        }
        if (normalizedName.endsWith(".webp")) {
            return "image/webp";
        }
        return "image/jpeg";
    }

    private static SimpleClientHttpRequestFactory requestFactory(Integer timeoutSeconds) {
        int seconds = Math.max(3, timeoutSeconds == null ? 40 : timeoutSeconds);
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(seconds));
        factory.setReadTimeout(Duration.ofSeconds(seconds));
        return factory;
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
