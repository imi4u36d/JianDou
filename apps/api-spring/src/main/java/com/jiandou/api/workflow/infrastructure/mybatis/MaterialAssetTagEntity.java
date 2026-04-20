package com.jiandou.api.workflow.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_material_asset_tags")
public class MaterialAssetTagEntity {

    @TableId("asset_tag_id")
    private String assetTagId;
    @TableField("material_asset_id")
    private String materialAssetId;
    @TableField("tag_type")
    private String tagType;
    @TableField("tag_key")
    private String tagKey;
    @TableField("tag_value")
    private String tagValue;
    @TableField("is_deleted")
    private Integer isDeleted;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;

    public String getAssetTagId() { return assetTagId; }
    public void setAssetTagId(String assetTagId) { this.assetTagId = assetTagId; }
    public String getMaterialAssetId() { return materialAssetId; }
    public void setMaterialAssetId(String materialAssetId) { this.materialAssetId = materialAssetId; }
    public String getTagType() { return tagType; }
    public void setTagType(String tagType) { this.tagType = tagType; }
    public String getTagKey() { return tagKey; }
    public void setTagKey(String tagKey) { this.tagKey = tagKey; }
    public String getTagValue() { return tagValue; }
    public void setTagValue(String tagValue) { this.tagValue = tagValue; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
}
