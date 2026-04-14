package com.jiandou.api.task.persistence;

import java.time.OffsetDateTime;
import java.util.Map;

public record TaskAttemptRow(
    String taskAttemptId,
    String taskId,
    int attemptNo,
    String triggerType,
    String status,
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
    Map<String, Object> payload,
    int timezoneOffsetMinutes,
    OffsetDateTime createTime,
    OffsetDateTime updateTime
) {}
