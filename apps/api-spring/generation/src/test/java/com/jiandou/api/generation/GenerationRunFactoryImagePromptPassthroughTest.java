package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import com.jiandou.api.generation.text.TextModelInvocation;
import com.jiandou.api.generation.text.TextModelProvider;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import com.jiandou.api.generation.video.SeedanceVideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.generation.video.VideoProviderTransport;
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
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        MediaProviderProfile imageProfile = new MediaProviderProfile(
            new MediaProviderConfig(
                "image",
                "gpt-image-2",
                "seedream",
                "gpt-image-2",
                "k",
                "https://api.example.com/v1/images",
                "",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, false, false, false, 5, 120, "", java.util.List.of(), java.util.List.of(), false)
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
                return textProfile;
            }

            /**
             * 处理解析图像Profile。
             * @param requestedModel requested模型值
             * @return 处理结果
             */
            @Override
            public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind) {
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
                throw new AssertionError("image prompt rewrite should not be called");
            }
        }));
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(storageProperties(tempDir), "ffmpeg");
        final String[] submittedPrompt = new String[1];
        final String[] submittedReferenceImageUrl = new String[1];
        final Integer[] submittedSeed = new Integer[1];
        final java.util.List<String>[] submittedReferenceImageUrls = new java.util.List[] {java.util.List.of()};
        ImageModelProvider fakeImageModelProvider = new ImageModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteImageGenerationResult generate(
                MediaProviderProfile profile,
                ImageGenerationRequest request
            ) {
                submittedPrompt[0] = request.prompt();
                submittedReferenceImageUrl[0] = request.referenceImageUrl();
                submittedSeed[0] = request.seed();
                submittedReferenceImageUrls[0] = request.referenceImageUrls();
                return new RemoteImageGenerationResult(
                    new byte[] {1, 2, 3},
                    "image/png",
                    "",
                    profile.provider(),
                    profile.modelName(),
                    "api.example.com",
                    request.width(),
                    request.height(),
                    request.width() + "x" + request.height(),
                    0
                );
            }
        };
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, textModelProviderRegistry);
        ImageModelProviderRegistry imageModelProviderRegistry = new ImageModelProviderRegistry(java.util.List.of(
            fakeImageModelProvider
        ));
        VideoProviderTransport videoProviderTransport = new VideoProviderTransport(new ObjectMapper());
        VideoModelProviderRegistry videoModelProviderRegistry = new VideoModelProviderRegistry(java.util.List.of(
            new SeedanceVideoModelProvider(videoProviderTransport)
        ));
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelProviderRegistry,
            imageModelProviderRegistry,
            videoModelProviderRegistry,
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
            "seed", 12345,
            "referenceImageUrl", "https://example.com/reference.png"
        ));
        request.put("model", Map.of(
            "textAnalysisModel", "gpt-text",
            "providerModel", "gpt-image-2"
        ));
        request.put("options", Map.of("stylePreset", "cinematic"));

        Map<String, Object> run = factory.createImageRun("run_image_1", request);

        assertTrue(submittedPrompt[0].startsWith(storyboardPrompt));
        assertTrue(submittedPrompt[0].contains("负面约束"));
        assertTrue(submittedPrompt[0].contains("不符合人体结构"));
        assertTrue(submittedPrompt[0].contains("不符合物理结构"));
        assertEquals("https://example.com/reference.png", submittedReferenceImageUrl[0]);
        assertNull(submittedSeed[0]);
        assertEquals(java.util.List.of("https://example.com/reference.png"), submittedReferenceImageUrls[0]);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertEquals(storyboardPrompt, result.get("keyframePrompt"));
        assertEquals(submittedPrompt[0], result.get("shapedPrompt"));
        assertTrue(String.valueOf(result.get("negativePrompt")).contains("不符合人体结构"));
        assertTrue(String.valueOf(result.get("negativePrompt")).contains("不符合物理结构"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals(12345, metadata.get("requestedSeed"));
        assertNull(metadata.get("imageGenerationSeed"));
        assertEquals(java.util.List.of("https://example.com/reference.png"), metadata.get("referenceImageUrls"));
        assertEquals("seedream", metadata.get("provider"));
        assertEquals("gpt-image-2", metadata.get("providerModel"));
        assertEquals("https://assets.example.com/storage/gen/_runs/run_image_1/image.png", metadata.get("remoteSourceUrl"));
        @SuppressWarnings("unchecked")
        Map<String, Object> modelInfo = (Map<String, Object>) result.get("modelInfo");
        assertEquals("gpt-image-2", modelInfo.get("requestedModel"));
        assertEquals("gpt-image-2", modelInfo.get("providerModel"));
        assertEquals("seedream", modelInfo.get("provider"));
        assertTrue(String.valueOf(result.get("outputUrl")).startsWith("/storage/"));
    }

    @Test
    void createImageRunCanSkipNegativePromptForExplicitPassthrough() {
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
            new MediaProviderConfig(
                "image",
                "gpt-image-2",
                "seedream",
                "gpt-image-2",
                "k",
                "https://api.example.com/v1/images",
                "",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, false, false, false, 5, 120, "", java.util.List.of(), java.util.List.of(), false)
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return textProfile;
            }

            @Override
            public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind) {
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
        TextModelProviderRegistry textModelProviderRegistry = new TextModelProviderRegistry(java.util.List.of());
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(storageProperties(tempDir), "ffmpeg");
        final String[] submittedPrompt = new String[1];
        ImageModelProvider fakeImageModelProvider = new ImageModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteImageGenerationResult generate(MediaProviderProfile profile, ImageGenerationRequest request) {
                submittedPrompt[0] = request.prompt();
                return new RemoteImageGenerationResult(
                    new byte[] {1, 2, 3},
                    "image/png",
                    "",
                    profile.provider(),
                    profile.modelName(),
                    "api.example.com",
                    request.width(),
                    request.height(),
                    request.width() + "x" + request.height(),
                    0
                );
            }
        };
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, textModelProviderRegistry);
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelProviderRegistry,
            new ImageModelProviderRegistry(java.util.List.of(fakeImageModelProvider)),
            new VideoModelProviderRegistry(java.util.List.of()),
            support
        );

        String prompt = "只生成一个白底香水瓶";
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "image");
        request.put("input", Map.of(
            "prompt", prompt,
            "width", 1024,
            "height", 1536,
            "frameRole", "free",
            "promptPassthrough", true
        ));
        request.put("model", Map.of(
            "textAnalysisModel", "gpt-text",
            "providerModel", "gpt-image-2"
        ));

        Map<String, Object> run = factory.createImageRun("run_image_free", request);

        assertEquals(prompt, submittedPrompt[0]);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertEquals(prompt, result.get("shapedPrompt"));
        assertEquals("", result.get("negativePrompt"));
    }

    private JiandouStorageProperties storageProperties(Path rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir.toString());
        properties.setPublicBaseUrl("https://assets.example.com/storage");
        return properties;
    }
}
