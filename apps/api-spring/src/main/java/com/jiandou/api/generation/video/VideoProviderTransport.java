package com.jiandou.api.generation.video;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.exception.GenerationProviderException;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 视频 provider 共用的 HTTP 传输与响应解析支持。
 */
@Component
public class VideoProviderTransport {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public VideoProviderTransport(ObjectMapper objectMapper) {
        this(objectMapper, HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build());
    }

    @Autowired
    public VideoProviderTransport(ObjectMapper objectMapper, HttpClient httpClient) {
        this.objectMapper = objectMapper;
        this.httpClient = httpClient;
    }

    public HttpResponse<String> sendJson(
        String endpoint,
        String apiKey,
        Map<String, Object> body,
        int timeoutSeconds,
        Map<String, String> extraHeaders
    ) {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(endpoint))
            .header("Authorization", "Bearer " + apiKey)
            .header("Content-Type", "application/json")
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(30, timeoutSeconds)))
            .POST(HttpRequest.BodyPublishers.ofString(encode(body)));
        for (Map.Entry<String, String> entry : extraHeaders.entrySet()) {
            builder.header(entry.getKey(), entry.getValue());
        }
        return send(builder.build(), "provider request failed");
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
            throw new GenerationProviderException("provider response decode failed: " + ex.getMessage());
        }
    }

    public String extractTaskId(Map<String, Object> payload) {
        return firstNonBlank(
            stringValue(payload.get("task_id")),
            stringValue(payload.get("taskId")),
            stringValue(payload.get("id")),
            stringValue(mapValue(payload.get("output")).get("task_id")),
            stringValue(mapValue(payload.get("output")).get("taskId")),
            stringValue(mapValue(payload.get("data")).get("task_id")),
            stringValue(mapValue(payload.get("data")).get("taskId"))
        );
    }

    public String extractVideoUrl(Map<String, Object> payload) {
        return extractFirstString(payload, "video_url", "videoUrl", "url", "file_url", "fileUrl", "media_url", "mediaUrl");
    }

    public String extractTaskStatus(Map<String, Object> payload) {
        return firstNonBlank(
            extractFirstString(payload, "task_status", "taskStatus", "status", "state"),
            extractFirstString(mapValue(payload.get("output")), "task_status", "taskStatus", "status", "state"),
            extractFirstString(mapValue(payload.get("data")), "task_status", "taskStatus", "status", "state"),
            "UNKNOWN"
        ).toUpperCase(Locale.ROOT);
    }

    public String extractTaskMessage(Map<String, Object> payload) {
        return firstNonBlank(
            extractFirstString(payload, "message", "error"),
            extractFirstString(mapValue(payload.get("output")), "message", "error"),
            extractFirstString(mapValue(payload.get("data")), "message", "error")
        );
    }

    public String encodePathSegment(String value) {
        return URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8).replace("+", "%20");
    }

    @SuppressWarnings("unchecked")
    public String extractFirstString(Object raw, String... keys) {
        if (raw instanceof Map<?, ?> map) {
            for (String key : keys) {
                Object value = map.get(key);
                if (value instanceof String text && !text.isBlank()) {
                    return text.trim();
                }
                if (value instanceof Map<?, ?> nestedMap) {
                    String nested = extractFirstString(nestedMap, keys);
                    if (!nested.isBlank()) {
                        return nested;
                    }
                }
                if (value instanceof List<?> nestedList) {
                    String nested = extractFirstString(nestedList, keys);
                    if (!nested.isBlank()) {
                        return nested;
                    }
                }
            }
            for (Object value : map.values()) {
                String nested = extractFirstString(value, keys);
                if (!nested.isBlank()) {
                    return nested;
                }
            }
        }
        if (raw instanceof List<?> list) {
            for (Object item : list) {
                String nested = extractFirstString(item, keys);
                if (!nested.isBlank()) {
                    return nested;
                }
            }
        }
        return "";
    }

    public Map<String, Object> mapValue(Object value) {
        if (!(value instanceof Map<?, ?> map)) {
            return Map.of();
        }
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            normalized.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return normalized;
    }

    private String encode(Map<String, Object> body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (IOException ex) {
            throw new GenerationProviderException("provider request encode failed: " + ex.getMessage());
        }
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String truncate(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() <= limit ? value : value.substring(0, limit);
    }
}
