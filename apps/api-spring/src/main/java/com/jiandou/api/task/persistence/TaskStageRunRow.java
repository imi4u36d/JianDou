package com.jiandou.api.task.persistence;

import java.time.OffsetDateTime;
import java.util.Map;

public record TaskStageRunRow(
    String taskStageRunId,
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
    String errorMessage,
    int timezoneOffsetMinutes,
    OffsetDateTime createTime,
    OffsetDateTime updateTime
) {}
