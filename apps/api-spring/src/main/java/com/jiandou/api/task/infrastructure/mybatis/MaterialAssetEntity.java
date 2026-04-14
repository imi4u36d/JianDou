package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_material_assets")
public class MaterialAssetEntity {

    @TableId("material_asset_id")
    private String materialAssetId;
    @TableField("task_id")
    private String taskId;
    @TableField("source_task_id")
    private String sourceTaskId;
    @TableField("source_material_id")
    private String sourceMaterialId;
    @TableField("asset_role")
    private String assetRole;
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

    public String getMaterialAssetId() { return materialAssetId; }
    public void setMaterialAssetId(String materialAssetId) { this.materialAssetId = materialAssetId; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getSourceTaskId() { return sourceTaskId; }
    public void setSourceTaskId(String sourceTaskId) { this.sourceTaskId = sourceTaskId; }
    public String getSourceMaterialId() { return sourceMaterialId; }
    public void setSourceMaterialId(String sourceMaterialId) { this.sourceMaterialId = sourceMaterialId; }
    public String getAssetRole() { return assetRole; }
    public void setAssetRole(String assetRole) { this.assetRole = assetRole; }
    public String getMediaType() { return mediaType; }
    public void setMediaType(String mediaType) { this.mediaType = mediaType; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getOriginProvider() { return originProvider; }
    public void setOriginProvider(String originProvider) { this.originProvider = originProvider; }
    public String getOriginModel() { return originModel; }
    public void setOriginModel(String originModel) { this.originModel = originModel; }
    public String getRemoteTaskId() { return remoteTaskId; }
    public void setRemoteTaskId(String remoteTaskId) { this.remoteTaskId = remoteTaskId; }
    public String getRemoteAssetId() { return remoteAssetId; }
    public void setRemoteAssetId(String remoteAssetId) { this.remoteAssetId = remoteAssetId; }
    public String getOriginalFileName() { return originalFileName; }
    public void setOriginalFileName(String originalFileName) { this.originalFileName = originalFileName; }
    public String getStoredFileName() { return storedFileName; }
    public void setStoredFileName(String storedFileName) { this.storedFileName = storedFileName; }
    public String getFileExt() { return fileExt; }
    public void setFileExt(String fileExt) { this.fileExt = fileExt; }
    public String getStorageProvider() { return storageProvider; }
    public void setStorageProvider(String storageProvider) { this.storageProvider = storageProvider; }
    public String getMimeType() { return mimeType; }
    public void setMimeType(String mimeType) { this.mimeType = mimeType; }
    public Long getSizeBytes() { return sizeBytes; }
    public void setSizeBytes(Long sizeBytes) { this.sizeBytes = sizeBytes; }
    public String getSha256() { return sha256; }
    public void setSha256(String sha256) { this.sha256 = sha256; }
    public Double getDurationSeconds() { return durationSeconds; }
    public void setDurationSeconds(Double durationSeconds) { this.durationSeconds = durationSeconds; }
    public Integer getWidth() { return width; }
    public void setWidth(Integer width) { this.width = width; }
    public Integer getHeight() { return height; }
    public void setHeight(Integer height) { this.height = height; }
    public Integer getHasAudio() { return hasAudio; }
    public void setHasAudio(Integer hasAudio) { this.hasAudio = hasAudio; }
    public String getLocalStoragePath() { return localStoragePath; }
    public void setLocalStoragePath(String localStoragePath) { this.localStoragePath = localStoragePath; }
    public String getLocalFilePath() { return localFilePath; }
    public void setLocalFilePath(String localFilePath) { this.localFilePath = localFilePath; }
    public String getPublicUrl() { return publicUrl; }
    public void setPublicUrl(String publicUrl) { this.publicUrl = publicUrl; }
    public String getThirdPartyUrl() { return thirdPartyUrl; }
    public void setThirdPartyUrl(String thirdPartyUrl) { this.thirdPartyUrl = thirdPartyUrl; }
    public String getRemoteUrl() { return remoteUrl; }
    public void setRemoteUrl(String remoteUrl) { this.remoteUrl = remoteUrl; }
    public String getMetadataJson() { return metadataJson; }
    public void setMetadataJson(String metadataJson) { this.metadataJson = metadataJson; }
    public OffsetDateTime getCapturedAt() { return capturedAt; }
    public void setCapturedAt(OffsetDateTime capturedAt) { this.capturedAt = capturedAt; }
    public Integer getTimezoneOffsetMinutes() { return timezoneOffsetMinutes; }
    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) { this.timezoneOffsetMinutes = timezoneOffsetMinutes; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
