package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import com.jiandou.api.generation.text.TextCompletionInvocation;
import com.jiandou.api.generation.text.TextModelInvocation;
import com.jiandou.api.generation.text.TextModelProvider;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import com.jiandou.api.generation.text.VisionCompletionInvocation;
import com.jiandou.api.generation.video.VideoGenerationRequest;
import com.jiandou.api.generation.video.VideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.media.LocalMediaArtifactService.StoredArtifact;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 生成运行工厂视频Async相关测试。
 */
class GenerationRunFactoryVideoAsyncTest {

    @TempDir
    Path tempDir;

    /**
     * 创建视频运行ReturnsRunningAndRefreshCompletes。
     */
    @Test
    void createVideoRunReturnsRunningAndRefreshCompletes() throws Exception {
        ModelRuntimeProfile textProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-text",
            "",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        ModelRuntimeProfile visionProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-vision",
            "",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        MediaProviderProfile videoProfile = new MediaProviderProfile(
            new MediaProviderConfig(
                "video",
                "wan2.2-i2v-plus",
                "wan",
                "wan2.2-i2v-plus",
                "k",
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
                "https://dashscope.aliyuncs.com/api/v1/tasks",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, true, false, false, 1, 120, "i2v", java.util.List.of(), java.util.List.of(6, 8, 10))
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            /**
             * 检查是否supports种子。
             * @param requestedModel requested模型值
             * @return 是否满足条件
             */
            @Override
            public boolean supportsSeed(String requestedModel) {
                return false;
            }

            /**
             * 处理解析文本Profile。
             * @param requestedModel requested模型值
             * @return 处理结果
             */
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return "gpt-vision".equals(requestedModel) ? visionProfile : textProfile;
            }

            /**
             * 处理解析视频Profile。
             * @param requestedModel requested模型值
             * @return 处理结果
             */
            @Override
            public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind) {
                return videoProfile;
            }

            /**
             * 处理值。
             * @param section section值
             * @param key key值
             * @param fallback 兜底值
             * @return 处理结果
             */
            @Override
            public String value(String section, String key, String fallback) {
                return fallback;
            }
        };
        PromptTemplateResolver promptTemplateResolver = new PromptTemplateResolver(
            new MockEnvironment(),
            modelResolver,
            new GenerationConfigPathLocator(new MockEnvironment())
        ) {
            /**
             * 处理系统提示词。
             * @param promptName 提示词Name值
             * @param key key值
             * @return 处理结果
             */
            @Override
            public String systemPrompt(String promptName, String key) {
                return "";
            }
        };
        TextModelProviderRegistry textModelProviderRegistry = new TextModelProviderRegistry(java.util.List.of(new TextModelProvider() {
            /**
             * 检查是否supports。
             * @param profile profile值
             * @return 是否满足条件
             */
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            /**
             * 处理generate。
             * @param profile profile值
             * @param invocation 调用值
             * @return 处理结果
             */
            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                if (invocation instanceof VisionCompletionInvocation) {
                    return new TextModelResponse(
                        "vision notes",
                        "https://api.example.com/v1/responses",
                        "api.example.com",
                        10,
                        true,
                        "resp_2"
                    );
                }
                TextCompletionInvocation textInvocation = (TextCompletionInvocation) invocation;
                return new TextModelResponse(
                    textInvocation.userPrompt(),
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_1"
                );
            }
        }));
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(storageProperties(tempDir), "ffmpeg");
        StoredArtifact remoteLocal = localMediaArtifactService.writeBinary("gen/_runs/source", "remote.mp4", new byte[] {1, 2, 3});
        VideoModelProvider fakeVideoModelProvider = new VideoModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request) {
                return new RemoteVideoTaskSubmission(
                    "wan",
                    request.requestedModel(),
                    request.requestedModel(),
                    "dashscope.aliyuncs.com",
                    "dashscope.aliyuncs.com",
                    "task_123",
                    "",
                    "",
                    false,
                    true,
                    request.prompt(),
                    0
                );
            }

            @Override
            public RemoteTaskQueryResult query(MediaProviderProfile profile, String taskId) {
                return new RemoteTaskQueryResult(
                    taskId,
                    "SUCCEEDED",
                    remoteLocal.publicUrl(),
                    "",
                    Map.of(
                        "output", Map.of(
                            "contents", java.util.List.of(Map.of(
                                "role", "last_frame",
                                "image_url", Map.of("url", "https://example.com/generated-last-frame.png")
                            ))
                        )
                    )
                );
            }
        };
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, modelResolver, textModelProviderRegistry);
        ImageModelProviderRegistry imageModelProviderRegistry = new ImageModelProviderRegistry(java.util.List.of());
        VideoModelProviderRegistry videoModelProviderRegistry = new VideoModelProviderRegistry(java.util.List.of(
            fakeVideoModelProvider
        ));
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelProviderRegistry,
            imageModelProviderRegistry,
            videoModelProviderRegistry,
            support
        );

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "video");
        request.put("input", Map.of(
            "prompt", "a hero enters frame",
            "videoSize", "720*1280",
            "durationSeconds", 8
        ));
        request.put("model", Map.of(
            "textAnalysisModel", "gpt-text",
            "visionModel", "gpt-vision",
            "providerModel", "wan2.2-i2v-plus"
        ));
        request.put("options", Map.of("stylePreset", "cinematic"));

        Map<String, Object> run = factory.createVideoRun("run_async_1", request);
        assertEquals("running", run.get("status"));
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals("task_123", metadata.get("taskId"));
        assertEquals("", result.get("outputUrl"));
        assertTrue(String.valueOf(result.get("negativePrompt")).contains("前0.5秒和后0.5秒"));
        assertTrue(String.valueOf(result.get("negativePrompt")).contains("物理规律"));
        assertTrue(String.valueOf(result.get("shapedPrompt")).contains("违背基本物理规律"));

        Map<String, Object> refreshed = factory.refreshVideoRun(run);
        assertEquals("succeeded", refreshed.get("status"));
        @SuppressWarnings("unchecked")
        Map<String, Object> refreshedResult = (Map<String, Object>) refreshed.get("result");
        String outputUrl = String.valueOf(refreshedResult.get("outputUrl"));
        assertTrue(outputUrl.startsWith("/storage/"));
        String outputPath = localMediaArtifactService.resolveAbsolutePath(outputUrl);
        assertFalse(outputPath.isBlank());
        assertTrue(Files.exists(Path.of(outputPath)));
        @SuppressWarnings("unchecked")
        Map<String, Object> refreshedMetadata = (Map<String, Object>) refreshedResult.get("metadata");
        assertEquals(remoteLocal.publicUrl(), refreshedMetadata.get("remoteSourceUrl"));
        assertEquals("https://example.com/generated-last-frame.png", refreshedMetadata.get("providerLastFrameUrl"));
        assertEquals("https://example.com/generated-last-frame.png", refreshedMetadata.get("lastFrameUrl"));
        assertEquals("https://example.com/generated-last-frame.png", refreshedMetadata.get("last_frame_url"));
        assertNotNull(refreshedMetadata.get("providerPayload"));
        assertNotNull(refreshedResult.get("callChain"));
    }

    private JiandouStorageProperties storageProperties(Path rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir.toString());
        return properties;
    }
}
