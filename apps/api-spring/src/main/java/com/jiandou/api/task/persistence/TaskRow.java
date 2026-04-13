package com.jiandou.api.task.persistence;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Represents the biz_tasks row and exposes the JSON payload/context blobs as maps.
 */
public record TaskRow(
    String taskId,
    String taskType,
    String title,
    String description,
    String platform,
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
    Integer taskSeed,
    Integer effectRating,
    String effectRatingNote,
    OffsetDateTime ratedAt,
    String modelProvider,
    String executionMode,
    String editingMode,
    String status,
    int progress,
    String errorCode,
    String errorMessage,
    String planJson,
    int retryCount,
    int timezoneOffsetMinutes,
    OffsetDateTime startedAt,
    OffsetDateTime finishedAt,
    OffsetDateTime createTime,
    OffsetDateTime updateTime
) {}
