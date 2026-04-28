// author: jf
package com.resumebuilder.springaibackend.realtime;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.config.DashScopeRealtimeAsrProperties;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

@Component
public class DashScopeRealtimeAsrWebSocketHandler extends TextWebSocketHandler {

    private static final String EVENT_SESSION_START = "session.start";

    private static final String EVENT_AUDIO_APPEND = "input_audio_buffer.append";

    private static final String EVENT_SESSION_FINISH = "session.finish";

    private final ObjectMapper objectMapper;

    private final DashScopeRealtimeAsrProperties properties;

    private final HttpClient httpClient;

    private final ConcurrentMap<String, BridgeSession> bridgeSessions = new ConcurrentHashMap<>();

    public DashScopeRealtimeAsrWebSocketHandler(
            ObjectMapper objectMapper,
            DashScopeRealtimeAsrProperties properties
    ) {
        this.objectMapper = objectMapper;
        this.properties = properties;
        this.httpClient = HttpClient.newHttpClient();
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        BridgeSession bridgeSession = bridgeSessions.computeIfAbsent(
                session.getId(),
                ignored -> new BridgeSession(session)
        );
        JsonNode payload = objectMapper.readTree(message.getPayload());
        String eventType = safeText(payload.path("type").asText(""));

        switch (eventType) {
            case EVENT_SESSION_START -> bridgeSession.open(payload);
            case EVENT_AUDIO_APPEND -> bridgeSession.appendAudio(payload.path("audio").asText(""));
            case EVENT_SESSION_FINISH -> bridgeSession.finish();
            default -> bridgeSession.sendError("unsupported_client_event", "不支持的实时语音事件: " + eventType);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        closeBridgeSession(session);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        BridgeSession bridgeSession = bridgeSessions.get(session.getId());
        if (bridgeSession != null) {
            bridgeSession.sendError("client_transport_error", safeText(exception.getMessage()));
        }
        closeBridgeSession(session);
    }

    private void closeBridgeSession(WebSocketSession session) {
        BridgeSession bridgeSession = bridgeSessions.remove(session.getId());
        if (bridgeSession != null) {
            bridgeSession.close();
        }
    }

    private final class BridgeSession {

        private final WebSocketSession clientSession;

        private final AtomicInteger sequence = new AtomicInteger(0);

        private final AtomicBoolean finishSent = new AtomicBoolean(false);

        private volatile WebSocket upstreamSocket;

        private volatile String model;

        private volatile String language;

        BridgeSession(WebSocketSession clientSession) {
            this.clientSession = clientSession;
        }

        void open(JsonNode payload) {
            if (upstreamSocket != null) {
                return;
            }
            if (!StringUtils.hasText(properties.getApiKey())) {
                throw new IllegalStateException("DASHSCOPE_API_KEY 未配置，无法连接 DashScope 实时语音服务");
            }

            this.model = firstText(payload.path("model").asText(""), properties.getModel(), "qwen3-asr-flash-realtime");
            this.language = firstText(payload.path("language").asText(""), properties.getLanguage(), "zh");
            int sampleRate = resolveSampleRate(payload.path("sampleRate"));
            URI uri = buildDashScopeUri(model);

            try {
                upstreamSocket = httpClient.newWebSocketBuilder()
                        .connectTimeout(Duration.ofSeconds(Math.max(1, properties.getOpenTimeoutSeconds())))
                        .header("Authorization", "bearer " + properties.getApiKey())
                        .buildAsync(uri, new DashScopeUpstreamListener(this))
                        .get(Math.max(1, properties.getOpenTimeoutSeconds()), TimeUnit.SECONDS);
                sendSessionUpdate(sampleRate);
            } catch (Exception ex) {
                throw new IllegalStateException("连接 DashScope 实时语音服务失败: " + safeText(ex.getMessage()), ex);
            }
        }

        void appendAudio(String audioBase64) {
            if (!StringUtils.hasText(audioBase64)) {
                return;
            }
            Map<String, Object> event = new LinkedHashMap<>();
            event.put("event_id", newEventId());
            event.put("type", EVENT_AUDIO_APPEND);
            event.put("audio", audioBase64);
            sendJsonToUpstream(event);
        }

        void finish() {
            if (upstreamSocket == null) {
                return;
            }
            if (!finishSent.compareAndSet(false, true)) {
                return;
            }
            Map<String, Object> event = new LinkedHashMap<>();
            event.put("event_id", newEventId());
            event.put("type", EVENT_SESSION_FINISH);
            sendJsonToUpstream(event);
        }

        void close() {
            WebSocket socket = upstreamSocket;
            if (socket != null) {
                finish();
                socket.sendClose(WebSocket.NORMAL_CLOSURE, "client closed");
            }
        }

        void sendProviderPayload(String rawPayload) {
            try {
                JsonNode payload = objectMapper.readTree(rawPayload);
                sendToClient(normalizeProviderPayload(payload));
            } catch (Exception ex) {
                sendError("provider_payload_parse_failed", "解析 DashScope 实时语音事件失败: " + safeText(ex.getMessage()));
            }
        }

        void sendProviderClosed(String message) {
            if (finishSent.get()) {
                Map<String, Object> event = new LinkedHashMap<>();
                event.put("type", "session_closed");
                event.put("sequence", nextSequence());
                event.put("provider", "dashscope");
                sendToClient(event);
                return;
            }
            sendError("provider_connection_closed", message);
        }

        void sendProviderFailed(String message) {
            sendError("provider_connection_failed", message);
        }

        void sendError(String code, String message) {
            Map<String, Object> event = new LinkedHashMap<>();
            event.put("type", "conversation.item.input_audio_transcription.failed");
            event.put("sequence", nextSequence());
            event.put("provider", "dashscope");
            event.put("errorCode", safeText(code));
            event.put("message", StringUtils.hasText(message) ? message : "DashScope 实时语音识别失败");
            sendToClient(event);
        }

        private void sendSessionUpdate(int sampleRate) {
            Map<String, Object> transcription = new LinkedHashMap<>();
            transcription.put("language", language);

            Map<String, Object> turnDetection = new LinkedHashMap<>();
            turnDetection.put("type", "server_vad");
            turnDetection.put("threshold", properties.getVadThreshold());
            turnDetection.put("silence_duration_ms", properties.getVadSilenceDurationMs());

            Map<String, Object> session = new LinkedHashMap<>();
            session.put("input_audio_format", "pcm");
            session.put("sample_rate", sampleRate);
            session.put("input_audio_transcription", transcription);
            session.put("turn_detection", turnDetection);

            Map<String, Object> event = new LinkedHashMap<>();
            event.put("event_id", newEventId());
            event.put("type", "session.update");
            event.put("session", session);
            sendJsonToUpstream(event);

            Map<String, Object> opened = new LinkedHashMap<>();
            opened.put("type", "session_started");
            opened.put("sequence", nextSequence());
            opened.put("provider", "dashscope");
            opened.put("model", model);
            opened.put("language", language);
            sendToClient(opened);
        }

        private Map<String, Object> normalizeProviderPayload(JsonNode payload) {
            String eventType = safeText(payload.path("type").asText(""));
            Map<String, Object> event = new LinkedHashMap<>();
            event.put("sequence", nextSequence());
            event.put("provider", "dashscope");

            if ("session.created".equals(eventType) || "session.updated".equals(eventType)) {
                event.put("type", "session_started");
                event.put("model", model);
                event.put("language", firstText(
                        payload.path("session").path("input_audio_transcription").path("language").asText(""),
                        language
                ));
                return event;
            }

            if ("input_audio_buffer.speech_started".equals(eventType)) {
                event.put("type", eventType);
                event.put("itemId", firstText(payload.path("item_id").asText(""), payload.path("itemId").asText("")));
                return event;
            }

            if ("conversation.item.input_audio_transcription.text".equals(eventType)) {
                event.put("type", eventType);
                event.put("itemId", firstText(payload.path("item_id").asText(""), payload.path("itemId").asText("")));
                event.put("text", extractTranscriptionText(payload));
                event.put("emotion", safeText(payload.path("emotion").asText("")));
                return event;
            }

            if ("conversation.item.input_audio_transcription.completed".equals(eventType)) {
                event.put("type", eventType);
                event.put("itemId", firstText(payload.path("item_id").asText(""), payload.path("itemId").asText("")));
                event.put("transcript", extractTranscriptionText(payload));
                event.put("segment", extractTranscriptionText(payload));
                event.put("emotion", safeText(payload.path("emotion").asText("")));
                return event;
            }

            if ("conversation.item.input_audio_transcription.failed".equals(eventType) || "error".equals(eventType)) {
                event.put("type", "conversation.item.input_audio_transcription.failed");
                event.put("message", firstText(
                        payload.path("message").asText(""),
                        payload.path("error").path("message").asText(""),
                        "DashScope 实时语音识别失败"
                ));
                event.put("errorCode", firstText(
                        payload.path("code").asText(""),
                        payload.path("error").path("code").asText("")
                ));
                return event;
            }

            if ("session.finished".equals(eventType)) {
                event.put("type", "session_closed");
                return event;
            }

            event.put("type", eventType);
            event.put("payload", payload);
            return event;
        }

        private void sendJsonToUpstream(Map<String, Object> event) {
            WebSocket socket = requireSocket();
            try {
                socket.sendText(objectMapper.writeValueAsString(event), true);
            } catch (JsonProcessingException ex) {
                throw new IllegalStateException("序列化 DashScope 实时语音事件失败", ex);
            }
        }

        private WebSocket requireSocket() {
            WebSocket socket = upstreamSocket;
            if (socket == null) {
                throw new IllegalStateException("DashScope 实时语音会话尚未连接");
            }
            return socket;
        }

        private void sendToClient(Map<String, Object> event) {
            if (!clientSession.isOpen()) {
                return;
            }
            try {
                synchronized (clientSession) {
                    clientSession.sendMessage(new TextMessage(objectMapper.writeValueAsString(event)));
                }
            } catch (IOException ex) {
                throw new IllegalStateException("发送实时语音事件到前端失败: " + safeText(ex.getMessage()), ex);
            }
        }

        private int nextSequence() {
            return sequence.incrementAndGet();
        }

        private String newEventId() {
            return "event_" + System.nanoTime() + "_" + nextSequence();
        }
    }

    private static final class DashScopeUpstreamListener implements WebSocket.Listener {

        private final BridgeSession bridgeSession;

        private final StringBuilder textBuffer = new StringBuilder();

        private DashScopeUpstreamListener(BridgeSession bridgeSession) {
            this.bridgeSession = bridgeSession;
        }

        @Override
        public void onOpen(WebSocket webSocket) {
            WebSocket.Listener.super.onOpen(webSocket);
            webSocket.request(1);
        }

        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            textBuffer.append(data);
            if (last) {
                bridgeSession.sendProviderPayload(textBuffer.toString());
                textBuffer.setLength(0);
            }
            webSocket.request(1);
            return null;
        }

        @Override
        public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
            bridgeSession.sendProviderClosed("DashScope 实时语音连接关闭: " + statusCode + " " + safeText(reason));
            return WebSocket.Listener.super.onClose(webSocket, statusCode, reason);
        }

        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            bridgeSession.sendProviderFailed("DashScope 实时语音连接异常: " + safeText(error.getMessage()));
        }
    }

    private URI buildDashScopeUri(String model) {
        String baseUrl = safeText(properties.getBaseUrl()).isBlank()
                ? "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
                : safeText(properties.getBaseUrl()).replaceAll("/+$", "");
        String query = "model=" + URLEncoder.encode(model, StandardCharsets.UTF_8);
        return URI.create(baseUrl + "?" + query);
    }

    private int resolveSampleRate(JsonNode sampleRateNode) {
        if (sampleRateNode != null && sampleRateNode.canConvertToInt()) {
            return Math.max(8000, sampleRateNode.asInt());
        }
        return Math.max(8000, properties.getSampleRate());
    }

    private static String extractTranscriptionText(JsonNode payload) {
        return firstText(
                payload.path("transcript").asText(""),
                payload.path("final_transcript").asText(""),
                payload.path("text").asText(""),
                payload.path("partial_transcript").asText(""),
                payload.path("stash").asText(""),
                payload.path("delta").asText("")
        );
    }

    private static String firstText(String... values) {
        if (values == null) {
            return "";
        }
        for (String value : values) {
            String safeValue = safeText(value);
            if (!safeValue.isBlank()) {
                return safeValue;
            }
        }
        return "";
    }

    private static String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
