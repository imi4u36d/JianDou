package com.jiandou.api.upload.web;

import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.upload.application.UploadApplicationService;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import com.jiandou.api.upload.exception.EmptyUploadFileException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 上传模块 Web 入口。
 */
@RestController
@RequestMapping(ApiPathConstants.UPLOADS)
public class UploadController {

    private final UploadApplicationService uploadService;

    /**
     * 创建新的上传控制器。
     * @param uploadService 上传服务值
     */
    public UploadController(UploadApplicationService uploadService) {
        this.uploadService = uploadService;
    }

    /**
     * 上传文本。
     * @param file 待上传的文件
     * @return 处理结果
     */
    @PostMapping("/texts")
    public UploadAssetResponse uploadText(@RequestParam("file") MultipartFile file) {
        return save(file, true);
    }

    /**
     * 上传视频。
     * @param file 待上传的文件
     * @return 处理结果
     */
    @PostMapping("/videos")
    public UploadAssetResponse uploadVideo(@RequestParam("file") MultipartFile file) {
        return save(file, false);
    }

    /**
     * 保存save。
     * @param file 待上传的文件
     * @param textUpload 文本上传值
     * @return 处理结果
     */
    private UploadAssetResponse save(MultipartFile file, boolean textUpload) {
        if (file.isEmpty()) {
            throw new EmptyUploadFileException();
        }
        return textUpload ? uploadService.uploadText(file) : uploadService.uploadVideo(file);
    }
}
