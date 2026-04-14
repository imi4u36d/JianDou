package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.media.LocalMediaArtifactService.StoredArtifact;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationRunFactoryVideoAsyncTest {

    @TempDir
    Path tempDir;

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
            "wan",
            "wan2.2-i2v-plus",
            "k",
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            "https://dashscope.aliyuncs.com/api/v1/tasks",
            60,
            1,
            120,
            true,
            false,
            false,
            "test"
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            @Override
            public boolean supportsSeed(String requestedModel) {
                return false;
            }

            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return "gpt-vision".equals(requestedModel) ? visionProfile : textProfile;
            }

            @Override
            public MediaProviderProfile resolveVideoProfile(String requestedModel) {
                return videoProfile;
            }

            @Override
            public Map<String, String> section(String sectionName) {
                return Map.of("supported_durations", "6,8,10");
            }

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
            @Override
            public String systemPrompt(String promptName, String key) {
                return "";
            }
        };
        CompatibleTextModelClient textModelClient = new CompatibleTextModelClient(new ObjectMapper(), java.util.List.of()) {
            @Override
            public TextModelResponse generateText(
                ModelRuntimeProfile profile,
                String systemPrompt,
                String userPrompt,
                double temperature,
                int maxTokens
            ) {
                return new TextModelResponse(
                    "rewritten prompt",
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_1"
                );
            }

            @Override
            public TextModelResponse generateVisionText(
                ModelRuntimeProfile profile,
                String systemPrompt,
                String userPrompt,
                java.util.List<String> imageUrls,
                double temperature,
                int maxTokens,
                Integer seed
            ) {
                return new TextModelResponse(
                    "vision notes",
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_2"
                );
            }
        };
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(tempDir.toString(), "ffmpeg");
        StoredArtifact remoteLocal = localMediaArtifactService.writeBinary("gen/_runs/source", "remote.mp4", new byte[] {1, 2, 3});
        RemoteMediaGenerationClient remoteMediaGenerationClient = new RemoteMediaGenerationClient(new ObjectMapper()) {
            @Override
            public RemoteVideoTaskSubmission submitDashscopeVideoTask(
                MediaProviderProfile profile,
                String requestedModel,
                String prompt,
                int width,
                int height,
                int durationSeconds,
                Integer seed
            ) {
                return new RemoteVideoTaskSubmission(
                    "wan",
                    "wan2.2-i2v-plus",
                    "wan2.2-i2v-plus",
                    "dashscope.aliyuncs.com",
                    "dashscope.aliyuncs.com",
                    "task_123",
                    "",
                    "",
                    false,
                    true,
                    prompt,
                    0
                );
            }

            @Override
            public RemoteTaskQueryResult queryDashscopeTask(MediaProviderProfile profile, String taskId) {
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
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, modelResolver, textModelClient);
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelClient,
            remoteMediaGenerationClient,
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
}
