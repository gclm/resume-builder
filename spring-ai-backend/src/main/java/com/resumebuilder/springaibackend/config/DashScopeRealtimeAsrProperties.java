// author: jf
package com.resumebuilder.springaibackend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.realtime-asr.dashscope")
public class DashScopeRealtimeAsrProperties {

    private String baseUrl = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime";

    private String apiKey = "";

    private String model = "qwen3-asr-flash-realtime";

    private String language = "zh";

    private int sampleRate = 16000;

    private double vadThreshold = 0.2D;

    private int vadSilenceDurationMs = 800;

    private int openTimeoutSeconds = 10;

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public String getApiKey() {
        return apiKey;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public int getSampleRate() {
        return sampleRate;
    }

    public void setSampleRate(int sampleRate) {
        this.sampleRate = sampleRate;
    }

    public double getVadThreshold() {
        return vadThreshold;
    }

    public void setVadThreshold(double vadThreshold) {
        this.vadThreshold = vadThreshold;
    }

    public int getVadSilenceDurationMs() {
        return vadSilenceDurationMs;
    }

    public void setVadSilenceDurationMs(int vadSilenceDurationMs) {
        this.vadSilenceDurationMs = vadSilenceDurationMs;
    }

    public int getOpenTimeoutSeconds() {
        return openTimeoutSeconds;
    }

    public void setOpenTimeoutSeconds(int openTimeoutSeconds) {
        this.openTimeoutSeconds = openTimeoutSeconds;
    }
}
