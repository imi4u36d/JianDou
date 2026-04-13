package com.jiandou.api.task.persistence;

import java.time.OffsetDateTime;
import java.util.Map;

public record TaskStatusHistoryRow(
    String taskStatusHistoryId,
    String taskId,
    String previousStatus,
    String currentStatus,
    int progress,
    String stage,
    String event,
    String message,
    Map<String, Object> payload,
    OffsetDateTime changeTime,
    String operatorType,
    String operatorId,
    int timezoneOffsetMinutes,
    OffsetDateTime createTime,
    OffsetDateTime updateTime
) {}
