package com.jiandou.api.upload.web;

import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.upload.application.UploadApplicationService;
import com.jiandou.api.upload.application.dto.UploadAssetResponse;
import com.jiandou.api.upload.exception.EmptyUploadFileException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

class UploadControllerTest {

    @Test
    void uploadTextDelegatesToApplicationService() {
        UploadApplicationService service = mock(UploadApplicationService.class);
        UploadController controller = new UploadController(service);
        MockMultipartFile file = new MockMultipartFile("file", "a.txt", "text/plain", "a".getBytes());
        UploadAssetResponse response = new UploadAssetResponse("asset_1", "a.txt", "/storage/uploads/a.txt", 1L);
        when(service.uploadText(file)).thenReturn(response);

        assertSame(response, controller.uploadText(file));
        verify(service).uploadText(file);
    }

    @Test
    void uploadVideoRejectsEmptyFile() {
        UploadApplicationService service = mock(UploadApplicationService.class);
        UploadController controller = new UploadController(service);
        MockMultipartFile file = new MockMultipartFile("file", "empty.mp4", "video/mp4", new byte[0]);

        assertThrows(EmptyUploadFileException.class, () -> controller.uploadVideo(file));
    }
}
