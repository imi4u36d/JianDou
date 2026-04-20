package com.jiandou.api.workflow.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_stage_versions")
public class StageVersionEntity {

    @TableId("stage_version_id")
    private String stageVersionId;
    @TableField("workflow_id")
    private String workflowId;
    @TableField("owner_user_id")
    private Long ownerUserId;
    @TableField("stage_type")
    private String stageType;
    @TableField("clip_index")
    private Integer clipIndex;
    @TableField("version_no")
    private Integer versionNo;
    private String title;
    private String status;
    private Integer selected;
    private Integer rating;
    @TableField("rating_note")
    private String ratingNote;
    @TableField("rated_at")
    private OffsetDateTime ratedAt;
    @TableField("parent_version_id")
    private String parentVersionId;
    @TableField("source_material_asset_id")
    private String sourceMaterialAssetId;
    @TableField("material_asset_id")
    private String materialAssetId;
    @TableField("preview_url")
    private String previewUrl;
    @TableField("download_url")
    private String downloadUrl;
    @TableField("input_summary_json")
    private String inputSummaryJson;
    @TableField("output_summary_json")
    private String outputSummaryJson;
    @TableField("model_call_summary_json")
    private String modelCallSummaryJson;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getStageVersionId() { return stageVersionId; }
    public void setStageVersionId(String stageVersionId) { this.stageVersionId = stageVersionId; }
    public String getWorkflowId() { return workflowId; }
    public void setWorkflowId(String workflowId) { this.workflowId = workflowId; }
    public Long getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(Long ownerUserId) { this.ownerUserId = ownerUserId; }
    public String getStageType() { return stageType; }
    public void setStageType(String stageType) { this.stageType = stageType; }
    public Integer getClipIndex() { return clipIndex; }
    public void setClipIndex(Integer clipIndex) { this.clipIndex = clipIndex; }
    public Integer getVersionNo() { return versionNo; }
    public void setVersionNo(Integer versionNo) { this.versionNo = versionNo; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getSelected() { return selected; }
    public void setSelected(Integer selected) { this.selected = selected; }
    public Integer getRating() { return rating; }
    public void setRating(Integer rating) { this.rating = rating; }
    public String getRatingNote() { return ratingNote; }
    public void setRatingNote(String ratingNote) { this.ratingNote = ratingNote; }
    public OffsetDateTime getRatedAt() { return ratedAt; }
    public void setRatedAt(OffsetDateTime ratedAt) { this.ratedAt = ratedAt; }
    public String getParentVersionId() { return parentVersionId; }
    public void setParentVersionId(String parentVersionId) { this.parentVersionId = parentVersionId; }
    public String getSourceMaterialAssetId() { return sourceMaterialAssetId; }
    public void setSourceMaterialAssetId(String sourceMaterialAssetId) { this.sourceMaterialAssetId = sourceMaterialAssetId; }
    public String getMaterialAssetId() { return materialAssetId; }
    public void setMaterialAssetId(String materialAssetId) { this.materialAssetId = materialAssetId; }
    public String getPreviewUrl() { return previewUrl; }
    public void setPreviewUrl(String previewUrl) { this.previewUrl = previewUrl; }
    public String getDownloadUrl() { return downloadUrl; }
    public void setDownloadUrl(String downloadUrl) { this.downloadUrl = downloadUrl; }
    public String getInputSummaryJson() { return inputSummaryJson; }
    public void setInputSummaryJson(String inputSummaryJson) { this.inputSummaryJson = inputSummaryJson; }
    public String getOutputSummaryJson() { return outputSummaryJson; }
    public void setOutputSummaryJson(String outputSummaryJson) { this.outputSummaryJson = outputSummaryJson; }
    public String getModelCallSummaryJson() { return modelCallSummaryJson; }
    public void setModelCallSummaryJson(String modelCallSummaryJson) { this.modelCallSummaryJson = modelCallSummaryJson; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
