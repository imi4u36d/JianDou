package com.jiandou.api.generation.text;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.exception.GenerationProviderException;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 文本 provider 共用的 HTTP 传输与响应解析支持。
 */
@Component
public class TextProviderTransport {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public TextProviderTransport(ObjectMapper objectMapper) {
        this(objectMapper, HttpClient.newBuilder().build());
    }

    @Autowired
    public TextProviderTransport(ObjectMapper objectMapper, HttpClient httpClient) {
        this.objectMapper = objectMapper;
        this.httpClient = httpClient;
    }

    public HttpResponse<String> sendJson(String endpoint, String apiKey, Map<String, Object> body, int timeoutSeconds, String errorPrefix) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint))
            .header("Authorization", "Bearer " + apiKey)
            .header("Content-Type", "application/json")
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(30, timeoutSeconds)))
            .POST(HttpRequest.BodyPublishers.ofString(encode(body)))
            .build();
        return send(request, errorPrefix);
    }

    public HttpResponse<String> send(HttpRequest request, String errorPrefix) {
        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new GenerationProviderException(
                    errorPrefix + ": http " + response.statusCode() + " " + truncate(response.body(), 320)
                );
            }
            return response;
        } catch (IOException | InterruptedException ex) {
            if (ex instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new GenerationProviderException(errorPrefix + ": " + ex.getMessage());
        }
    }

    public Map<String, Object> decode(String raw) {
        try {
            return objectMapper.readValue(raw, MAP_TYPE);
        } catch (IOException ex) {
            throw new GenerationProviderException("text model response decode failed: " + ex.getMessage());
        }
    }

    public String extractText(Map<String, Object> responseMap) {
        String outputText = stringValue(responseMap.get("output_text"));
        if (!outputText.isBlank()) {
            return outputText;
        }
        String fromOutput = extractFromOutput(responseMap.get("output"));
        if (!fromOutput.isBlank()) {
            return fromOutput;
        }
        String fromChoices = extractFromChoices(responseMap.get("choices"));
        if (!fromChoices.isBlank()) {
            return fromChoices;
        }
        return stringValue(responseMap.get("text"));
    }

    public String endpointHost(String endpoint) {
        try {
            String host = URI.create(endpoint).getHost();
            return host == null ? "" : host;
        } catch (Exception ignored) {
            return "";
        }
    }

    public String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String encode(Map<String, Object> body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (IOException ex) {
            throw new GenerationProviderException("text model request encode failed: " + ex.getMessage());
        }
    }

    private String extractFromOutput(Object raw) {
        if (!(raw instanceof List<?> items)) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            appendContent(builder, map.get("content"));
        }
        return builder.toString().trim();
    }

    private String extractFromChoices(Object raw) {
        if (!(raw instanceof List<?> choices) || choices.isEmpty()) {
            return "";
        }
        Object first = choices.get(0);
        if (!(first instanceof Map<?, ?> map)) {
            return "";
        }
        Object message = map.get("message");
        if (message instanceof Map<?, ?> messageMap) {
            Object content = messageMap.get("content");
            if (content instanceof String text) {
                return text.trim();
            }
            StringBuilder builder = new StringBuilder();
            appendContent(builder, content);
            return builder.toString().trim();
        }
        return stringValue(map.get("text"));
    }

    private void appendContent(StringBuilder builder, Object raw) {
        if (raw instanceof String text) {
            if (!text.isBlank()) {
                if (builder.length() > 0) {
                    builder.append('\n');
                }
                builder.append(text.trim());
            }
            return;
        }
        if (raw instanceof List<?> list) {
            for (Object item : list) {
                appendContent(builder, item);
            }
            return;
        }
        if (!(raw instanceof Map<?, ?> map)) {
            return;
        }
        Object type = map.get("type");
        if ("output_text".equals(type) || "text".equals(type) || "input_text".equals(type)) {
            appendContent(builder, map.get("text"));
            return;
        }
        if (map.containsKey("content")) {
            appendContent(builder, map.get("content"));
        }
    }

    private String truncate(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() <= limit ? value : value.substring(0, limit);
    }
}
