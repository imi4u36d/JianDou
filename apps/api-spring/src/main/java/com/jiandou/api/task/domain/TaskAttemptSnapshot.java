package com.jiandou.api.task.domain;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

public record TaskAttemptSnapshot(
    String attemptId,
    String taskId,
    int attemptNo,
    String triggerType,
    TaskStatus status,
    String queueName,
    String workerInstanceId,
    OffsetDateTime queueEnteredAt,
    OffsetDateTime queueLeftAt,
    OffsetDateTime claimedAt,
    OffsetDateTime startedAt,
    OffsetDateTime finishedAt,
    String resumeFromStage,
    int resumeFromClipIndex,
    String failureCode,
    String failureMessage,
    Map<String, Object> payload
) {
    public TaskAttemptSnapshot {
        payload = payload == null ? new LinkedHashMap<>() : new LinkedHashMap<>(payload);
    }
}
