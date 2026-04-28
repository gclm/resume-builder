// author: jf
package com.resumebuilder.springaibackend.config;

import com.resumebuilder.springaibackend.realtime.DashScopeRealtimeAsrWebSocketHandler;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class RealtimeAsrWebSocketConfig implements WebSocketConfigurer {

    private final AppProperties appProperties;

    private final DashScopeRealtimeAsrWebSocketHandler dashScopeRealtimeAsrWebSocketHandler;

    public RealtimeAsrWebSocketConfig(
            AppProperties appProperties,
            DashScopeRealtimeAsrWebSocketHandler dashScopeRealtimeAsrWebSocketHandler
    ) {
        this.appProperties = appProperties;
        this.dashScopeRealtimeAsrWebSocketHandler = dashScopeRealtimeAsrWebSocketHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(dashScopeRealtimeAsrWebSocketHandler, "/ws/ai/realtime-asr")
                .setAllowedOrigins(appProperties.getCorsAllowedOrigins().toArray(String[]::new));
    }
}
