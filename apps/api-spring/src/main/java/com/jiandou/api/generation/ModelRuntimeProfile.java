package com.jiandou.api.generation;

import java.net.URI;

public record ModelRuntimeProfile(
    String provider,
    String modelName,
    String fallbackModel,
    String apiKey,
    String baseUrl,
    int timeoutSeconds,
    double temperature,
    int maxTokens,
    String source
) {

    public boolean ready() {
        return apiKey != null && !apiKey.isBlank() && baseUrl != null && !baseUrl.isBlank();
    }

    public String endpointHost() {
        try {
            return URI.create(baseUrl).getHost();
        } catch (Exception ignored) {
            return "";
        }
    }
}
