package com.jiandou.api.task.domain;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

public record TaskStageRunSnapshot(
    String stageRunId,
    String taskId,
    String attemptId,
    String stageName,
    int stageSeq,
    int clipIndex,
    String status,
    String workerInstanceId,
    OffsetDateTime startedAt,
    OffsetDateTime finishedAt,
    int durationMs,
    Map<String, Object> inputSummary,
    Map<String, Object> outputSummary,
    String errorCode,
    String errorMessage
) {
    public TaskStageRunSnapshot {
        inputSummary = inputSummary == null ? new LinkedHashMap<>() : new LinkedHashMap<>(inputSummary);
        outputSummary = outputSummary == null ? new LinkedHashMap<>() : new LinkedHashMap<>(outputSummary);
    }
}
