// author: jf
package com.resumebuilder.springaibackend.dto;

public record RealtimeClientSecretResponse(
        String clientSecret,
        Long expiresAt,
        String model,
        String realtimeApiBaseUrl,
        String realtimeCallsPath,
        String provider,
        String websocketPath,
        Integer sampleRate,
        String language
) {
    public RealtimeClientSecretResponse(
            String clientSecret,
            Long expiresAt,
            String model,
            String realtimeApiBaseUrl,
            String realtimeCallsPath
    ) {
        this(clientSecret, expiresAt, model, realtimeApiBaseUrl, realtimeCallsPath, "openai", null, null, null);
    }
}
