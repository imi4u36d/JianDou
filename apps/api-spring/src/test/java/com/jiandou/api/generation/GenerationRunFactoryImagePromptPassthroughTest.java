package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationRunFactoryImagePromptPassthroughTest {

    @TempDir
    Path tempDir;

    @Test
    void createImageRunUsesStoryboardPromptDirectly() {
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
        MediaProviderProfile imageProfile = new MediaProviderProfile(
            "seedream",
            "seedream-4.5",
            "k",
            "https://api.example.com/v1/images",
            "",
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
            public MediaProviderProfile resolveImageProfile(String requestedModel) {
                return imageProfile;
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
        );
        CompatibleTextModelClient textModelClient = new CompatibleTextModelClient(new ObjectMapper(), java.util.List.of()) {
            @Override
            public TextModelResponse generateText(
                ModelRuntimeProfile profile,
                String systemPrompt,
                String userPrompt,
                double temperature,
                int maxTokens
            ) {
                throw new AssertionError("image prompt rewrite should not be called");
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
                throw new AssertionError("vision analysis should not be called");
            }
        };
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(tempDir.toString(), "ffmpeg");
        final String[] submittedPrompt = new String[1];
        RemoteMediaGenerationClient remoteMediaGenerationClient = new RemoteMediaGenerationClient(new ObjectMapper()) {
            @Override
            public RemoteImageGenerationResult generateSeedreamImage(
                MediaProviderProfile profile,
                String requestedModel,
                String prompt,
                int width,
                int height,
                Integer seed
            ) {
                submittedPrompt[0] = prompt;
                return new RemoteImageGenerationResult(
                    new byte[] {1, 2, 3},
                    "image/png",
                    "",
                    "seedream",
                    requestedModel,
                    "api.example.com",
                    width,
                    height,
                    width + "x" + height,
                    0
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

        String storyboardPrompt = "镜头编号：1\n统一提示词：女主站在雨夜街口，抬眼看向远处霓虹。";
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "image");
        request.put("input", Map.of(
            "prompt", storyboardPrompt,
            "width", 720,
            "height", 1280,
            "frameRole", "first",
            "referenceImageUrl", "https://example.com/reference.png"
        ));
        request.put("model", Map.of(
            "textAnalysisModel", "gpt-text",
            "providerModel", "seedream-4.5"
        ));
        request.put("options", Map.of("stylePreset", "cinematic"));

        Map<String, Object> run = factory.createImageRun("run_image_1", request);

        assertEquals(storyboardPrompt, submittedPrompt[0]);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertEquals(storyboardPrompt, result.get("keyframePrompt"));
        assertEquals(storyboardPrompt, result.get("shapedPrompt"));
        assertEquals("", result.get("negativePrompt"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals(true, metadata.get("visionAnalysisSkipped"));
        assertTrue(String.valueOf(result.get("outputUrl")).startsWith("/storage/"));
    }
}
