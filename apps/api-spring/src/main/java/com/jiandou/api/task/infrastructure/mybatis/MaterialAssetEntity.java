package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

/**
 * 素材素材持久化实体。
 */
@TableName("biz_material_assets")
public class MaterialAssetEntity {

    @TableId("material_asset_id")
    private String materialAssetId;
    @TableField("owner_user_id")
    private Long ownerUserId;
    @TableField("task_id")
    private String taskId;
    @TableField("workflow_id")
    private String workflowId;
    @TableField("source_task_id")
    private String sourceTaskId;
    @TableField("source_material_id")
    private String sourceMaterialId;
    @TableField("asset_role")
    private String assetRole;
    @TableField("stage_type")
    private String stageType;
    @TableField("clip_index")
    private Integer clipIndex;
    @TableField("version_no")
    private Integer versionNo;
    @TableField("selected_for_next")
    private Integer selectedForNext;
    @TableField("user_rating")
    private Integer userRating;
    @TableField("rating_note")
    private String ratingNote;
    @TableField("media_type")
    private String mediaType;
    private String title;
    @TableField("origin_provider")
    private String originProvider;
    @TableField("origin_model")
    private String originModel;
    @TableField("remote_task_id")
    private String remoteTaskId;
    @TableField("remote_asset_id")
    private String remoteAssetId;
    @TableField("original_file_name")
    private String originalFileName;
    @TableField("stored_file_name")
    private String storedFileName;
    @TableField("file_ext")
    private String fileExt;
    @TableField("storage_provider")
    private String storageProvider;
    @TableField("mime_type")
    private String mimeType;
    @TableField("size_bytes")
    private Long sizeBytes;
    private String sha256;
    @TableField("duration_seconds")
    private Double durationSeconds;
    private Integer width;
    private Integer height;
    @TableField("has_audio")
    private Integer hasAudio;
    @TableField("local_storage_path")
    private String localStoragePath;
    @TableField("local_file_path")
    private String localFilePath;
    @TableField("public_url")
    private String publicUrl;
    @TableField("third_party_url")
    private String thirdPartyUrl;
    @TableField("remote_url")
    private String remoteUrl;
    @TableField("metadata_json")
    private String metadataJson;
    @TableField("captured_at")
    private OffsetDateTime capturedAt;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    /**
     * 返回素材素材标识。
     * @return 处理结果
     */
    public String getMaterialAssetId() { return materialAssetId; }
    public void setMaterialAssetId(String materialAssetId) { this.materialAssetId = materialAssetId; }
    public Long getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(Long ownerUserId) { this.ownerUserId = ownerUserId; }
    /**
     * 返回任务标识。
     * @return 处理结果
     */
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getWorkflowId() { return workflowId; }
    public void setWorkflowId(String workflowId) { this.workflowId = workflowId; }
    /**
     * 返回来源任务标识。
     * @return 处理结果
     */
    public String getSourceTaskId() { return sourceTaskId; }
    public void setSourceTaskId(String sourceTaskId) { this.sourceTaskId = sourceTaskId; }
    /**
     * 返回来源素材标识。
     * @return 处理结果
     */
    public String getSourceMaterialId() { return sourceMaterialId; }
    public void setSourceMaterialId(String sourceMaterialId) { this.sourceMaterialId = sourceMaterialId; }
    /**
     * 返回素材Role。
     * @return 处理结果
     */
    public String getAssetRole() { return assetRole; }
    public void setAssetRole(String assetRole) { this.assetRole = assetRole; }
    public String getStageType() { return stageType; }
    public void setStageType(String stageType) { this.stageType = stageType; }
    public Integer getClipIndex() { return clipIndex; }
    public void setClipIndex(Integer clipIndex) { this.clipIndex = clipIndex; }
    public Integer getVersionNo() { return versionNo; }
    public void setVersionNo(Integer versionNo) { this.versionNo = versionNo; }
    public Integer getSelectedForNext() { return selectedForNext; }
    public void setSelectedForNext(Integer selectedForNext) { this.selectedForNext = selectedForNext; }
    public Integer getUserRating() { return userRating; }
    public void setUserRating(Integer userRating) { this.userRating = userRating; }
    public String getRatingNote() { return ratingNote; }
    public void setRatingNote(String ratingNote) { this.ratingNote = ratingNote; }
    /**
     * 返回媒体类型。
     * @return 处理结果
     */
    public String getMediaType() { return mediaType; }
    public void setMediaType(String mediaType) { this.mediaType = mediaType; }
    /**
     * 返回Title。
     * @return 处理结果
     */
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    /**
     * 返回OriginProvider。
     * @return 处理结果
     */
    public String getOriginProvider() { return originProvider; }
    public void setOriginProvider(String originProvider) { this.originProvider = originProvider; }
    /**
     * 返回Origin模型。
     * @return 处理结果
     */
    public String getOriginModel() { return originModel; }
    public void setOriginModel(String originModel) { this.originModel = originModel; }
    /**
     * 返回远程任务标识。
     * @return 处理结果
     */
    public String getRemoteTaskId() { return remoteTaskId; }
    public void setRemoteTaskId(String remoteTaskId) { this.remoteTaskId = remoteTaskId; }
    /**
     * 返回远程素材标识。
     * @return 处理结果
     */
    public String getRemoteAssetId() { return remoteAssetId; }
    public void setRemoteAssetId(String remoteAssetId) { this.remoteAssetId = remoteAssetId; }
    /**
     * 返回Original文件Name。
     * @return 处理结果
     */
    public String getOriginalFileName() { return originalFileName; }
    public void setOriginalFileName(String originalFileName) { this.originalFileName = originalFileName; }
    /**
     * 返回Stored文件Name。
     * @return 处理结果
     */
    public String getStoredFileName() { return storedFileName; }
    public void setStoredFileName(String storedFileName) { this.storedFileName = storedFileName; }
    /**
     * 返回文件Ext。
     * @return 处理结果
     */
    public String getFileExt() { return fileExt; }
    public void setFileExt(String fileExt) { this.fileExt = fileExt; }
    /**
     * 返回StorageProvider。
     * @return 处理结果
     */
    public String getStorageProvider() { return storageProvider; }
    public void setStorageProvider(String storageProvider) { this.storageProvider = storageProvider; }
    /**
     * 返回Mime类型。
     * @return 处理结果
     */
    public String getMimeType() { return mimeType; }
    public void setMimeType(String mimeType) { this.mimeType = mimeType; }
    /**
     * 返回SizeBytes。
     * @return 处理结果
     */
    public Long getSizeBytes() { return sizeBytes; }
    public void setSizeBytes(Long sizeBytes) { this.sizeBytes = sizeBytes; }
    /**
     * 返回Sha256。
     * @return 处理结果
     */
    public String getSha256() { return sha256; }
    public void setSha256(String sha256) { this.sha256 = sha256; }
    /**
     * 返回时长Seconds。
     * @return 处理结果
     */
    public Double getDurationSeconds() { return durationSeconds; }
    public void setDurationSeconds(Double durationSeconds) { this.durationSeconds = durationSeconds; }
    /**
     * 返回Width。
     * @return 处理结果
     */
    public Integer getWidth() { return width; }
    public void setWidth(Integer width) { this.width = width; }
    /**
     * 返回Height。
     * @return 处理结果
     */
    public Integer getHeight() { return height; }
    public void setHeight(Integer height) { this.height = height; }
    /**
     * 返回HasAudio。
     * @return 处理结果
     */
    public Integer getHasAudio() { return hasAudio; }
    public void setHasAudio(Integer hasAudio) { this.hasAudio = hasAudio; }
    /**
     * 返回本地Storage路径。
     * @return 处理结果
     */
    public String getLocalStoragePath() { return localStoragePath; }
    public void setLocalStoragePath(String localStoragePath) { this.localStoragePath = localStoragePath; }
    /**
     * 返回本地文件路径。
     * @return 处理结果
     */
    public String getLocalFilePath() { return localFilePath; }
    public void setLocalFilePath(String localFilePath) { this.localFilePath = localFilePath; }
    /**
     * 返回PublicURL。
     * @return 处理结果
     */
    public String getPublicUrl() { return publicUrl; }
    public void setPublicUrl(String publicUrl) { this.publicUrl = publicUrl; }
    /**
     * 返回ThirdPartyURL。
     * @return 处理结果
     */
    public String getThirdPartyUrl() { return thirdPartyUrl; }
    public void setThirdPartyUrl(String thirdPartyUrl) { this.thirdPartyUrl = thirdPartyUrl; }
    /**
     * 返回远程URL。
     * @return 处理结果
     */
    public String getRemoteUrl() { return remoteUrl; }
    public void setRemoteUrl(String remoteUrl) { this.remoteUrl = remoteUrl; }
    /**
     * 返回MetadataJson。
     * @return 处理结果
     */
    public String getMetadataJson() { return metadataJson; }
    public void setMetadataJson(String metadataJson) { this.metadataJson = metadataJson; }
    /**
     * 返回CapturedAt。
     * @return 处理结果
     */
    public OffsetDateTime getCapturedAt() { return capturedAt; }
    public void setCapturedAt(OffsetDateTime capturedAt) { this.capturedAt = capturedAt; }
    /**
     * 返回TimezoneOffsetMinutes。
     * @return 处理结果
     */
    public Integer getTimezoneOffsetMinutes() { return timezoneOffsetMinutes; }
    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) { this.timezoneOffsetMinutes = timezoneOffsetMinutes; }
    /**
     * 返回Create时间。
     * @return 处理结果
     */
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    /**
     * 返回Update时间。
     * @return 处理结果
     */
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    /**
     * 返回IsDeleted。
     * @return 处理结果
     */
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
