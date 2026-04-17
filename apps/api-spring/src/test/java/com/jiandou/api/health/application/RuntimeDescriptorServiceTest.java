package com.jiandou.api.health.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouAppProperties;
import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.TextProviderCapabilities;
import com.jiandou.api.generation.runtime.TextProviderConfig;
import com.jiandou.api.health.dto.RuntimeDescriptorResponse;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class RuntimeDescriptorServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void describeRuntimeMarksServiceReadyWhenAllModelKindsAreConfigured() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        RuntimeDescriptorService service = new RuntimeDescriptorService(resolver, "JianDou API", appProperties(), storageProperties());
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(Map.of("value", "gpt-4.1")));
        when(resolver.listModelsByKind(GenerationModelKinds.VISION)).thenReturn(List.of(Map.of("value", "gpt-4.1-vision")));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of(Map.of("value", "seedream-3.0")));
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(Map.of("value", "seedance-1.0")));
        when(resolver.resolveTextProfile("gpt-4.1")).thenReturn(readyTextProfile("gpt-4.1"));
        when(resolver.resolveTextProfile("gpt-4.1-vision")).thenReturn(readyTextProfile("gpt-4.1-vision"));
        when(resolver.resolveImageProfile("seedream-3.0")).thenReturn(readyMediaProfile("seedream-3.0"));
        when(resolver.resolveVideoProfile("seedance-1.0")).thenReturn(readyMediaProfile("seedance-1.0"));
        when(resolver.value("model", "temperature", "0.15")).thenReturn("0.35");
        when(resolver.value("model", "max_tokens", "2000")).thenReturn("4096");
        when(resolver.configSource()).thenReturn("dir:/workspace/config");

        RuntimeDescriptorResponse response = service.describeRuntime();

        assertTrue(response.ok());
        assertEquals("JianDou API", response.runtime().name());
        assertEquals("test", response.runtime().env());
        assertEquals("worker", response.runtime().executionMode());
        assertEquals(tempDir.toAbsolutePath().normalize().toString(), response.runtime().storageRoot());
        assertTrue(response.runtime().model().apiKeyPresent());
        assertTrue(response.runtime().model().ready());
        assertEquals(0.35, response.runtime().model().temperature());
        assertEquals(4096, response.runtime().model().maxTokens());
        assertEquals("dir:/workspace/config", response.runtime().model().configSource());
        assertEquals(List.of(), response.runtime().model().configErrors());
        assertTrue(response.runtime().planningCapabilities().timedTranscriptSupported());
        assertFalse(response.runtime().planningCapabilities().fallbackHeuristicEnabled());
    }

    @Test
    void describeRuntimeReportsConfigurationGaps() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        RuntimeDescriptorService service = new RuntimeDescriptorService(resolver, "JianDou API", appProperties(), storageProperties());
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VISION)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of());
        when(resolver.value("model", "temperature", "0.15")).thenReturn("bad");
        when(resolver.value("model", "max_tokens", "2000")).thenReturn("bad");
        when(resolver.configSource()).thenReturn("missing");

        RuntimeDescriptorResponse response = service.describeRuntime();

        assertFalse(response.runtime().model().apiKeyPresent());
        assertFalse(response.runtime().model().ready());
        assertEquals(0.15, response.runtime().model().temperature());
        assertEquals(2000, response.runtime().model().maxTokens());
        assertEquals(
            List.of("未配置可用文本模型", "未配置可用视觉模型", "未配置可用关键帧模型", "未配置可用视频模型"),
            response.runtime().model().configErrors()
        );
    }

    private JiandouAppProperties appProperties() {
        JiandouAppProperties properties = new JiandouAppProperties();
        properties.setEnv("test");
        properties.setExecutionMode("worker");
        return properties;
    }

    private JiandouStorageProperties storageProperties() {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(tempDir.toString());
        return properties;
    }

    private ModelRuntimeProfile readyTextProfile(String modelName) {
        return new ModelRuntimeProfile(
            new TextProviderConfig("text", modelName, "openai", modelName, "", "key", "https://api.example.com/v1", 30, 0.2, 1000, "cfg"),
            new TextProviderCapabilities(true, true, false)
        );
    }

    private MediaProviderProfile readyMediaProfile(String modelName) {
        return new MediaProviderProfile(
            new MediaProviderConfig("video", modelName, "provider", modelName, "key", "https://api.example.com", "https://task.example.com", 30, "cfg"),
            new MediaProviderCapabilities(true, true, false, false, 5, 120, "", List.of(), List.of())
        );
    }
}
