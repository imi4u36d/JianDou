package com.jiandou.api.upload.application;

import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import org.springframework.web.multipart.MultipartFile;

/**
 * 上传应用服务边界。
 */
public interface UploadApplicationService {

    UploadAssetResponse uploadText(MultipartFile file);

    UploadAssetResponse uploadVideo(MultipartFile file);
}
