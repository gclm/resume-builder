package com.resumebuilder.springaibackend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretRequest;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

@Service
public class RealtimeSessionService {

    private static final Logger log = LoggerFactory.getLogger(RealtimeSessionService.class);

    private final ObjectMapper objectMapper;
    private final RestClient restClient;
    private final String realtimeApiKey;
    private final String clientSecretsPath;
    private final String realtimeApiBaseUrl;
    private final String realtimeCallsPath;
    private final String defaultModel;
    private final String defaultLanguage;

    public RealtimeSessionService(
            ObjectMapper objectMapper,
            @Value("${spring.ai.openai.realtime.base-url:${OPENAI_REALTIME_BASE_URL:${OPENAI_BASE_URL:https://api.openai.com}}}") String realtimeBaseUrl,
            @Value("${spring.ai.openai.realtime.api-key:${OPENAI_REALTIME_API_KEY:${OPENAI_API_KEY:}}}") String realtimeApiKey,
            @Value("${spring.ai.openai.realtime.client-secrets-path:${OPENAI_REALTIME_CLIENT_SECRETS_PATH:/v1/realtime/client_secrets}}") String clientSecretsPath,
            @Value("${spring.ai.openai.realtime.calls-path:${OPENAI_REALTIME_CALLS_PATH:/v1/realtime/calls}}") String realtimeCallsPath,
            @Value("${spring.ai.openai.realtime.transcription-model:${OPENAI_REALTIME_TRANSCRIPTION_MODEL:gpt-4o-transcribe}}") String defaultModel,
            @Value("${spring.ai.openai.realtime.language:${OPENAI_REALTIME_LANGUAGE:zh}}") String defaultLanguage
    ) {
        this.objectMapper = objectMapper;
        this.realtimeApiBaseUrl = normalizeBaseUrl(realtimeBaseUrl);
        this.restClient = RestClient.builder().baseUrl(this.realtimeApiBaseUrl).build();
        this.realtimeApiKey = safeText(realtimeApiKey);
        this.clientSecretsPath = normalizePath(clientSecretsPath, "/v1/realtime/client_secrets");
        this.realtimeCallsPath = normalizePath(realtimeCallsPath, "/v1/realtime/calls");
        this.defaultModel = safeText(defaultModel);
        this.defaultLanguage = safeText(defaultLanguage);
    }

    public RealtimeClientSecretResponse createClientSecret(RealtimeClientSecretRequest request) {
        if (!StringUtils.hasText(this.realtimeApiKey)) {
            throw new IllegalStateException("Realtime API key is not configured");
        }

        String model = StringUtils.hasText(request.model()) ? safeText(request.model()) : this.defaultModel;
        if (!StringUtils.hasText(model)) {
            throw new IllegalStateException("Realtime transcription model is not configured");
        }

        String language = StringUtils.hasText(request.language()) ? safeText(request.language()) : this.defaultLanguage;

        Map<String, Object> transcription = new LinkedHashMap<>();
        transcription.put("model", model);
        if (StringUtils.hasText(language)) {
            transcription.put("language", language);
        }

        Map<String, Object> input = new LinkedHashMap<>();
        input.put("transcription", transcription);

        Map<String, Object> audio = new LinkedHashMap<>();
        audio.put("input", input);

        Map<String, Object> session = new LinkedHashMap<>();
        session.put("type", "transcription");
        session.put("audio", audio);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("session", session);

        String rawResponse;
        try {
            rawResponse = restClient.post()
                    .uri(this.clientSecretsPath)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + this.realtimeApiKey)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(String.class);
        } catch (Exception ex) {
            String message = "Create realtime client secret failed at " + this.realtimeApiBaseUrl + this.clientSecretsPath;
            log.error(message, ex);
            throw new IllegalStateException(message, ex);
        }

        return parseResponse(rawResponse, model);
    }

    private RealtimeClientSecretResponse parseResponse(String rawResponse, String fallbackModel) {
        try {
            JsonNode root = objectMapper.readTree(safeText(rawResponse));

            JsonNode clientSecretNode = root.path("client_secret");
            String clientSecret = safeText(clientSecretNode.path("value").asText());
            if (!StringUtils.hasText(clientSecret)) {
                clientSecret = safeText(root.path("value").asText());
            }
            if (!StringUtils.hasText(clientSecret)) {
                throw new IllegalStateException("Realtime provider did not return a client secret");
            }

            Long expiresAt = null;
            if (clientSecretNode.path("expires_at").canConvertToLong()) {
                expiresAt = clientSecretNode.path("expires_at").asLong();
            } else if (root.path("expires_at").canConvertToLong()) {
                expiresAt = root.path("expires_at").asLong();
            }

            String model = safeText(root.path("session").path("audio").path("input").path("transcription").path("model").asText());
            if (!StringUtils.hasText(model)) {
                model = safeText(root.path("session").path("model").asText());
            }
            if (!StringUtils.hasText(model)) {
                model = fallbackModel;
            }

            return new RealtimeClientSecretResponse(
                    clientSecret,
                    expiresAt,
                    model,
                    this.realtimeApiBaseUrl,
                    this.realtimeCallsPath
            );
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to parse realtime session response", ex);
        }
    }

    private String normalizeBaseUrl(String baseUrl) {
        if (!StringUtils.hasText(baseUrl)) {
            return "https://api.openai.com";
        }
        return baseUrl.trim().replaceAll("/+$", "");
    }

    private String normalizePath(String path, String fallback) {
        String target = StringUtils.hasText(path) ? path.trim() : fallback;
        return target.startsWith("/") ? target : "/" + target;
    }

    private String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
