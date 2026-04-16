package com.jiandou.api.upload.application;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import com.jiandou.api.upload.exception.UploadFailedException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

/**
 * 默认上传服务实现。
 * 当前直接落盘到本地存储目录，后续如果接入对象存储也可以在这里替换。
 */
@Service
public class DefaultUploadApplicationService implements UploadApplicationService {

    private final JiandouStorageProperties storageProperties;
    private final Path uploadsDir;

    /**
     * 创建新的默认上传应用服务。
     * @param storageRoot storageRoot值
     */
    public DefaultUploadApplicationService(JiandouStorageProperties storageProperties) {
        this.storageProperties = storageProperties;
        this.uploadsDir = storageProperties.resolveUploadsDir();
    }

    /**
     * 上传文本。
     * @param file 待上传的文件
     * @return 处理结果
     */
    @Override
    public UploadAssetResponse uploadText(MultipartFile file) {
        return saveFile(file);
    }

    /**
     * 上传视频。
     * @param file 待上传的文件
     * @return 处理结果
     */
    @Override
    public UploadAssetResponse uploadVideo(MultipartFile file) {
        return saveFile(file);
    }

    /**
     * 上传接口统一通过该方法生成资产标识、清洗文件名并写入磁盘。
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
                storageProperties.buildPublicUrl(storageProperties.getUploadsDir() + "/" + storedName),
                Files.size(target)
            );
        } catch (IOException ex) {
            throw new UploadFailedException("文件保存失败", ex);
        }
    }
}
