package com.jiandou.api.auth.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.admin.dto.AdminModelConfigKeyUpdateRequest;
import com.jiandou.api.admin.dto.AdminModelConfigResponse;
import com.jiandou.api.admin.dto.AdminModelConfigValidationResponse;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisUserModelCredentialRepository;
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

class UserModelConfigServiceTest {

    @Test
    void readBuildsUserScopedSnapshotFromDatabaseKeys() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        MybatisUserModelCredentialRepository repository = mock(MybatisUserModelCredentialRepository.class);
        UserModelConfigService service = new UserModelConfigService(resolver, repository);
        when(repository.findApiKeysByUserId(7L)).thenReturn(Map.of("deepseek", "user-secret"));
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of("value", "deepseek-v4-pro", "label", "DeepSeek V4 Pro", "provider", "deepseek", "vendor", "deepseek")
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(
            Map.of("value", "seedance-v1", "label", "Seedance", "provider", "seedance", "vendor", "volcengine")
        ));
        when(resolver.resolveTextProfile("deepseek-v4-pro", 7L)).thenReturn(new ModelRuntimeProfile(
            new TextProviderConfig("text", "deepseek-v4-pro", "deepseek", "deepseek-v4-pro", "user-secret", "https://api.deepseek.com/v1", 30, 0.2, 2000, "user-db"),
            new TextProviderCapabilities(false, false)
        ));
        when(resolver.resolveMediaProfile("seedance-v1", GenerationModelKinds.VIDEO, 7L)).thenReturn(new MediaProviderProfile(
            new MediaProviderConfig("video", "seedance-v1", "seedance", "seedance-v1", "", "https://video.example.com", "https://video.example.com/tasks", 30, "file"),
            new MediaProviderCapabilities(true, true, false, false, 5, 120, "i2v", List.of(), List.of(), false)
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("deepseek", Map.of("provider", "deepseek", "vendor", "deepseek")),
            new ModelRuntimePropertiesResolver.ConfigSection("seedance", Map.of("provider", "seedance", "vendor", "volcengine"))
        ));
        when(resolver.section("model.providers.deepseek.extras")).thenReturn(Map.of());
        when(resolver.section("model.providers.seedance.extras")).thenReturn(Map.of("task_base_url", "https://video.example.com/tasks"));
        when(resolver.value("model.providers.deepseek.extras", "task_base_url", "")).thenReturn("");
        when(resolver.value("model.providers.seedance.extras", "task_base_url", "")).thenReturn("https://video.example.com/tasks");
        stubDefaults(resolver);
        when(resolver.configErrors()).thenReturn(List.of());

        AdminModelConfigResponse response = service.read(7L);

        assertEquals("user-db", response.configSource());
        assertEquals(2, response.providers().size());
        assertTrue(response.providers().stream().filter(item -> "deepseek".equals(item.key())).findFirst().orElseThrow().apiKeyConfigured());
        assertTrue(response.models().stream().filter(item -> "deepseek-v4-pro".equals(item.name())).findFirst().orElseThrow().ready());
    }

    @Test
    void saveKeysPersistsUserScopedOverrides() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        MybatisUserModelCredentialRepository repository = mock(MybatisUserModelCredentialRepository.class);
        UserModelConfigService service = new UserModelConfigService(resolver, repository);
        when(repository.findApiKeysByUserId(7L)).thenReturn(Map.of());
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of("value", "deepseek-v4-pro", "label", "DeepSeek V4 Pro", "provider", "deepseek", "vendor", "deepseek")
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of());
        when(resolver.resolveTextProfile("deepseek-v4-pro", 7L)).thenReturn(new ModelRuntimeProfile(
            new TextProviderConfig("text", "deepseek-v4-pro", "deepseek", "deepseek-v4-pro", "", "https://api.deepseek.com/v1", 30, 0.2, 2000, "file"),
            new TextProviderCapabilities(false, false)
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("deepseek", Map.of("provider", "deepseek", "vendor", "deepseek"))
        ));
        when(resolver.section("model.providers.deepseek.extras")).thenReturn(Map.of());
        when(resolver.value("model.providers.deepseek.extras", "task_base_url", "")).thenReturn("");
        stubDefaults(resolver);
        when(resolver.configErrors()).thenReturn(List.of());

        AdminModelConfigValidationResponse validation = service.validateKeys(
            7L,
            new AdminModelConfigKeyUpdateRequest(List.of(new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "user-secret")))
        );
        service.saveKeys(7L, new AdminModelConfigKeyUpdateRequest(List.of(
            new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "user-secret")
        )));

        assertTrue(validation.valid());
        verify(repository).saveApiKeys(7L, Map.of("deepseek", "user-secret"));
    }

    @Test
    void resetKeysPersistsWithoutReadingUserCredentials() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        MybatisUserModelCredentialRepository repository = mock(MybatisUserModelCredentialRepository.class);
        UserModelConfigService service = new UserModelConfigService(resolver, repository);
        when(resolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(
            Map.of("value", "deepseek-v4-pro", "label", "DeepSeek V4 Pro", "provider", "deepseek", "vendor", "deepseek")
        ));
        when(resolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of());
        when(resolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(
            Map.of("value", "seedance-v1", "label", "Seedance", "provider", "seedance", "vendor", "volcengine")
        ));
        when(resolver.listSections("model.providers")).thenReturn(List.of(
            new ModelRuntimePropertiesResolver.ConfigSection("deepseek", Map.of("provider", "deepseek", "vendor", "deepseek")),
            new ModelRuntimePropertiesResolver.ConfigSection("seedance", Map.of("provider", "seedance", "vendor", "volcengine"))
        ));

        service.resetKeys(7L, new AdminModelConfigKeyUpdateRequest(List.of(
            new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "user-secret")
        )));

        verify(repository, never()).findApiKeysByUserId(7L);
        verify(repository).saveApiKeys(7L, Map.of("deepseek", "user-secret"));
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
