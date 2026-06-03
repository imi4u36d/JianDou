package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.credit.application.UserCreditService;
import com.jiandou.api.credit.domain.CreditCharge;
import com.jiandou.api.credit.domain.CreditFeatureCode;
import com.jiandou.api.credit.domain.CreditTransactionContext;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.image.ImageGenerationRequest;
import com.jiandou.api.generation.image.ImageModelProvider;
import com.jiandou.api.generation.image.ImageModelProviderRegistry;
import com.jiandou.api.generation.orchestration.GenerationRunFactory;
import com.jiandou.api.generation.orchestration.GenerationRunSupport;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.PromptTemplateResolver;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import com.jiandou.api.generation.video.VideoGenerationRequest;
import com.jiandou.api.generation.video.VideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationRunFactoryCreditTest {

    @TempDir
    Path tempDir;

    @Test
    void imageRunRefundsCreditsWhenProviderFails() {
        UserCreditService creditService = mock(UserCreditService.class);
        CreditCharge charge = new CreditCharge(true, 9L, CreditFeatureCode.IMAGE_GENERATION, 10, 50, 40, "credit_image");
        when(creditService.charge(eq(9L), eq(CreditFeatureCode.IMAGE_GENERATION), eq("run_image_fail"), any(CreditTransactionContext.class)))
            .thenReturn(charge);
        ImageModelProvider imageProvider = new ImageModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteImageGenerationResult generate(MediaProviderProfile profile, ImageGenerationRequest request) {
                throw new GenerationProviderException("image provider failed");
            }
        };
        GenerationRunFactory factory = factory(creditService, imageProvider, null);

        assertThrows(GenerationProviderException.class, () -> factory.createImageRun("run_image_fail", imageRequest(9L)));

        verify(creditService).refund(eq(charge), any(CreditTransactionContext.class));
    }

    @Test
    void videoRunRefundsCreditsWhenSubmitFails() {
        UserCreditService creditService = mock(UserCreditService.class);
        CreditCharge charge = new CreditCharge(true, 9L, CreditFeatureCode.VIDEO_GENERATION, 50, 50, 0, "credit_video_fail");
        when(creditService.charge(eq(9L), eq(CreditFeatureCode.VIDEO_GENERATION), eq("run_video_fail"), any(CreditTransactionContext.class)))
            .thenReturn(charge);
        VideoModelProvider videoProvider = new VideoModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request) {
                throw new GenerationProviderException("video submit failed");
            }

            @Override
            public RemoteTaskQueryResult query(MediaProviderProfile profile, String remoteTaskId) {
                throw new AssertionError("query should not be called");
            }
        };
        GenerationRunFactory factory = factory(creditService, null, videoProvider);

        assertThrows(GenerationProviderException.class, () -> factory.createVideoRun("run_video_fail", videoRequest(9L)));

        verify(creditService).refund(eq(charge), any(CreditTransactionContext.class));
    }

    @Test
    void videoRunKeepsChargeAfterSuccessfulSubmit() {
        UserCreditService creditService = mock(UserCreditService.class);
        CreditCharge charge = new CreditCharge(true, 9L, CreditFeatureCode.VIDEO_GENERATION, 50, 50, 0, "credit_video_ok");
        when(creditService.charge(eq(9L), eq(CreditFeatureCode.VIDEO_GENERATION), eq("run_video_ok"), any(CreditTransactionContext.class)))
            .thenReturn(charge);
        VideoModelProvider videoProvider = new VideoModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request) {
                return new RemoteVideoTaskSubmission(
                    "seedance",
                    request.requestedModel(),
                    request.requestedModel(),
                    "video.example.com",
                    "video.example.com",
                    "remote_task_1",
                    request.firstFrameUrl(),
                    request.lastFrameUrl(),
                    request.returnLastFrame(),
                    request.generateAudio(),
                    request.prompt(),
                    0
                );
            }

            @Override
            public RemoteTaskQueryResult query(MediaProviderProfile profile, String remoteTaskId) {
                throw new AssertionError("query should not be called");
            }
        };
        GenerationRunFactory factory = factory(creditService, null, videoProvider);

        Map<String, Object> run = factory.createVideoRun("run_video_ok", videoRequest(9L));

        assertEquals("running", run.get("status"));
        Map<String, Object> metadata = mapValue(mapValue(run.get("result")).get("metadata"));
        assertEquals("remote_task_1", metadata.get("taskId"));
        assertEquals("task_9", metadata.get("relatedTaskId"));
        assertEquals("credit_video_ok", metadata.get("creditTransactionId"));
        verify(creditService, never()).refund(any(), any());
    }

    private GenerationRunFactory factory(
        UserCreditService creditService,
        ImageModelProvider imageProvider,
        VideoModelProvider videoProvider
    ) {
        ModelRuntimeProfile textProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-text",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        MediaProviderProfile imageProfile = new MediaProviderProfile(
            new MediaProviderConfig("image", "gpt-image-2", "image-provider", "gpt-image-2", "k", "https://api.example.com/images", "", 60, "test"),
            new MediaProviderCapabilities(false, false, false, false, 5, 120, "", List.of(), List.of(), false)
        );
        MediaProviderProfile videoProfile = new MediaProviderProfile(
            new MediaProviderConfig("video", "seedance-v1", "seedance", "seedance-v1", "k", "https://api.example.com/videos", "https://api.example.com/tasks", 60, "test"),
            new MediaProviderCapabilities(false, true, false, false, 5, 120, "i2v", List.of(), List.of(8), false)
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel, Long userId) {
                return textProfile;
            }

            @Override
            public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind, Long userId) {
                return GenerationModelKinds.VIDEO.equals(expectedKind) ? videoProfile : imageProfile;
            }

            @Override
            public String value(String section, String key, String fallback) {
                return fallback;
            }
        };
        TextModelProviderRegistry textRegistry = new TextModelProviderRegistry(List.of());
        PromptTemplateResolver promptTemplateResolver = new PromptTemplateResolver(
            new MockEnvironment(),
            modelResolver,
            new GenerationConfigPathLocator(new MockEnvironment())
        );
        JiandouStorageProperties storageProperties = new JiandouStorageProperties();
        storageProperties.setRootDir(tempDir.toString());
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        GenerationRunSupport support = new GenerationRunSupport(
            new LocalMediaArtifactService(storageProperties, "ffmpeg"),
            textRegistry
        );
        return new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textRegistry,
            new ImageModelProviderRegistry(imageProvider == null ? List.of() : List.of(imageProvider)),
            new VideoModelProviderRegistry(videoProvider == null ? List.of() : List.of(videoProvider)),
            support,
            creditService
        );
    }

    private Map<String, Object> imageRequest(Long userId) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "image");
        request.put("auth", Map.of("userId", userId));
        request.put("input", Map.of("prompt", "生成雨夜街角关键帧", "width", 720, "height", 1280));
        request.put("model", Map.of("textAnalysisModel", "gpt-text", "providerModel", "gpt-image-2"));
        request.put("metadata", Map.of("relatedTaskId", "task_" + userId));
        request.put("storage", Map.of("requireRemoteSourceUrl", false));
        return request;
    }

    private Map<String, Object> videoRequest(Long userId) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "video");
        request.put("auth", Map.of("userId", userId));
        request.put("input", Map.of(
            "prompt", "a hero enters frame",
            "videoSize", "720*1280",
            "durationSeconds", 8,
            "firstFrameUrl", "https://cdn.example.com/clip1-first.png"
        ));
        request.put("model", Map.of("textAnalysisModel", "gpt-text", "providerModel", "seedance-v1"));
        request.put("metadata", Map.of("relatedTaskId", "task_" + userId));
        return request;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }
}
