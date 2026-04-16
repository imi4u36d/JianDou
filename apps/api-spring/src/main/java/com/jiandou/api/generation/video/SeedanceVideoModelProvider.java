package com.jiandou.api.generation.video;

import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.RemoteVideoTaskSubmission;
import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * Seedance 视频 provider。
 */
@Component
public class SeedanceVideoModelProvider implements VideoModelProvider {

    private static final Map<String, String> SEEDANCE_MODEL_ALIASES = Map.of(
        "seedance-1.5-pro", "doubao-seedance-1-5-pro-251215"
    );

    private final VideoProviderTransport transport;

    public SeedanceVideoModelProvider(VideoProviderTransport transport) {
        this.transport = transport;
    }

    @Override
    public boolean supports(MediaProviderProfile profile) {
        String provider = profile == null ? "" : profile.provider();
        return provider.toLowerCase(Locale.ROOT).contains("seedance");
    }

    @Override
    public RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request) {
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("seedance config missing endpoint, task endpoint or api key");
        }
        if (request.firstFrameUrl() == null || request.firstFrameUrl().isBlank()) {
            throw new GenerationProviderException("seedance video requires firstFrameUrl");
        }
        String providerModel = normalizeSeedanceModelName(blankTo(profile.modelName(), request.requestedModel()));
        Map<String, Object> body = buildSeedanceVideoRequestBody(
            providerModel,
            request.prompt(),
            request.width(),
            request.height(),
            request.durationSeconds(),
            request.firstFrameUrl(),
            request.lastFrameUrl(),
            request.seed(),
            request.cameraFixed(),
            request.watermark(),
            request.returnLastFrame(),
            request.generateAudio()
        );
        HttpResponse<String> submitResponse = transport.sendJson(
            profile.baseUrl(),
            profile.apiKey(),
            body,
            profile.timeoutSeconds(),
            Map.of("X-Api-Key", profile.apiKey())
        );
        Map<String, Object> submitPayload = transport.decode(submitResponse.body());
        String taskId = transport.extractTaskId(submitPayload);
        if (taskId.isBlank()) {
            throw new GenerationProviderException("seedance task response missing task id");
        }
        return new RemoteVideoTaskSubmission(
            profile.provider(),
            request.requestedModel(),
            providerModel,
            profile.endpointHost(),
            profile.taskEndpointHost(),
            taskId,
            request.firstFrameUrl(),
            request.lastFrameUrl() == null ? "" : request.lastFrameUrl(),
            request.returnLastFrame(),
            request.generateAudio(),
            request.prompt(),
            0
        );
    }

    @Override
    public RemoteTaskQueryResult query(MediaProviderProfile profile, String remoteTaskId) {
        String normalizedTaskId = remoteTaskId == null ? "" : remoteTaskId.trim();
        if (normalizedTaskId.isBlank()) {
            throw new GenerationProviderException("seedance task id is required");
        }
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("seedance config missing task endpoint or api key");
        }
        String pollUrl = profile.taskBaseUrl().replaceAll("/+$", "") + "/" + transport.encodePathSegment(normalizedTaskId);
        HttpRequest request = HttpRequest.newBuilder(URI.create(pollUrl))
            .header("Authorization", "Bearer " + profile.apiKey())
            .header("X-Api-Key", profile.apiKey())
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(15, profile.timeoutSeconds())))
            .GET()
            .build();
        HttpResponse<String> response = transport.send(request, "seedance task query failed");
        Map<String, Object> payload = transport.decode(response.body());
        return new RemoteTaskQueryResult(
            blankTo(transport.extractTaskId(payload), normalizedTaskId),
            transport.extractTaskStatus(payload),
            transport.extractVideoUrl(payload),
            transport.extractTaskMessage(payload),
            payload
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

    private String blankTo(String primary, String fallback) {
        return primary == null || primary.isBlank() ? fallback : primary;
    }
}
