package com.jiandou.api.generation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class RemoteMediaGenerationClient {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
    private static final Map<String, String> SEEDREAM_MODEL_ALIASES = Map.ofEntries(
        Map.entry("doubao-seedream-4.5", "doubao-seedream-4-5-251128"),
        Map.entry("doubao-seedream-4-5", "doubao-seedream-4-5-251128"),
        Map.entry("seedream-4.5", "doubao-seedream-4-5-251128"),
        Map.entry("seedream-4-5", "doubao-seedream-4-5-251128"),
        Map.entry("doubao-seedream-5.0", "doubao-seedream-5-0-260128"),
        Map.entry("doubao-seedream-5-0", "doubao-seedream-5-0-260128"),
        Map.entry("seedream-5.0", "doubao-seedream-5-0-260128"),
        Map.entry("seedream-5-0", "doubao-seedream-5-0-260128")
    );
    private static final Map<String, String> SEEDANCE_MODEL_ALIASES = Map.of(
        "seedance-1.5-pro", "doubao-seedance-1-5-pro-251215"
    );

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public RemoteMediaGenerationClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
    }

    public RemoteImageGenerationResult generateSeedreamImage(
        MediaProviderProfile profile,
        String requestedModel,
        String prompt,
        int width,
        int height,
        Integer seed
    ) {
        if (!profile.ready()) {
            throw new GenerationConfigurationException("image provider config missing api key or base url");
        }
        String modelName = normalizeSeedreamModelName(blankTo(profile.modelName(), requestedModel));
        String size = seedreamSize(modelName, width, height);
        Map<String, Object> body = buildSeedreamImageRequestBody(modelName, prompt, size, seed);
        HttpResponse<String> response = sendJson(
            profile.baseUrl(),
            profile.apiKey(),
            body,
            profile.timeoutSeconds(),
            Map.of("X-Api-Key", profile.apiKey())
        );
        int latencyMs = 0;
        Map<String, Object> payload = decode(response.body());
        String sourceUrl = extractFirstString(payload, "url", "image_url", "imageUrl", "file_url", "fileUrl");
        byte[] data;
        String mimeType = "image/png";
        if (!sourceUrl.isBlank()) {
            DownloadedBinary binary = downloadBinary(sourceUrl, profile.timeoutSeconds());
            data = binary.data();
            mimeType = binary.mimeType().isBlank() ? mimeType : binary.mimeType();
        } else {
            String b64 = extractFirstString(payload, "b64_json", "base64_data", "base64", "imageBase64");
            if (b64.isBlank()) {
                throw new GenerationProviderException("seedream response did not include usable image data");
            }
            try {
                data = Base64.getDecoder().decode(b64);
            } catch (IllegalArgumentException ex) {
                throw new GenerationProviderException("seedream response returned invalid base64 image data");
            }
        }
        return new RemoteImageGenerationResult(
            data,
            mimeType,
            sourceUrl,
            profile.provider(),
            modelName,
            profile.endpointHost(),
            width,
            height,
            size,
            latencyMs
        );
    }

    Map<String, Object> buildSeedreamImageRequestBody(String modelName, String prompt, String size, Integer seed) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("prompt", prompt);
        body.put("sequential_image_generation", "disabled");
        body.put("response_format", "url");
        body.put("size", size);
        body.put("stream", false);
        body.put("watermark", false);
        if (seed != null) {
            body.put("seed", seed);
        }
        return body;
    }

    public RemoteVideoTaskSubmission submitDashscopeVideoTask(
        MediaProviderProfile profile,
        String requestedModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        Integer seed
    ) {
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("video provider config missing endpoint, task endpoint or api key");
        }
        String providerModel = blankTo(profile.modelName(), requestedModel);
        Map<String, Object> body = buildDashscopeVideoRequestBody(providerModel, prompt, width, height, durationSeconds, profile.promptExtend(), seed);
        HttpResponse<String> submitResponse = sendJson(
            profile.baseUrl(),
            profile.apiKey(),
            body,
            profile.timeoutSeconds(),
            Map.of("X-DashScope-Async", "enable")
        );
        Map<String, Object> submitPayload = decode(submitResponse.body());
        String taskId = extractTaskId(submitPayload);
        if (taskId.isBlank()) {
            throw new GenerationProviderException("dashscope video task response missing task id");
        }
        return new RemoteVideoTaskSubmission(
            profile.provider(),
            requestedModel,
            providerModel,
            profile.endpointHost(),
            profile.taskEndpointHost(),
            taskId,
            "",
            "",
            false,
            true,
            prompt,
            0
        );
    }

    Map<String, Object> buildDashscopeVideoRequestBody(
        String providerModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        boolean promptExtend,
        Integer seed
    ) {
        String normalizedSize = width + "*" + height;
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("size", normalizedSize);
        parameters.put("prompt_extend", promptExtend);
        parameters.put("duration", durationSeconds);
        if (seed != null) {
            parameters.put("seed", seed);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", providerModel);
        body.put("input", Map.of("prompt", prompt));
        body.put("parameters", parameters);
        return body;
    }

    public RemoteVideoTaskSubmission submitSeedanceVideoTask(
        MediaProviderProfile profile,
        String requestedModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        String firstFrameUrl,
        String lastFrameUrl,
        Integer seed,
        boolean cameraFixed,
        boolean watermark,
        boolean returnLastFrame,
        boolean generateAudio
    ) {
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("seedance config missing endpoint, task endpoint or api key");
        }
        if (firstFrameUrl == null || firstFrameUrl.isBlank()) {
            throw new GenerationProviderException("seedance video requires firstFrameUrl");
        }
        String providerModel = normalizeSeedanceModelName(blankTo(profile.modelName(), requestedModel));
        Map<String, Object> body = buildSeedanceVideoRequestBody(
            providerModel,
            prompt,
            width,
            height,
            durationSeconds,
            firstFrameUrl,
            lastFrameUrl,
            seed,
            cameraFixed,
            watermark,
            returnLastFrame,
            generateAudio
        );
        HttpResponse<String> submitResponse = sendJson(
            profile.baseUrl(),
            profile.apiKey(),
            body,
            profile.timeoutSeconds(),
            Map.of("X-Api-Key", profile.apiKey())
        );
        Map<String, Object> submitPayload = decode(submitResponse.body());
        String taskId = extractTaskId(submitPayload);
        if (taskId.isBlank()) {
            throw new GenerationProviderException("seedance task response missing task id");
        }
        return new RemoteVideoTaskSubmission(
            profile.provider(),
            requestedModel,
            providerModel,
            profile.endpointHost(),
            profile.taskEndpointHost(),
            taskId,
            firstFrameUrl,
            lastFrameUrl == null ? "" : lastFrameUrl,
            returnLastFrame,
            generateAudio,
            prompt,
            0
        );
    }

    Map<String, Object> buildSeedanceVideoRequestBody(
        String providerModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        String firstFrameUrl,
        String lastFrameUrl,
        Integer seed,
        boolean cameraFixed,
        boolean watermark,
        boolean returnLastFrame,
        boolean generateAudio
    ) {
        List<Map<String, Object>> content = new ArrayList<>();
        content.add(Map.of("type", "text", "text", prompt));
        content.add(Map.of(
            "type", "image_url",
            "role", "first_frame",
            "image_url", Map.of("url", firstFrameUrl)
        ));
        if (lastFrameUrl != null && !lastFrameUrl.isBlank()) {
            content.add(Map.of(
                "type", "image_url",
                "role", "last_frame",
                "image_url", Map.of("url", lastFrameUrl)
            ));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", providerModel);
        body.put("content", content);
        body.put("ratio", aspectRatio(width, height));
        body.put("resolution", seedanceResolution(width, height));
        body.put("duration", durationSeconds);
        if (seed != null) {
            body.put("seed", seed);
        }
        body.put("camera_fixed", cameraFixed);
        body.put("watermark", watermark);
        body.put("return_last_frame", returnLastFrame);
        body.put("generate_audio", generateAudio);
        return body;
    }

    public RemoteVideoGenerationResult generateDashscopeVideo(
        MediaProviderProfile profile,
        String requestedModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        Integer seed
    ) {
        RemoteVideoTaskSubmission submission = submitDashscopeVideoTask(
            profile,
            requestedModel,
            prompt,
            width,
            height,
            durationSeconds,
            seed
        );
        Map<String, Object> resultPayload = waitForDashscopeTask(profile, submission.taskId());
        String videoUrl = extractVideoUrl(resultPayload);
        if (videoUrl.isBlank()) {
            throw new GenerationProviderException("dashscope video task completed without video url");
        }
        DownloadedBinary binary = downloadBinary(videoUrl, Math.max(profile.timeoutSeconds(), 300));
        Map<String, Object> output = mapValue(resultPayload.get("output"));
        String actualPrompt = firstNonBlank(
            stringValue(output.get("orig_prompt")),
            stringValue(output.get("actual_prompt")),
            submission.actualPrompt()
        );
        return new RemoteVideoGenerationResult(
            binary.data(),
            binary.mimeType().isBlank() ? "video/mp4" : binary.mimeType(),
            videoUrl,
            submission.provider(),
            submission.providerModel(),
            submission.providerModel(),
            submission.endpointHost(),
            submission.taskEndpointHost(),
            submission.taskId(),
            width,
            height,
            durationSeconds,
            true,
            "",
            "",
            "",
            false,
            true,
            actualPrompt,
            submission.submitLatencyMs()
        );
    }

    public RemoteVideoGenerationResult generateSeedanceVideo(
        MediaProviderProfile profile,
        String requestedModel,
        String prompt,
        int width,
        int height,
        int durationSeconds,
        String firstFrameUrl,
        String lastFrameUrl,
        Integer seed,
        boolean cameraFixed,
        boolean watermark,
        boolean returnLastFrame,
        boolean generateAudio
    ) {
        RemoteVideoTaskSubmission submission = submitSeedanceVideoTask(
            profile,
            requestedModel,
            prompt,
            width,
            height,
            durationSeconds,
            firstFrameUrl,
            lastFrameUrl,
            seed,
            cameraFixed,
            watermark,
            returnLastFrame,
            generateAudio
        );
        Map<String, Object> resultPayload = waitForSeedanceTask(profile, submission.taskId());
        String videoUrl = extractVideoUrl(resultPayload);
        if (videoUrl.isBlank()) {
            throw new GenerationProviderException("seedance task completed without video url");
        }
        DownloadedBinary binary = downloadBinary(videoUrl, Math.max(profile.timeoutSeconds(), 300));
        String resolvedLastFrameUrl = extractFirstString(resultPayload, "last_frame_url", "lastFrameUrl");
        return new RemoteVideoGenerationResult(
            binary.data(),
            binary.mimeType().isBlank() ? "video/mp4" : binary.mimeType(),
            videoUrl,
            submission.provider(),
            submission.requestedModel(),
            submission.providerModel(),
            submission.endpointHost(),
            submission.taskEndpointHost(),
            submission.taskId(),
            width,
            height,
            durationSeconds,
            submission.generateAudio(),
            submission.firstFrameUrl(),
            submission.requestedLastFrameUrl(),
            resolvedLastFrameUrl,
            submission.returnLastFrame(),
            submission.generateAudio(),
            submission.actualPrompt(),
            submission.submitLatencyMs()
        );
    }

    public RemoteTaskQueryResult queryDashscopeTask(MediaProviderProfile profile, String remoteTaskId) {
        String normalizedTaskId = stringValue(remoteTaskId);
        if (normalizedTaskId.isBlank()) {
            throw new GenerationProviderException("dashscope task id is required");
        }
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("dashscope config missing task endpoint or api key");
        }
        String pollUrl = profile.taskBaseUrl().replaceAll("/+$", "") + "/" + encodePathSegment(normalizedTaskId);
        HttpRequest request = HttpRequest.newBuilder(URI.create(pollUrl))
            .header("Authorization", "Bearer " + profile.apiKey())
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(15, profile.timeoutSeconds())))
            .GET()
            .build();
        HttpResponse<String> response = send(request, "dashscope task query failed");
        Map<String, Object> payload = decode(response.body());
        return new RemoteTaskQueryResult(
            firstNonBlank(extractTaskId(payload), normalizedTaskId),
            extractTaskStatus(payload),
            extractVideoUrl(payload),
            extractTaskMessage(payload),
            payload
        );
    }

    public RemoteTaskQueryResult querySeedanceTask(MediaProviderProfile profile, String remoteTaskId) {
        String normalizedTaskId = stringValue(remoteTaskId);
        if (normalizedTaskId.isBlank()) {
            throw new GenerationProviderException("seedance task id is required");
        }
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("seedance config missing task endpoint or api key");
        }
        String pollUrl = profile.taskBaseUrl().replaceAll("/+$", "") + "/" + encodePathSegment(normalizedTaskId);
        HttpRequest request = HttpRequest.newBuilder(URI.create(pollUrl))
            .header("Authorization", "Bearer " + profile.apiKey())
            .header("X-Api-Key", profile.apiKey())
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(15, profile.timeoutSeconds())))
            .GET()
            .build();
        HttpResponse<String> response = send(request, "seedance task query failed");
        Map<String, Object> payload = decode(response.body());
        return new RemoteTaskQueryResult(
            firstNonBlank(extractTaskId(payload), normalizedTaskId),
            extractTaskStatus(payload),
            extractVideoUrl(payload),
            extractTaskMessage(payload),
            payload
        );
    }

    private HttpResponse<String> sendJson(
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

    private Map<String, Object> waitForDashscopeTask(MediaProviderProfile profile, String taskId) {
        long deadline = System.currentTimeMillis() + Math.max(30, profile.pollTimeoutSeconds()) * 1000L;
        while (System.currentTimeMillis() < deadline) {
            RemoteTaskQueryResult result = queryDashscopeTask(profile, taskId);
            String status = normalizeStatus(result.status());
            if (isSuccessStatus(status)) {
                return result.payload();
            }
            if (isFailureStatus(status)) {
                throw new GenerationProviderException(firstNonBlank(result.message(), "dashscope task failed"));
            }
            sleepSeconds(profile.pollIntervalSeconds());
        }
        throw new GenerationProviderException("dashscope task poll timeout");
    }

    private Map<String, Object> waitForSeedanceTask(MediaProviderProfile profile, String taskId) {
        long deadline = System.currentTimeMillis() + Math.max(30, profile.pollTimeoutSeconds()) * 1000L;
        while (System.currentTimeMillis() < deadline) {
            RemoteTaskQueryResult result = querySeedanceTask(profile, taskId);
            String status = normalizeStatus(result.status());
            if (isSuccessStatus(status)) {
                return result.payload();
            }
            if (isFailureStatus(status)) {
                throw new GenerationProviderException(firstNonBlank(result.message(), "seedance task failed"));
            }
            sleepSeconds(profile.pollIntervalSeconds());
        }
        throw new GenerationProviderException("seedance task poll timeout");
    }

    private boolean isSuccessStatus(String status) {
        return List.of("SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED").contains(normalizeStatus(status));
    }

    private boolean isFailureStatus(String status) {
        return List.of("FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR").contains(normalizeStatus(status));
    }

    private String normalizeStatus(String status) {
        return stringValue(status).toUpperCase(Locale.ROOT);
    }

    private DownloadedBinary downloadBinary(String url, int timeoutSeconds) {
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

    private HttpResponse<String> send(HttpRequest request, String errorPrefix) {
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

    private String encode(Map<String, Object> body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (IOException ex) {
            throw new GenerationProviderException("provider request encode failed: " + ex.getMessage());
        }
    }

    private Map<String, Object> decode(String raw) {
        try {
            return objectMapper.readValue(raw, MAP_TYPE);
        } catch (IOException ex) {
            throw new GenerationProviderException("provider response decode failed: " + ex.getMessage());
        }
    }

    private String extractTaskId(Map<String, Object> payload) {
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

    private String extractVideoUrl(Map<String, Object> payload) {
        return extractFirstString(payload, "video_url", "videoUrl", "url", "file_url", "fileUrl", "media_url", "mediaUrl");
    }

    private String extractTaskStatus(Map<String, Object> payload) {
        return firstNonBlank(
            extractFirstString(payload, "task_status", "taskStatus", "status", "state"),
            extractFirstString(mapValue(payload.get("output")), "task_status", "taskStatus", "status", "state"),
            extractFirstString(mapValue(payload.get("data")), "task_status", "taskStatus", "status", "state"),
            "UNKNOWN"
        ).toUpperCase(Locale.ROOT);
    }

    private String extractTaskMessage(Map<String, Object> payload) {
        return firstNonBlank(
            extractFirstString(payload, "message", "error"),
            extractFirstString(mapValue(payload.get("output")), "message", "error"),
            extractFirstString(mapValue(payload.get("data")), "message", "error")
        );
    }

    @SuppressWarnings("unchecked")
    private String extractFirstString(Object raw, String... keys) {
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

    private Map<String, Object> mapValue(Object value) {
        if (!(value instanceof Map<?, ?> map)) {
            return Map.of();
        }
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            normalized.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return normalized;
    }

    private String normalizeSeedreamModelName(String raw) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        return SEEDREAM_MODEL_ALIASES.getOrDefault(normalized, raw);
    }

    private String normalizeSeedanceModelName(String raw) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        return SEEDANCE_MODEL_ALIASES.getOrDefault(normalized, raw);
    }

    private String aspectRatio(int width, int height) {
        if (width == height) {
            return "1:1";
        }
        return width > height ? "16:9" : "9:16";
    }

    private String seedanceResolution(int width, int height) {
        int longestEdge = Math.max(width, height);
        if (longestEdge >= 1920) {
            return "1080p";
        }
        if (longestEdge >= 1280) {
            return "720p";
        }
        return "480p";
    }

    String seedreamSize(String modelName, int width, int height) {
        String normalizedModel = normalizeSeedreamModelName(modelName);
        if ("doubao-seedream-4-5-251128".equals(normalizedModel)) {
            return "2K";
        }
        return "1K";
    }

    private void sleepSeconds(int seconds) {
        try {
            Thread.sleep(Math.max(1, seconds) * 1000L);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new GenerationProviderException("provider task poll interrupted");
        }
    }

    private String blankTo(String primary, String fallback) {
        return primary == null || primary.isBlank() ? fallback : primary;
    }

    private String encodePathSegment(String value) {
        return URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8).replace("+", "%20");
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

    private record DownloadedBinary(byte[] data, String mimeType) {
    }
}
