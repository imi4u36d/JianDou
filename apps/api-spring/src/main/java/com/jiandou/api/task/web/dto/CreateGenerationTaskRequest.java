package com.jiandou.api.task.web.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 创建生成任务的请求体。
 * 这里保留现有 JSON 字段形态，避免影响前端调用。
 */
public record CreateGenerationTaskRequest(
    @NotBlank String title,
    String creativePrompt,
    String aspectRatio,
    String textAnalysisModel,
    String visionModel,
    String imageModel,
    String videoModel,
    String videoSize,
    Integer seed,
    Object videoDurationSeconds,
    Object outputCount,
    Integer minDurationSeconds,
    Integer maxDurationSeconds,
    String transcriptText,
    Boolean stopBeforeVideoGeneration
) {}
