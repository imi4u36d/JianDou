package com.jiandou.api.workflow.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "工作流列表摘要")
public record WorkflowSummaryResponse(
    @Schema(description = "工作流ID") String id,
    @Schema(description = "标题") String title,
    @Schema(description = "状态") String status,
    @Schema(description = "当前阶段") String currentStage,
    @Schema(description = "画幅比例") String aspectRatio,
    @Schema(description = "效果评分") Integer effectRating,
    @Schema(description = "创建时间") String createdAt,
    @Schema(description = "更新时间") String updatedAt,
    @Schema(description = "分镜版本数") long storyboardVersionCount,
    @Schema(description = "角色卡数") long characterSheetCount,
    @Schema(description = "已选角色卡数") long selectedCharacterSheetCount,
    @Schema(description = "角色卡版本总数") long characterSheetVersionCount,
    @Schema(description = "关键帧版本数") long keyframeVersionCount,
    @Schema(description = "视频版本数") long videoVersionCount
) {}
