package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
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
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationRunFactoryImageRemoteUrlTest {

    @TempDir
    Path tempDir;

    @Test
    void createImageRunStoresPublicRemoteSourceUrlWhenProviderReturnsBase64StyleBytes() {
        GenerationRunFactory factory = factory("", "https://assets.example.com/storage");

        Map<String, Object> run = factory.createImageRun("run_base64_image", imageRequest());

        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        assertEquals("/storage/gen/_runs/run_base64_image/image.png", result.get("outputUrl"));
        assertEquals("https://assets.example.com/storage/gen/_runs/run_base64_image/image.png", metadata.get("remoteSourceUrl"));
        assertEquals("", metadata.get("providerRemoteSourceUrl"));
        assertEquals("https://assets.example.com/storage/gen/_runs/run_base64_image/image.png", metadata.get("artifactRemoteSourceUrl"));
    }

    @Test
    void createImageRunKeepsProviderRemoteSourceUrlWhenProviderReturnsUrl() {
        GenerationRunFactory factory = factory("https://provider.example.com/generated.png", "");

        Map<String, Object> run = factory.createImageRun("run_url_image", imageRequest());

        Map<String, Object> metadata = mapValue(mapValue(run.get("result")).get("metadata"));
        assertEquals("https://provider.example.com/generated.png", metadata.get("remoteSourceUrl"));
        assertEquals("https://provider.example.com/generated.png", metadata.get("providerRemoteSourceUrl"));
        assertEquals("", metadata.get("artifactRemoteSourceUrl"));
    }

    @Test
    void createImageRunFailsWhenProviderHasNoUrlAndPublicBaseUrlIsMissing() {
        GenerationRunFactory factory = factory("", "");

        GenerationProviderException ex = assertThrows(
            GenerationProviderException.class,
            () -> factory.createImageRun("run_missing_public_base", imageRequest())
        );

        assertTrue(ex.getMessage().contains("JIANDOU_STORAGE_PUBLIC_BASE_URL"));
    }

    @Test
    void createImageRunAllowsLocalOnlyStorageWhenRemoteSourceIsNotRequired() {
        GenerationRunFactory factory = factory("", "");

        Map<String, Object> run = factory.createImageRun("run_local_only_image", imageRequest(false));

        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        assertEquals("/storage/gen/_runs/run_local_only_image/image.png", result.get("outputUrl"));
        assertEquals("", metadata.get("remoteSourceUrl"));
        assertEquals("", metadata.get("providerRemoteSourceUrl"));
        assertEquals("", metadata.get("artifactRemoteSourceUrl"));
    }

    private GenerationRunFactory factory(String providerRemoteSourceUrl, String publicBaseUrl) {
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
            new MediaProviderCapabilities(false, false, false, false, 5, 120, "", List.of(), List.of(), false)
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
        TextModelProviderRegistry textModelProviderRegistry = new TextModelProviderRegistry(List.of());
        JiandouStorageProperties storageProperties = new JiandouStorageProperties();
        storageProperties.setRootDir(tempDir.toString());
        storageProperties.setPublicBaseUrl(publicBaseUrl);
        GenerationRunSupport support = new GenerationRunSupport(
            new LocalMediaArtifactService(storageProperties, "ffmpeg"),
            textModelProviderRegistry
        );
        ImageModelProvider imageModelProvider = new ImageModelProvider() {
            @Override
            public boolean supports(MediaProviderProfile profile) {
                return true;
            }

            @Override
            public RemoteImageGenerationResult generate(MediaProviderProfile profile, ImageGenerationRequest request) {
                return new RemoteImageGenerationResult(
                    new byte[] {1, 2, 3},
                    "image/png",
                    providerRemoteSourceUrl,
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
        return new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelProviderRegistry,
            new ImageModelProviderRegistry(List.of(imageModelProvider)),
            new VideoModelProviderRegistry(List.of()),
            support
        );
    }

    private Map<String, Object> imageRequest() {
        return imageRequest(true);
    }

    private Map<String, Object> imageRequest(boolean requireRemoteSourceUrl) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "image");
        request.put("input", Map.of(
            "prompt", "生成雨夜街角关键帧",
            "width", 720,
            "height", 1280,
            "frameRole", "first"
        ));
        request.put("model", Map.of(
            "textAnalysisModel", "gpt-text",
            "providerModel", "gpt-image-2"
        ));
        request.put("options", Map.of("stylePreset", "cinematic"));
        request.put("storage", Map.of("requireRemoteSourceUrl", requireRemoteSourceUrl));
        return request;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }
}
