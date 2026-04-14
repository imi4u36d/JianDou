package com.jiandou.api.generation;

public record RemoteVideoGenerationResult(
    byte[] data,
    String mimeType,
    String remoteSourceUrl,
    String provider,
    String providerModel,
    String modelName,
    String endpointHost,
    String taskEndpointHost,
    String taskId,
    int width,
    int height,
    int durationSeconds,
    boolean hasAudio,
    String firstFrameUrl,
    String requestedLastFrameUrl,
    String lastFrameUrl,
    boolean returnLastFrame,
    boolean generateAudio,
    String actualPrompt,
    int submitLatencyMs
) {
}
