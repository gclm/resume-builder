package com.resumebuilder.springaibackend.controller;

import java.time.Instant;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * author: jf
 *
 * <p>Docker 健康检查控制器只表达应用进程是否已完成 HTTP 层启动。
 * 这里不访问数据库、向量库或外部 AI，避免健康检查把依赖初始化状态误判为应用不可用。</p>
 */
@RestController
public class HealthController {

    private final Instant bootTime = Instant.now();

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of(
                "status", "UP",
                "service", "spring-ai-backend",
                "bootTime", bootTime.toString()
        );
    }
}
