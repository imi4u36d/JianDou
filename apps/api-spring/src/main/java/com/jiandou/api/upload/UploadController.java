package com.jiandou.api.upload;

import com.jiandou.api.upload.application.UploadApplicationService;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 上传模块 Web 入口。
 */
@RestController
@RequestMapping("/api/v2/uploads")
public class UploadController {

    private final UploadApplicationService uploadService;

    public UploadController(UploadApplicationService uploadService) {
        this.uploadService = uploadService;
    }

    @PostMapping("/texts")
    public UploadAssetResponse uploadText(@RequestParam("file") MultipartFile file) {
        return save(file, true);
    }

    @PostMapping("/videos")
    public UploadAssetResponse uploadVideo(@RequestParam("file") MultipartFile file) {
        return save(file, false);
    }

    private UploadAssetResponse save(MultipartFile file, boolean textUpload) {
        if (file.isEmpty()) {
            throw new EmptyUploadFileException();
        }
        return textUpload ? uploadService.uploadText(file) : uploadService.uploadVideo(file);
    }
}
