package com.jiandou.api.upload;

import com.jiandou.api.upload.application.UploadApplicationService;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v2/uploads")
public class UploadController {

    private final UploadApplicationService uploadService;

    public UploadController(UploadApplicationService uploadService) {
        this.uploadService = uploadService;
    }

    @PostMapping("/texts")
    public Map<String, Object> uploadText(@RequestParam("file") MultipartFile file) {
        return save(file, true);
    }

    @PostMapping("/videos")
    public Map<String, Object> uploadVideo(@RequestParam("file") MultipartFile file) {
        return save(file, false);
    }

    private Map<String, Object> save(MultipartFile file, boolean textUpload) {
        if (file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "上传文件不能为空");
        }
        try {
            return textUpload ? uploadService.uploadText(file) : uploadService.uploadVideo(file);
        } catch (UploadFailedException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "文件保存失败", ex);
        }
    }
}
