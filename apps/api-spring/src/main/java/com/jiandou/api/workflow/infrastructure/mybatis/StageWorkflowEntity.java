package com.jiandou.api.workflow.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_stage_workflows")
public class StageWorkflowEntity {

    @TableId("workflow_id")
    private String workflowId;
    @TableField("owner_user_id")
    private Long ownerUserId;
    private String title;
    @TableField("transcript_text")
    private String transcriptText;
    @TableField("global_prompt")
    private String globalPrompt;
    @TableField("aspect_ratio")
    private String aspectRatio;
    @TableField("style_preset")
    private String stylePreset;
    @TableField("text_analysis_model")
    private String textAnalysisModel;
    @TableField("vision_model")
    private String visionModel;
    @TableField("image_model")
    private String imageModel;
    @TableField("video_model")
    private String videoModel;
    @TableField("video_size")
    private String videoSize;
    @TableField("task_seed")
    private Integer taskSeed;
    @TableField("min_duration_seconds")
    private Integer minDurationSeconds;
    @TableField("max_duration_seconds")
    private Integer maxDurationSeconds;
    private String status;
    @TableField("current_stage")
    private String currentStage;
    @TableField("selected_storyboard_version_id")
    private String selectedStoryboardVersionId;
    @TableField("final_join_asset_id")
    private String finalJoinAssetId;
    @TableField("effect_rating")
    private Integer effectRating;
    @TableField("effect_rating_note")
    private String effectRatingNote;
    @TableField("rated_at")
    private OffsetDateTime ratedAt;
    @TableField("metadata_json")
    private String metadataJson;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getWorkflowId() { return workflowId; }
    public void setWorkflowId(String workflowId) { this.workflowId = workflowId; }
    public Long getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(Long ownerUserId) { this.ownerUserId = ownerUserId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getTranscriptText() { return transcriptText; }
    public void setTranscriptText(String transcriptText) { this.transcriptText = transcriptText; }
    public String getGlobalPrompt() { return globalPrompt; }
    public void setGlobalPrompt(String globalPrompt) { this.globalPrompt = globalPrompt; }
    public String getAspectRatio() { return aspectRatio; }
    public void setAspectRatio(String aspectRatio) { this.aspectRatio = aspectRatio; }
    public String getStylePreset() { return stylePreset; }
    public void setStylePreset(String stylePreset) { this.stylePreset = stylePreset; }
    public String getTextAnalysisModel() { return textAnalysisModel; }
    public void setTextAnalysisModel(String textAnalysisModel) { this.textAnalysisModel = textAnalysisModel; }
    public String getVisionModel() { return visionModel; }
    public void setVisionModel(String visionModel) { this.visionModel = visionModel; }
    public String getImageModel() { return imageModel; }
    public void setImageModel(String imageModel) { this.imageModel = imageModel; }
    public String getVideoModel() { return videoModel; }
    public void setVideoModel(String videoModel) { this.videoModel = videoModel; }
    public String getVideoSize() { return videoSize; }
    public void setVideoSize(String videoSize) { this.videoSize = videoSize; }
    public Integer getTaskSeed() { return taskSeed; }
    public void setTaskSeed(Integer taskSeed) { this.taskSeed = taskSeed; }
    public Integer getMinDurationSeconds() { return minDurationSeconds; }
    public void setMinDurationSeconds(Integer minDurationSeconds) { this.minDurationSeconds = minDurationSeconds; }
    public Integer getMaxDurationSeconds() { return maxDurationSeconds; }
    public void setMaxDurationSeconds(Integer maxDurationSeconds) { this.maxDurationSeconds = maxDurationSeconds; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getCurrentStage() { return currentStage; }
    public void setCurrentStage(String currentStage) { this.currentStage = currentStage; }
    public String getSelectedStoryboardVersionId() { return selectedStoryboardVersionId; }
    public void setSelectedStoryboardVersionId(String selectedStoryboardVersionId) { this.selectedStoryboardVersionId = selectedStoryboardVersionId; }
    public String getFinalJoinAssetId() { return finalJoinAssetId; }
    public void setFinalJoinAssetId(String finalJoinAssetId) { this.finalJoinAssetId = finalJoinAssetId; }
    public Integer getEffectRating() { return effectRating; }
    public void setEffectRating(Integer effectRating) { this.effectRating = effectRating; }
    public String getEffectRatingNote() { return effectRatingNote; }
    public void setEffectRatingNote(String effectRatingNote) { this.effectRatingNote = effectRatingNote; }
    public OffsetDateTime getRatedAt() { return ratedAt; }
    public void setRatedAt(OffsetDateTime ratedAt) { this.ratedAt = ratedAt; }
    public String getMetadataJson() { return metadataJson; }
    public void setMetadataJson(String metadataJson) { this.metadataJson = metadataJson; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
