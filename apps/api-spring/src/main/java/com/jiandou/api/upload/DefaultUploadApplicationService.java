package com.jiandou.api.upload;

import com.jiandou.api.upload.application.UploadApplicationService;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

/**
 * 默认上传服务实现。
 * 当前直接落盘到本地存储目录，后续如果接入对象存储也可以在这里替换。
 */
@Service
public class DefaultUploadApplicationService implements UploadApplicationService {

    private final Path uploadsDir;

    public DefaultUploadApplicationService(@Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot) {
        this.uploadsDir = Paths.get(storageRoot).toAbsolutePath().normalize().resolve("uploads");
    }

    @Override
    public UploadAssetResponse uploadText(MultipartFile file) {
        return saveFile(file);
    }

    @Override
    public UploadAssetResponse uploadVideo(MultipartFile file) {
        return saveFile(file);
    }

    /**
     * 上传接口统一通过该方法生成资产 ID、清洗文件名并写入磁盘。
     */
    private UploadAssetResponse saveFile(MultipartFile file) {
        try {
            Files.createDirectories(uploadsDir);
            String assetId = "asset_" + UUID.randomUUID().toString().replace("-", "");
            String originalName = StringUtils.hasText(file.getOriginalFilename()) ? file.getOriginalFilename() : "upload.bin";
            String storedName = assetId + "_" + originalName.replaceAll("[^A-Za-z0-9._-]+", "_");
            Path target = uploadsDir.resolve(storedName).normalize();
            file.transferTo(target);
            return new UploadAssetResponse(
                assetId,
                originalName,
                "/storage/uploads/" + storedName,
                Files.size(target)
            );
        } catch (IOException ex) {
            throw new UploadFailedException("文件保存失败", ex);
        }
    }
}
