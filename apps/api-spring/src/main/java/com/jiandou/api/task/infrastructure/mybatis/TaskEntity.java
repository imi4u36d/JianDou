package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_tasks")
public class TaskEntity {

    @TableId("task_id")
    private String taskId;
    @TableField("task_type")
    private String taskType;
    @TableField
    private String title;
    @TableField
    private String description;
    @TableField
    private String platform;
    @TableField("aspect_ratio")
    private String aspectRatio;
    @TableField("min_duration_seconds")
    private Integer minDurationSeconds;
    @TableField("max_duration_seconds")
    private Integer maxDurationSeconds;
    @TableField("output_count")
    private Integer outputCount;
    @TableField("source_primary_asset_id")
    private String sourcePrimaryAssetId;
    @TableField("source_file_name")
    private String sourceFileName;
    @TableField("source_asset_ids_json")
    private String sourceAssetIdsJson;
    @TableField("source_file_names_json")
    private String sourceFileNamesJson;
    @TableField("request_payload_json")
    private String requestPayloadJson;
    @TableField("context_json")
    private String contextJson;
    @TableField("intro_template")
    private String introTemplate;
    @TableField("outro_template")
    private String outroTemplate;
    @TableField("creative_prompt")
    private String creativePrompt;
    @TableField("task_seed")
    private Integer taskSeed;
    @TableField("effect_rating")
    private Integer effectRating;
    @TableField("effect_rating_note")
    private String effectRatingNote;
    @TableField("rated_at")
    private OffsetDateTime ratedAt;
    @TableField("model_provider")
    private String modelProvider;
    @TableField("execution_mode")
    private String executionMode;
    @TableField("editing_mode")
    private String editingMode;
    @TableField
    private String status;
    @TableField
    private Integer progress;
    @TableField("error_code")
    private String errorCode;
    @TableField("error_message")
    private String errorMessage;
    @TableField("plan_json")
    private String planJson;
    @TableField("retry_count")
    private Integer retryCount;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("started_at")
    private OffsetDateTime startedAt;
    @TableField("finished_at")
    private OffsetDateTime finishedAt;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public String getTaskType() {
        return taskType;
    }

    public void setTaskType(String taskType) {
        this.taskType = taskType;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getPlatform() {
        return platform;
    }

    public void setPlatform(String platform) {
        this.platform = platform;
    }

    public String getAspectRatio() {
        return aspectRatio;
    }

    public void setAspectRatio(String aspectRatio) {
        this.aspectRatio = aspectRatio;
    }

    public Integer getMinDurationSeconds() {
        return minDurationSeconds;
    }

    public void setMinDurationSeconds(Integer minDurationSeconds) {
        this.minDurationSeconds = minDurationSeconds;
    }

    public Integer getMaxDurationSeconds() {
        return maxDurationSeconds;
    }

    public void setMaxDurationSeconds(Integer maxDurationSeconds) {
        this.maxDurationSeconds = maxDurationSeconds;
    }

    public Integer getOutputCount() {
        return outputCount;
    }

    public void setOutputCount(Integer outputCount) {
        this.outputCount = outputCount;
    }

    public String getSourcePrimaryAssetId() {
        return sourcePrimaryAssetId;
    }

    public void setSourcePrimaryAssetId(String sourcePrimaryAssetId) {
        this.sourcePrimaryAssetId = sourcePrimaryAssetId;
    }

    public String getSourceFileName() {
        return sourceFileName;
    }

    public void setSourceFileName(String sourceFileName) {
        this.sourceFileName = sourceFileName;
    }

    public String getSourceAssetIdsJson() {
        return sourceAssetIdsJson;
    }

    public void setSourceAssetIdsJson(String sourceAssetIdsJson) {
        this.sourceAssetIdsJson = sourceAssetIdsJson;
    }

    public String getSourceFileNamesJson() {
        return sourceFileNamesJson;
    }

    public void setSourceFileNamesJson(String sourceFileNamesJson) {
        this.sourceFileNamesJson = sourceFileNamesJson;
    }

    public String getRequestPayloadJson() {
        return requestPayloadJson;
    }

    public void setRequestPayloadJson(String requestPayloadJson) {
        this.requestPayloadJson = requestPayloadJson;
    }

    public String getContextJson() {
        return contextJson;
    }

    public void setContextJson(String contextJson) {
        this.contextJson = contextJson;
    }

    public String getIntroTemplate() {
        return introTemplate;
    }

    public void setIntroTemplate(String introTemplate) {
        this.introTemplate = introTemplate;
    }

    public String getOutroTemplate() {
        return outroTemplate;
    }

    public void setOutroTemplate(String outroTemplate) {
        this.outroTemplate = outroTemplate;
    }

    public String getCreativePrompt() {
        return creativePrompt;
    }

    public void setCreativePrompt(String creativePrompt) {
        this.creativePrompt = creativePrompt;
    }

    public Integer getTaskSeed() {
        return taskSeed;
    }

    public void setTaskSeed(Integer taskSeed) {
        this.taskSeed = taskSeed;
    }

    public Integer getEffectRating() {
        return effectRating;
    }

    public void setEffectRating(Integer effectRating) {
        this.effectRating = effectRating;
    }

    public String getEffectRatingNote() {
        return effectRatingNote;
    }

    public void setEffectRatingNote(String effectRatingNote) {
        this.effectRatingNote = effectRatingNote;
    }

    public OffsetDateTime getRatedAt() {
        return ratedAt;
    }

    public void setRatedAt(OffsetDateTime ratedAt) {
        this.ratedAt = ratedAt;
    }

    public String getModelProvider() {
        return modelProvider;
    }

    public void setModelProvider(String modelProvider) {
        this.modelProvider = modelProvider;
    }

    public String getExecutionMode() {
        return executionMode;
    }

    public void setExecutionMode(String executionMode) {
        this.executionMode = executionMode;
    }

    public String getEditingMode() {
        return editingMode;
    }

    public void setEditingMode(String editingMode) {
        this.editingMode = editingMode;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getProgress() {
        return progress;
    }

    public void setProgress(Integer progress) {
        this.progress = progress;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public void setErrorCode(String errorCode) {
        this.errorCode = errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public String getPlanJson() {
        return planJson;
    }

    public void setPlanJson(String planJson) {
        this.planJson = planJson;
    }

    public Integer getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(Integer retryCount) {
        this.retryCount = retryCount;
    }

    public Integer getTimezoneOffsetMinutes() {
        return timezoneOffsetMinutes;
    }

    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) {
        this.timezoneOffsetMinutes = timezoneOffsetMinutes;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(OffsetDateTime finishedAt) {
        this.finishedAt = finishedAt;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

    public Integer getIsDeleted() {
        return isDeleted;
    }

    public void setIsDeleted(Integer isDeleted) {
        this.isDeleted = isDeleted;
    }
}
