package com.jiandou.api.generation.image;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.exception.GenerationProviderException;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 图片 provider 共用的 HTTP 传输与响应解析支持。
 */
@Component
public class ImageProviderTransport {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public ImageProviderTransport(ObjectMapper objectMapper) {
        this(objectMapper, HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build());
    }

    @Autowired
    public ImageProviderTransport(ObjectMapper objectMapper, HttpClient httpClient) {
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

    public DownloadedBinary downloadBinary(String url, int timeoutSeconds) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
            .header("User-Agent", "jiandou-spring/0.1")
            .header("Accept", "*/*")
            .timeout(Duration.ofSeconds(Math.max(15, timeoutSeconds)))
            .GET()
            .build();
        try {
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new GenerationProviderException("remote media download failed: http " + response.statusCode());
            }
            String mimeType = firstNonBlank(response.headers().firstValue("content-type").orElse(""), "");
            return new DownloadedBinary(response.body(), mimeType);
        } catch (IOException | InterruptedException ex) {
            if (ex instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new GenerationProviderException("remote media download failed: " + ex.getMessage());
        }
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

    private String encode(Map<String, Object> body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (IOException ex) {
            throw new GenerationProviderException("provider request encode failed: " + ex.getMessage());
        }
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

    /**
     * 下载后的二进制结构。
     * @param data data值
     * @param mimeType mime类型值
     */
    public record DownloadedBinary(byte[] data, String mimeType) {
    }
}
