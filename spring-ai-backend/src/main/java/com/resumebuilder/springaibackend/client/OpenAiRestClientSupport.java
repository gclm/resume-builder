// author: jf
package com.resumebuilder.springaibackend.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import org.springframework.web.client.RestClientResponseException;

public final class OpenAiRestClientSupport {

    private static final int MAX_UPSTREAM_ERROR_LENGTH = 800;

    private OpenAiRestClientSupport() {
    }

    public static String normalizeBaseUrl(String baseUrl) {
        String raw = safeText(baseUrl);
        return raw.isBlank() ? "https://api.openai.com" : raw.replaceAll("/+$", "");
    }

    public static String normalizeEndpointPath(String normalizedBaseUrl, String path, String fallback) {
        String target = normalizePath(path, fallback);
        if (safeText(normalizedBaseUrl).endsWith("/v1") && target.startsWith("/v1/")) {
            return target.substring("/v1".length());
        }
        return target;
    }

    public static String buildResponseExceptionMessage(
            ObjectMapper objectMapper,
            String action,
            String endpoint,
            RestClientResponseException exception
    ) {
        StringBuilder message = new StringBuilder();
        message.append(action)
                .append("失败: HTTP ")
                .append(exception.getStatusCode().value())
                .append("，endpoint=")
                .append(endpoint);

        String upstreamError = extractUpstreamError(objectMapper, exception.getResponseBodyAsString());
        if (!upstreamError.isBlank()) {
            message.append("，上游错误=").append(upstreamError);
        }
        return message.toString();
    }

    static String safeText(String text) {
        return text == null ? "" : text.trim();
    }

    private static String normalizePath(String path, String fallback) {
        String target = safeText(path).isBlank() ? fallback : safeText(path);
        return target.startsWith("/") ? target : "/" + target;
    }

    private static String extractUpstreamError(ObjectMapper objectMapper, String responseBody) {
        String rawBody = safeText(responseBody);
        if (rawBody.isBlank()) {
            return "";
        }

        try {
            JsonNode root = objectMapper.readTree(rawBody);
            String jsonMessage = extractJsonErrorMessage(root);
            if (!jsonMessage.isBlank()) {
                return limitLength(jsonMessage);
            }
        } catch (Exception ignored) {
            // 上游错误体不一定是 JSON，失败时直接返回压缩后的原文片段。
        }

        return limitLength(rawBody.replaceAll("\\s+", " "));
    }

    private static String extractJsonErrorMessage(JsonNode root) {
        JsonNode error = root.path("error");
        if (error.isTextual()) {
            return safeText(error.asText());
        }
        if (error.isObject()) {
            List<String> parts = new ArrayList<>();
            appendIfPresent(parts, "message", error.path("message").asText(""));
            appendIfPresent(parts, "type", error.path("type").asText(""));
            appendIfPresent(parts, "code", error.path("code").asText(""));
            return String.join("，", parts);
        }

        for (String fieldName : List.of("message", "detail", "error_description")) {
            String message = safeText(root.path(fieldName).asText(""));
            if (!message.isBlank()) {
                return message;
            }
        }
        return "";
    }

    private static void appendIfPresent(List<String> parts, String name, String value) {
        String safeValue = safeText(value);
        if (!safeValue.isBlank()) {
            parts.add(name + "=" + safeValue);
        }
    }

    private static String limitLength(String value) {
        String safeValue = safeText(value);
        if (safeValue.length() <= MAX_UPSTREAM_ERROR_LENGTH) {
            return safeValue;
        }
        return safeValue.substring(0, MAX_UPSTREAM_ERROR_LENGTH) + "...";
    }
}
