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
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * Dashscope 视频 provider。
 */
@Component
public class DashscopeVideoModelProvider implements VideoModelProvider {

    private final VideoProviderTransport transport;

    public DashscopeVideoModelProvider(VideoProviderTransport transport) {
        this.transport = transport;
    }

    @Override
    public boolean supports(MediaProviderProfile profile) {
        String provider = profile == null ? "" : profile.provider();
        return !provider.toLowerCase(Locale.ROOT).contains("seedance");
    }

    @Override
    public RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request) {
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("video provider config missing endpoint, task endpoint or api key");
        }
        String providerModel = blankTo(profile.modelName(), request.requestedModel());
        Map<String, Object> body = buildDashscopeVideoRequestBody(
            providerModel,
            request.prompt(),
            request.width(),
            request.height(),
            request.durationSeconds(),
            profile.promptExtend(),
            request.seed()
        );
        HttpResponse<String> submitResponse = transport.sendJson(
            profile.baseUrl(),
            profile.apiKey(),
            body,
            profile.timeoutSeconds(),
            Map.of("X-DashScope-Async", "enable")
        );
        Map<String, Object> submitPayload = transport.decode(submitResponse.body());
        String taskId = transport.extractTaskId(submitPayload);
        if (taskId.isBlank()) {
            throw new GenerationProviderException("dashscope video task response missing task id");
        }
        return new RemoteVideoTaskSubmission(
            profile.provider(),
            request.requestedModel(),
            providerModel,
            profile.endpointHost(),
            profile.taskEndpointHost(),
            taskId,
            "",
            "",
            false,
            true,
            request.prompt(),
            0
        );
    }

    @Override
    public RemoteTaskQueryResult query(MediaProviderProfile profile, String remoteTaskId) {
        String normalizedTaskId = remoteTaskId == null ? "" : remoteTaskId.trim();
        if (normalizedTaskId.isBlank()) {
            throw new GenerationProviderException("dashscope task id is required");
        }
        if (!profile.ready() || profile.taskBaseUrl() == null || profile.taskBaseUrl().isBlank()) {
            throw new GenerationConfigurationException("dashscope config missing task endpoint or api key");
        }
        String pollUrl = profile.taskBaseUrl().replaceAll("/+$", "") + "/" + transport.encodePathSegment(normalizedTaskId);
        HttpRequest request = HttpRequest.newBuilder(URI.create(pollUrl))
            .header("Authorization", "Bearer " + profile.apiKey())
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(Math.max(15, profile.timeoutSeconds())))
            .GET()
            .build();
        HttpResponse<String> response = transport.send(request, "dashscope task query failed");
        Map<String, Object> payload = transport.decode(response.body());
        return new RemoteTaskQueryResult(
            blankTo(transport.extractTaskId(payload), normalizedTaskId),
            transport.extractTaskStatus(payload),
            transport.extractVideoUrl(payload),
            transport.extractTaskMessage(payload),
            payload
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

    private String blankTo(String primary, String fallback) {
        return primary == null || primary.isBlank() ? fallback : primary;
    }
}
