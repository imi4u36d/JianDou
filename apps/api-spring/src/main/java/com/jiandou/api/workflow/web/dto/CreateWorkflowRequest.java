package com.jiandou.api.workflow.web.dto;

public record CreateWorkflowRequest(
    String title,
    String transcriptText,
    String globalPrompt,
    String aspectRatio,
    String stylePreset,
    String textAnalysisModel,
    String visionModel,
    String imageModel,
    String videoModel,
    String videoSize,
    Integer seed,
    Integer minDurationSeconds,
    Integer maxDurationSeconds
) {}
