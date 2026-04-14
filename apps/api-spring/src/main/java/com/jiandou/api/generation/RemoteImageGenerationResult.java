package com.jiandou.api.generation;

public record RemoteImageGenerationResult(
    byte[] data,
    String mimeType,
    String remoteSourceUrl,
    String provider,
    String providerModel,
    String endpointHost,
    int width,
    int height,
    String requestedSize,
    int latencyMs
) {
}
