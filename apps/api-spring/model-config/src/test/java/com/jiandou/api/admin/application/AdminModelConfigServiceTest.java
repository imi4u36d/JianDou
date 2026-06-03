package com.jiandou.api.admin.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.admin.dto.AdminModelConfigKeyUpdateRequest;
import com.jiandou.api.admin.dto.AdminModelConfigResponse;
import com.jiandou.api.admin.dto.AdminModelConfigValidationResponse;
import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.TextProviderCapabilities;
import com.jiandou.api.generation.runtime.TextProviderConfig;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AdminModelConfigServiceTest {

    @Test
    void readBuildsSortedModelAndProviderSnapshot() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        AdminModelConfigService service = new AdminModelConfigService(resolver, mock(AdminModelConfigSecretsService.class));
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of(
                "value", "gpt-4.1",
                "label", "GPT 4.1",
                "provider", "openai",
                "vendor", "openai",
                "family", "gpt",
                "description", "text",
                "supportsSeed", true,
                "supportsResponsesApi", true
            )
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(
            Map.of(
                "value", "seedance",
                "label", "Seedance",
                "provider", "seedance",
                "vendor", "volcengine",
                "generationMode", "standard",
                "supportedSizes", "720*1280, 1080*1920",
                "supportedDurations", "4,8,8"
            )
        ));
        when(resolver.resolveTextProfile("gpt-4.1")).thenReturn(new ModelRuntimeProfile(
            new TextProviderConfig("text", "gpt-4.1", "openai", "gpt-4.1", "key", "https://api.openai.com/v1", 30, 0.2, 2000, "cfg"),
            new TextProviderCapabilities(true, true)
        ));
        when(resolver.resolveMediaProfile("seedance", GenerationModelKinds.VIDEO)).thenReturn(new MediaProviderProfile(
            new MediaProviderConfig("video", "seedance", "volcengine", "seedance", "key", "https://video.example.com", "https://task.example.com", 30, "cfg"),
            new MediaProviderCapabilities(true, true, false, false, 5, 120, "standard", List.of("720*1280", "1080*1920"), List.of(4, 8), false)
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("openai", Map.of("provider", "openai", "vendor", "openai", "base_url", "https://api.openai.com/v1")),
            new ModelRuntimePropertiesResolver.ConfigSection("seedance", Map.of("provider", "seedance", "vendor", "volcengine", "base_url", "https://video.example.com"))
        ));
        when(resolver.section("model.providers.openai.extras")).thenReturn(Map.of("region", "global"));
        when(resolver.section("model.providers.seedance.extras")).thenReturn(Map.of("task_base_url", "https://task.example.com"));
        when(resolver.value("model.providers.seedance.extras", "task_base_url", "")).thenReturn("https://task.example.com");
        stubDefaults(resolver);
        when(resolver.configSource()).thenReturn("dir:/workspace/config");
        when(resolver.configErrors()).thenReturn(List.of("minor warning"));

        AdminModelConfigResponse response = service.read();

        assertEquals("dir:/workspace/config", response.configSource());
        assertEquals(2, response.summary().providerCount());
        assertEquals(2, response.summary().vendorCount());
        assertEquals(2, response.summary().modelCount());
        assertEquals(2, response.summary().readyModelCount());
        assertEquals(1, response.summary().readyTextModelCount());
        assertEquals(0, response.summary().readyImageModelCount());
        assertEquals(1, response.summary().readyVideoModelCount());
        assertEquals(0.25, response.defaults().temperature());
        assertEquals(4096, response.defaults().maxTokens());
        assertEquals(List.of("gpt-4.1", "seedance"), response.models().stream().map(AdminModelConfigResponse.ModelItem::name).toList());
        assertEquals("openai", response.models().get(0).vendor());
        assertEquals("volcengine", response.models().get(1).vendor());
        assertTrue(response.models().get(0).ready());
        assertTrue(response.models().get(1).ready());
        assertEquals(List.of("720*1280", "1080*1920"), response.models().get(1).supportedSizes());
        assertEquals(List.of(4, 8), response.models().get(1).supportedDurations());
        assertEquals("api.openai.com", response.providers().get(0).endpointHost());
        assertEquals("openai", response.providers().get(0).vendor());
        assertEquals("volcengine", response.providers().get(1).key());
        assertEquals("volcengine", response.providers().get(1).vendor());
        assertTrue(response.providers().get(0).apiKeyConfigured());
        assertTrue(response.providers().get(1).taskBaseUrlConfigured());
        assertEquals(List.of("minor warning"), response.configErrors());
    }

    @Test
    void validateKeysTreatsTypedApiKeyAsReady() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        AdminModelConfigService service = new AdminModelConfigService(resolver, mock(AdminModelConfigSecretsService.class));
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of("value", "deepseek-v4-pro", "label", "DeepSeek V4 Pro", "provider", "deepseek", "vendor", "deepseek")
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of());
        when(resolver.resolveTextProfile("deepseek-v4-pro")).thenReturn(new ModelRuntimeProfile(
            new TextProviderConfig("text", "deepseek-v4-pro", "deepseek", "deepseek-v4-pro", "", "https://api.deepseek.com/v1", 30, 0.2, 2000, "cfg"),
            new TextProviderCapabilities(false, false)
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("deepseek", Map.of("provider", "deepseek", "vendor", "deepseek", "base_url", "https://api.deepseek.com/v1"))
        ));
        when(resolver.section("model.providers.deepseek.extras")).thenReturn(Map.of());
        when(resolver.value("model.providers.deepseek.extras", "task_base_url", "")).thenReturn("");
        stubDefaults(resolver);
        when(resolver.configSource()).thenReturn("dir:/workspace/config");
        when(resolver.configErrors()).thenReturn(List.of());

        AdminModelConfigValidationResponse response = service.validateKeys(
            new AdminModelConfigKeyUpdateRequest(List.of(new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "secret-key")))
        );

        assertTrue(response.valid());
        assertEquals("deepseek", response.snapshot().providers().get(0).vendor());
        assertEquals("deepseek", response.snapshot().models().get(0).vendor());
        assertTrue(response.snapshot().providers().get(0).apiKeyConfigured());
        assertTrue(response.snapshot().models().get(0).ready());
        assertEquals(List.of(), response.snapshot().models().get(0).issues());
    }

    @Test
    void saveKeysPersistsOverridesAndRefreshesResolver() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        AdminModelConfigSecretsService secretsService = mock(AdminModelConfigSecretsService.class);
        AdminModelConfigService service = new AdminModelConfigService(resolver, secretsService);
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of("value", "deepseek-v4-pro", "label", "DeepSeek V4 Pro", "provider", "deepseek", "vendor", "deepseek")
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of());
        when(resolver.resolveTextProfile("deepseek-v4-pro")).thenReturn(new ModelRuntimeProfile(
            new TextProviderConfig("text", "deepseek-v4-pro", "deepseek", "deepseek-v4-pro", "", "https://api.deepseek.com/v1", 30, 0.2, 2000, "cfg"),
            new TextProviderCapabilities(false, false)
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("deepseek", Map.of("provider", "deepseek", "vendor", "deepseek", "base_url", "https://api.deepseek.com/v1"))
        ));
        when(resolver.section("model.providers.deepseek.extras")).thenReturn(Map.of());
        when(resolver.value("model.providers.deepseek.extras", "task_base_url", "")).thenReturn("");
        stubDefaults(resolver);
        when(resolver.configSource()).thenReturn("dir:/workspace/config");
        when(resolver.configErrors()).thenReturn(List.of());

        service.saveKeys(new AdminModelConfigKeyUpdateRequest(
            List.of(new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "secret-key"))
        ));

        verify(secretsService).saveApiKeys(Map.of("deepseek", "secret-key"));
        verify(resolver).refresh();
    }

    private void stubDefaults(ModelRuntimePropertiesResolver resolver) {
        when(resolver.value("pipeline", "default_aspect_ratio", "9:16")).thenReturn("9:16");
        when(resolver.value("catalog.defaults", "style_preset", "cinematic")).thenReturn("cinematic");
        when(resolver.value("catalog.defaults", "image_size", "1024x1024")).thenReturn("1024x1024");
        when(resolver.value("catalog.defaults", "video_size", "720*1280")).thenReturn("720*1280");
        when(resolver.intValue("catalog.defaults", "video_duration_seconds", 8)).thenReturn(8);
        when(resolver.intValue("model", "timeout_seconds", 120)).thenReturn(120);
        when(resolver.value("model", "temperature", "0.15")).thenReturn("0.25");
        when(resolver.intValue("model", "max_tokens", 2000)).thenReturn(4096);
    }
}
