package com.jiandou.api.task.domain;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record TaskAggregate(
    String taskId,
    String taskType,
    String title,
    String description,
    String aspectRatio,
    int minDurationSeconds,
    int maxDurationSeconds,
    int outputCount,
    String sourcePrimaryAssetId,
    String sourceFileName,
    List<String> sourceAssetIds,
    List<String> sourceFileNames,
    Map<String, Object> requestPayload,
    Map<String, Object> context,
    String introTemplate,
    String outroTemplate,
    String creativePrompt,
    String modelProvider,
    String executionMode,
    String editingMode,
    TaskStatus status,
    int progress,
    String errorCode,
    String errorMessage,
    String planJson,
    int retryCount,
    int timezoneOffsetMinutes,
    OffsetDateTime startedAt,
    OffsetDateTime finishedAt,
    List<TaskAttemptSnapshot> attempts,
    List<TaskStageRunSnapshot> stageRuns
) {
    public TaskAggregate {
        sourceAssetIds = sourceAssetIds == null ? new ArrayList<>() : new ArrayList<>(sourceAssetIds);
        sourceFileNames = sourceFileNames == null ? new ArrayList<>() : new ArrayList<>(sourceFileNames);
        requestPayload = requestPayload == null ? new LinkedHashMap<>() : new LinkedHashMap<>(requestPayload);
        context = context == null ? new LinkedHashMap<>() : new LinkedHashMap<>(context);
        attempts = attempts == null ? new ArrayList<>() : new ArrayList<>(attempts);
        stageRuns = stageRuns == null ? new ArrayList<>() : new ArrayList<>(stageRuns);
    }
}
