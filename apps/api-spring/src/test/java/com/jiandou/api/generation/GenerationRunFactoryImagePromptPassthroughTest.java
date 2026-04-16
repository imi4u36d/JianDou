package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 生成运行工厂图像提示词Passthrough相关测试。
 */
class GenerationRunFactoryImagePromptPassthroughTest {

    @TempDir
    Path tempDir;

    /**
     * 创建图像运行Uses分镜提示词Directly。
     */
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
             * 处理解析图像Profile。
             * @param requestedModel requested模型值
             * @return 处理结果
             */
            @Override
            public MediaProviderProfile resolveImageProfile(String requestedModel) {
                return imageProfile;
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
        );
        CompatibleTextModelClient textModelClient = new CompatibleTextModelClient(new ObjectMapper(), java.util.List.of()) {
            /**
             * 生成文本。
             * @param profile profile值
             * @param systemPrompt 系统提示词值
             * @param userPrompt user提示词值
             * @param temperature temperature值
             * @param maxTokens 最大Tokens值
             * @return 处理结果
             */
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

            /**
             * 生成视觉文本。
             * @param profile profile值
             * @param systemPrompt 系统提示词值
             * @param userPrompt user提示词值
             * @param imageUrls 图像Urls值
             * @param temperature temperature值
             * @param maxTokens 最大Tokens值
             * @param seed 种子值
             * @return 处理结果
             */
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
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(storageProperties(tempDir), "ffmpeg");
        final String[] submittedPrompt = new String[1];
        RemoteMediaGenerationClient remoteMediaGenerationClient = new RemoteMediaGenerationClient(new ObjectMapper()) {
            /**
             * 生成Seedream图像。
             * @param profile profile值
             * @param requestedModel requested模型值
             * @param prompt 提示词值
             * @param width width值
             * @param height height值
             * @param seed 种子值
             * @return 处理结果
             */
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

    private JiandouStorageProperties storageProperties(Path rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir.toString());
        return properties;
    }
}
