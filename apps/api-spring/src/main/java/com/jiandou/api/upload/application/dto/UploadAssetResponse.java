package com.jiandou.api.upload.application.dto;

/**
 * 上传成功后的资产信息。
 */
public record UploadAssetResponse(
    String assetId,
    String fileName,
    String fileUrl,
    long sizeBytes
) {
}
