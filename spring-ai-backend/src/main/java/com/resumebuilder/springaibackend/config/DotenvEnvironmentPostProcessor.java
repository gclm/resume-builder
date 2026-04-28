// author: jf
package com.resumebuilder.springaibackend.config;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.MutablePropertySources;
import org.springframework.core.env.StandardEnvironment;

public class DotenvEnvironmentPostProcessor implements EnvironmentPostProcessor, Ordered {

    private static final String PROPERTY_SOURCE_NAME = "springAiBackendDotenv";

    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        Map<String, Object> dotenvProperties = loadDotenvProperties();
        if (dotenvProperties.isEmpty()) {
            return;
        }

        addSpringAiOpenAiAliases(dotenvProperties);
        MutablePropertySources propertySources = environment.getPropertySources();
        MapPropertySource dotenvPropertySource = new MapPropertySource(PROPERTY_SOURCE_NAME, dotenvProperties);
        if (propertySources.contains(PROPERTY_SOURCE_NAME)) {
            propertySources.replace(PROPERTY_SOURCE_NAME, dotenvPropertySource);
            return;
        }
        if (propertySources.contains(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME)) {
            propertySources.addAfter(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, dotenvPropertySource);
        } else {
            propertySources.addFirst(dotenvPropertySource);
        }
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 20;
    }

    private Map<String, Object> loadDotenvProperties() {
        for (Path candidate : resolveDotenvCandidates()) {
            if (!Files.isRegularFile(candidate)) {
                continue;
            }
            try {
                return parseDotenv(candidate);
            } catch (IOException ignored) {
                return Map.of();
            }
        }
        return Map.of();
    }

    private Set<Path> resolveDotenvCandidates() {
        Set<Path> candidates = new LinkedHashSet<>();
        Path current = Path.of("").toAbsolutePath().normalize();
        Path cursor = current;
        for (int i = 0; i < 6 && cursor != null; i++) {
            candidates.add(cursor.resolve(".env").normalize());
            candidates.add(cursor.resolve("spring-ai-backend").resolve(".env").normalize());
            cursor = cursor.getParent();
        }
        return candidates;
    }

    private Map<String, Object> parseDotenv(Path dotenvPath) throws IOException {
        Map<String, Object> properties = new LinkedHashMap<>();
        try (BufferedReader reader = Files.newBufferedReader(dotenvPath, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#") || !trimmed.contains("=")) {
                    continue;
                }
                String[] parts = trimmed.split("=", 2);
                String key = parts[0].trim();
                if (key.startsWith("\uFEFF")) {
                    key = key.substring(1).trim();
                }
                if (key.startsWith("export ")) {
                    key = key.substring("export ".length()).trim();
                }
                if (key.isEmpty()) {
                    continue;
                }
                properties.put(key, normalizeValue(parts.length > 1 ? parts[1] : ""));
            }
        }
        return properties;
    }

    private void addSpringAiOpenAiAliases(Map<String, Object> properties) {
        putIfText(properties, "spring.ai.openai.api-key", firstText(properties, "OPENAI_API_KEY", "OPENAI_CHAT_API_KEY"));
        putIfText(properties, "spring.ai.openai.chat.api-key", firstText(properties, "OPENAI_CHAT_API_KEY", "OPENAI_API_KEY"));
        putIfText(properties, "spring.ai.openai.base-url", firstText(properties, "OPENAI_BASE_URL", "OPENAI_CHAT_BASE_URL"));
        putIfText(properties, "spring.ai.openai.chat.base-url", firstText(properties, "OPENAI_CHAT_BASE_URL", "OPENAI_BASE_URL"));
        putIfText(properties, "spring.ai.openai.chat.options.model", firstText(properties, "OPENAI_CHAT_MODEL"));
    }

    private void putIfText(Map<String, Object> properties, String key, String value) {
        if (hasText(value) && !hasText(String.valueOf(properties.getOrDefault(key, "")))) {
            properties.put(key, value);
        }
    }

    private String firstText(Map<String, Object> properties, String... keys) {
        for (String key : keys) {
            Object value = properties.get(key);
            if (value != null && hasText(String.valueOf(value))) {
                return String.valueOf(value).trim();
            }
        }
        return "";
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private String normalizeValue(String rawValue) {
        String value = rawValue == null ? "" : rawValue.trim();
        if (value.length() >= 2
                && (value.startsWith("\"") && value.endsWith("\"") || value.startsWith("'") && value.endsWith("'"))) {
            return value.substring(1, value.length() - 1);
        }
        return value;
    }
}
