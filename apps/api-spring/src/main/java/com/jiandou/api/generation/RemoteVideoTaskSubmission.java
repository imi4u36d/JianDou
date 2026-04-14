package com.jiandou.api.generation;

public record RemoteVideoTaskSubmission(
    String provider,
    String requestedModel,
    String providerModel,
    String endpointHost,
    String taskEndpointHost,
    String taskId,
    String firstFrameUrl,
    String requestedLastFrameUrl,
    boolean returnLastFrame,
    boolean generateAudio,
    String actualPrompt,
    int submitLatencyMs
) {
}
