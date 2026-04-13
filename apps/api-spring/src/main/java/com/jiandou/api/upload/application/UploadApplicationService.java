package com.jiandou.api.upload.application;

import java.util.Map;
import org.springframework.web.multipart.MultipartFile;

public interface UploadApplicationService {

    Map<String, Object> uploadText(MultipartFile file);

    Map<String, Object> uploadVideo(MultipartFile file);
}
