package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_task_results")
public class TaskResultEntity {

    @TableId("task_result_id")
    private String taskResultId;
    @TableField("task_id")
    private String taskId;
    @TableField("result_type")
    private String resultType;
    @TableField("clip_index")
    private Integer clipIndex;
    private String title;
    private String reason;
    @TableField("source_model_call_id")
    private String sourceModelCallId;
    @TableField("material_asset_id")
    private String materialAssetId;
    @TableField("start_seconds")
    private Double startSeconds;
    @TableField("end_seconds")
    private Double endSeconds;
    @TableField("duration_seconds")
    private Double durationSeconds;
    @TableField("preview_path")
    private String previewPath;
    @TableField("download_path")
    private String downloadPath;
    private Integer width;
    private Integer height;
    @TableField("mime_type")
    private String mimeType;
    @TableField("size_bytes")
    private Long sizeBytes;
    @TableField("remote_url")
    private String remoteUrl;
    @TableField("extra_json")
    private String extraJson;
    @TableField("produced_at")
    private OffsetDateTime producedAt;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskResultId() { return taskResultId; }
    public void setTaskResultId(String taskResultId) { this.taskResultId = taskResultId; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getResultType() { return resultType; }
    public void setResultType(String resultType) { this.resultType = resultType; }
    public Integer getClipIndex() { return clipIndex; }
    public void setClipIndex(Integer clipIndex) { this.clipIndex = clipIndex; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
    public String getSourceModelCallId() { return sourceModelCallId; }
    public void setSourceModelCallId(String sourceModelCallId) { this.sourceModelCallId = sourceModelCallId; }
    public String getMaterialAssetId() { return materialAssetId; }
    public void setMaterialAssetId(String materialAssetId) { this.materialAssetId = materialAssetId; }
    public Double getStartSeconds() { return startSeconds; }
    public void setStartSeconds(Double startSeconds) { this.startSeconds = startSeconds; }
    public Double getEndSeconds() { return endSeconds; }
    public void setEndSeconds(Double endSeconds) { this.endSeconds = endSeconds; }
    public Double getDurationSeconds() { return durationSeconds; }
    public void setDurationSeconds(Double durationSeconds) { this.durationSeconds = durationSeconds; }
    public String getPreviewPath() { return previewPath; }
    public void setPreviewPath(String previewPath) { this.previewPath = previewPath; }
    public String getDownloadPath() { return downloadPath; }
    public void setDownloadPath(String downloadPath) { this.downloadPath = downloadPath; }
    public Integer getWidth() { return width; }
    public void setWidth(Integer width) { this.width = width; }
    public Integer getHeight() { return height; }
    public void setHeight(Integer height) { this.height = height; }
    public String getMimeType() { return mimeType; }
    public void setMimeType(String mimeType) { this.mimeType = mimeType; }
    public Long getSizeBytes() { return sizeBytes; }
    public void setSizeBytes(Long sizeBytes) { this.sizeBytes = sizeBytes; }
    public String getRemoteUrl() { return remoteUrl; }
    public void setRemoteUrl(String remoteUrl) { this.remoteUrl = remoteUrl; }
    public String getExtraJson() { return extraJson; }
    public void setExtraJson(String extraJson) { this.extraJson = extraJson; }
    public OffsetDateTime getProducedAt() { return producedAt; }
    public void setProducedAt(OffsetDateTime producedAt) { this.producedAt = producedAt; }
    public Integer getTimezoneOffsetMinutes() { return timezoneOffsetMinutes; }
    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) { this.timezoneOffsetMinutes = timezoneOffsetMinutes; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
