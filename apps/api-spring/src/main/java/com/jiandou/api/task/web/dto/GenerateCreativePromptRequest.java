package com.jiandou.api.task.web.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 生成创意提示词的请求体。
 */
public record GenerateCreativePromptRequest(
    @NotBlank String title,
    String aspectRatio,
    Integer minDurationSeconds,
    Integer maxDurationSeconds,
    String introTemplate,
    String outroTemplate,
    String transcriptText
) {}
