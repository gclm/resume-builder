// author: jf
package com.resumebuilder.springaibackend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.client.OpenAiRestClientSupport;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretRequest;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

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
    private final String realtimeAsrProvider;
    private final String dashScopeApiKey;
    private final String dashScopeModel;
    private final String dashScopeLanguage;
    private final int dashScopeSampleRate;

    public RealtimeSessionService(
            ObjectMapper objectMapper,
            @Value("${app.realtime-asr.provider:${REALTIME_ASR_PROVIDER:dashscope}}") String realtimeAsrProvider,
            @Value("${spring.ai.openai.realtime.base-url:${OPENAI_REALTIME_BASE_URL:${OPENAI_BASE_URL:https://api.openai.com}}}") String realtimeBaseUrl,
            @Value("${spring.ai.openai.realtime.api-key:${OPENAI_REALTIME_API_KEY:${OPENAI_API_KEY:}}}") String realtimeApiKey,
            @Value("${spring.ai.openai.realtime.client-secrets-path:${OPENAI_REALTIME_CLIENT_SECRETS_PATH:/v1/realtime/client_secrets}}") String clientSecretsPath,
            @Value("${spring.ai.openai.realtime.calls-path:${OPENAI_REALTIME_CALLS_PATH:/v1/realtime/calls}}") String realtimeCallsPath,
            @Value("${spring.ai.openai.realtime.transcription-model:${OPENAI_REALTIME_TRANSCRIPTION_MODEL:gpt-4o-transcribe}}") String defaultModel,
            @Value("${spring.ai.openai.realtime.language:${OPENAI_REALTIME_LANGUAGE:zh}}") String defaultLanguage,
            @Value("${spring.ai.openai.realtime.timeout-seconds:${OPENAI_REALTIME_TIMEOUT_SECONDS:120}}") Integer timeoutSeconds,
            @Value("${app.realtime-asr.dashscope.api-key:${DASHSCOPE_API_KEY:}}") String dashScopeApiKey,
            @Value("${app.realtime-asr.dashscope.model:${DASHSCOPE_REALTIME_MODEL:qwen3-asr-flash-realtime}}") String dashScopeModel,
            @Value("${app.realtime-asr.dashscope.language:${DASHSCOPE_REALTIME_LANGUAGE:zh}}") String dashScopeLanguage,
            @Value("${app.realtime-asr.dashscope.sample-rate:${DASHSCOPE_REALTIME_SAMPLE_RATE:16000}}") Integer dashScopeSampleRate
    ) {
        this.objectMapper = objectMapper;
        this.realtimeAsrProvider = normalizeProvider(realtimeAsrProvider);
        this.realtimeApiBaseUrl = OpenAiRestClientSupport.normalizeBaseUrl(realtimeBaseUrl);
        this.restClient = RestClient.builder()
                .baseUrl(this.realtimeApiBaseUrl)
                .requestFactory(requestFactory(timeoutSeconds))
                .build();
        this.realtimeApiKey = safeText(realtimeApiKey);
        this.clientSecretsPath = OpenAiRestClientSupport.normalizeEndpointPath(
                this.realtimeApiBaseUrl,
                clientSecretsPath,
                "/v1/realtime/client_secrets"
        );
        this.realtimeCallsPath = OpenAiRestClientSupport.normalizeEndpointPath(
                this.realtimeApiBaseUrl,
                realtimeCallsPath,
                "/v1/realtime/calls"
        );
        this.defaultModel = safeText(defaultModel).isBlank() ? "gpt-4o-transcribe" : safeText(defaultModel);
        this.defaultLanguage = safeText(defaultLanguage).isBlank() ? "zh" : safeText(defaultLanguage);
        this.dashScopeApiKey = safeText(dashScopeApiKey);
        this.dashScopeModel = safeText(dashScopeModel).isBlank() ? "qwen3-asr-flash-realtime" : safeText(dashScopeModel);
        this.dashScopeLanguage = safeText(dashScopeLanguage).isBlank() ? "zh" : safeText(dashScopeLanguage);
        this.dashScopeSampleRate = Math.max(8000, dashScopeSampleRate == null ? 16000 : dashScopeSampleRate);
    }

    public RealtimeClientSecretResponse createClientSecret(RealtimeClientSecretRequest request) {
        RealtimeClientSecretRequest safeRequest = request == null
                ? new RealtimeClientSecretRequest(null, null)
                : request;
        if ("dashscope".equals(this.realtimeAsrProvider)) {
            return createDashScopeSessionDescriptor(safeRequest);
        }
        if (!StringUtils.hasText(this.realtimeApiKey)) {
            throw new IllegalStateException("OPENAI_REALTIME_API_KEY 或 OPENAI_API_KEY 未配置，无法创建 Realtime 临时密钥");
        }

        String model = StringUtils.hasText(safeRequest.model()) ? safeText(safeRequest.model()) : this.defaultModel;
        if (!StringUtils.hasText(model)) {
            throw new IllegalStateException("OPENAI_REALTIME_TRANSCRIPTION_MODEL 未配置，无法创建 Realtime 转写会话");
        }

        String language = StringUtils.hasText(safeRequest.language()) ? safeText(safeRequest.language()) : this.defaultLanguage;

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
        } catch (RestClientResponseException ex) {
            String message = OpenAiRestClientSupport.buildResponseExceptionMessage(
                    objectMapper,
                    "创建 Realtime 临时密钥请求",
                    endpoint(),
                    ex
            );
            log.error(message, ex);
            throw new IllegalStateException(message, ex);
        } catch (RestClientException ex) {
            String message = "创建 Realtime 临时密钥请求失败: " + safeText(ex.getMessage());
            log.error(message, ex);
            throw new IllegalStateException(message, ex);
        }

        return parseResponse(rawResponse, model);
    }

    private RealtimeClientSecretResponse createDashScopeSessionDescriptor(RealtimeClientSecretRequest request) {
        if (!StringUtils.hasText(this.dashScopeApiKey)) {
            throw new IllegalStateException("DASHSCOPE_API_KEY 未配置，无法创建 DashScope 实时语音会话");
        }

        String model = StringUtils.hasText(request.model()) ? safeText(request.model()) : this.dashScopeModel;
        String language = StringUtils.hasText(request.language()) ? safeText(request.language()) : this.dashScopeLanguage;
        return new RealtimeClientSecretResponse(
                "",
                null,
                model,
                "",
                "",
                "dashscope",
                "/ws/ai/realtime-asr",
                this.dashScopeSampleRate,
                language
        );
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
                throw new IllegalStateException("Realtime 服务未返回可用临时密钥");
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
            throw new IllegalStateException("解析 Realtime 会话响应失败", ex);
        }
    }

    private String endpoint() {
        return this.realtimeApiBaseUrl + this.clientSecretsPath;
    }

    private static SimpleClientHttpRequestFactory requestFactory(Integer timeoutSeconds) {
        int seconds = Math.max(3, timeoutSeconds == null ? 120 : timeoutSeconds);
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(seconds));
        factory.setReadTimeout(Duration.ofSeconds(seconds));
        return factory;
    }

    private static String normalizeProvider(String provider) {
        String normalized = safeText(provider).toLowerCase();
        return "openai".equals(normalized) ? "openai" : "dashscope";
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
