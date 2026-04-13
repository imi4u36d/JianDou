package com.jiandou.api.generation;

public record TextModelResponse(
    String text,
    String endpoint,
    String endpointHost,
    int latencyMs,
    boolean responsesApi,
    String responseId
) {
}
