package com.jiandou.api.upload;

import com.jiandou.api.upload.application.UploadApplicationService;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Service
public class DefaultUploadApplicationService implements UploadApplicationService {

    private final Path uploadsDir;

    public DefaultUploadApplicationService(@Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot) {
        this.uploadsDir = Paths.get(storageRoot).toAbsolutePath().normalize().resolve("uploads");
    }

    @Override
    public Map<String, Object> uploadText(MultipartFile file) {
        return saveFile(file);
    }

    @Override
    public Map<String, Object> uploadVideo(MultipartFile file) {
        return saveFile(file);
    }

    private Map<String, Object> saveFile(MultipartFile file) {
        try {
            Files.createDirectories(uploadsDir);
            String assetId = "asset_" + UUID.randomUUID().toString().replace("-", "");
            String originalName = StringUtils.hasText(file.getOriginalFilename()) ? file.getOriginalFilename() : "upload.bin";
            String storedName = assetId + "_" + originalName.replaceAll("[^A-Za-z0-9._-]+", "_");
            Path target = uploadsDir.resolve(storedName).normalize();
            file.transferTo(target);
            return Map.of(
                "assetId", assetId,
                "fileName", originalName,
                "fileUrl", "/storage/uploads/" + storedName,
                "sizeBytes", Files.size(target)
            );
        } catch (IOException ex) {
            throw new UploadFailedException("文件保存失败", ex);
        }
    }
}
