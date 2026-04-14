package com.jiandou.api.generation;

import java.net.URI;

public record MediaProviderProfile(
    String provider,
    String modelName,
    String apiKey,
    String baseUrl,
    String taskBaseUrl,
    int timeoutSeconds,
    int pollIntervalSeconds,
    int pollTimeoutSeconds,
    boolean promptExtend,
    boolean cameraFixed,
    boolean watermark,
    String source
) {

    public boolean ready() {
        return apiKey != null && !apiKey.isBlank() && baseUrl != null && !baseUrl.isBlank();
    }

    public String endpointHost() {
        return hostOf(baseUrl);
    }

    public String taskEndpointHost() {
        return hostOf(taskBaseUrl);
    }

    private String hostOf(String raw) {
        try {
            return URI.create(raw).getHost();
        } catch (Exception ignored) {
            return "";
        }
    }
}
