package com.jiandou.api.upload.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import com.jiandou.api.upload.exception.UploadFailedException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

class DefaultUploadApplicationServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void uploadTextStoresFileOnDiskAndBuildsPublicUrl() throws Exception {
        DefaultUploadApplicationService service = new DefaultUploadApplicationService(storageProperties());
        MockMultipartFile file = new MockMultipartFile("file", "My Demo 视频.txt", "text/plain", "hello".getBytes());

        UploadAssetResponse response = service.uploadText(file);

        assertTrue(response.assetId().startsWith("asset_"));
        assertEquals("My Demo 视频.txt", response.fileName());
        assertTrue(response.fileUrl().startsWith("/storage/uploads/" + response.assetId() + "_"));
        assertEquals(5L, response.sizeBytes());
        List<Path> storedFiles = Files.list(tempDir.resolve("uploads")).toList();
        assertEquals(1, storedFiles.size());
        assertTrue(storedFiles.get(0).getFileName().toString().contains("My_Demo_.txt"));
        assertEquals("hello", Files.readString(storedFiles.get(0)));
    }

    @Test
    void uploadVideoWrapsIoFailures() throws Exception {
        DefaultUploadApplicationService service = new DefaultUploadApplicationService(storageProperties());
        MultipartFile file = mock(MultipartFile.class);
        when(file.getOriginalFilename()).thenReturn("video.mp4");
        doThrow(new IOException("disk full")).when(file).transferTo(any(Path.class));

        UploadFailedException ex = assertThrows(UploadFailedException.class, () -> service.uploadVideo(file));

        assertEquals("UPLOAD_SAVE_FAILED", ex.code());
        assertEquals("文件保存失败", ex.getMessage());
    }

    private JiandouStorageProperties storageProperties() {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(tempDir.toString());
        return properties;
    }
}
