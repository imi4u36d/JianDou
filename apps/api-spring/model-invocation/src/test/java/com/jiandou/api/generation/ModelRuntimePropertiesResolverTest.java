package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.RuntimeModelCredentialProvider;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 模型运行时Properties相关测试。
 */
class ModelRuntimePropertiesResolverTest {

    @TempDir
    Path tempDir;

    /**
     * 处理cacheReloadsWhenTtlExpiresAnd文件Changes。
     */
    @Test
    void cacheReloadsWhenTtlExpiresAndFileChanges() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");

        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", configDir.toString())
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "1");
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals(0.20d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);

        writeConfig(configDir, "0.95");
        assertEquals(0.20d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);

        Thread.sleep(1200L);
        assertEquals(0.95d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);
    }

    /**
     * 处理missing配置Can失败Fast。
     */
    @Test
    void missingConfigCanFailFast() {
        Path missingDir = tempDir.resolve("missing-config");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", missingDir.toString())
            .withProperty("JIANDOU_CONFIG_FAIL_FAST", "true");
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertThrows(GenerationConfigurationException.class, () -> resolver.value("model", "temperature", "0.15"));
    }

    /**
     * 处理missing配置IsObservableWhen失败FastDisabled。
     */
    @Test
    void missingConfigIsObservableWhenFailFastDisabled() {
        Path missingDir = tempDir.resolve("missing-config");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", missingDir.toString())
            .withProperty("JIANDOU_CONFIG_FAIL_FAST", "false");
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals("0.15", resolver.value("model", "temperature", "0.15"));
        assertFalse(resolver.configErrors().isEmpty());
        assertTrue(resolver.configSource().contains("missing"));
    }

    /**
     * 处理secrets覆盖ProvidesApiKey。
     */
    @Test
    void secretsOverlayProvidesApiKey() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");
        Path secretsFile = configDir.resolve("model").resolve("providers.secrets.yml");
        Files.createDirectories(secretsFile.getParent());
        Files.writeString(
            secretsFile,
            """
                model:
                  providers:
                    deepseek:
                      api_key: "secret-key"
                """
        );

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals("secret-key", resolver.resolveTextProfile("deepseek-v4-pro").apiKey());
        assertTrue(resolver.configSource().contains("providers.secrets.yml"));
    }

    @Test
    void listModelsByKindResolvesVendorFromModelOrProviderSection() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        List<Map<String, Object>> items = resolver.listModelsByKind("text");

        assertEquals(1, items.size());
        assertEquals("deepseek", items.get(0).get("provider"));
        assertEquals("deepseek", items.get(0).get("vendor"));
    }

    @Test
    void resolveProfilesSupportConfiguredProviderModel() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals("deepseek-v4-pro", resolver.resolveTextProfile("deepseek-v4-pro").config().requestedModel());
        assertEquals("deepseek-v4-pro", resolver.resolveTextProfile("deepseek-v4-pro").modelName());
        assertEquals("seedance-v1", resolver.resolveVideoProfile("seedance-v1").requestedModel());
        assertEquals("seedance-v1-upstream", resolver.resolveVideoProfile("seedance-v1").modelName());
        assertTrue(resolver.supportsSeed("seedance-v1"));
    }

    @Test
    void volcengineProviderApiKeyIsSharedAcrossSiblingModels() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals("video-key", resolver.resolveImageProfile("seedream-v1").apiKey());
        assertEquals("video-key", resolver.resolveVideoProfile("seedance-v1").apiKey());
    }

    @Test
    void userScopedProfilesUseDatabaseApiKeysWithoutFallingBackToSharedSecrets() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");
        Path secretsFile = configDir.resolve("model").resolve("providers.secrets.yml");
        Files.createDirectories(secretsFile.getParent());
        Files.writeString(
            secretsFile,
            """
                model:
                  providers:
                    deepseek:
                      api_key: "shared-text-key"
                    volcengine:
                      api_key: "shared-volc-key"
                """
        );

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        RuntimeModelCredentialProvider repository = mock(RuntimeModelCredentialProvider.class);
        when(repository.findRuntimeApiKey(eq(42L), anyList())).thenAnswer(invocation -> {
            List<String> providerKeys = invocation.getArgument(1);
            if (providerKeys.contains("deepseek")) {
                return "admin-text-key";
            }
            if (providerKeys.contains("volcengine")) {
                return "admin-volc-key";
            }
            return "";
        });

        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env), repository);

        assertEquals("shared-text-key", resolver.resolveTextProfile("deepseek-v4-pro").apiKey());
        assertEquals("shared-volc-key", resolver.resolveImageProfile("seedream-v1").apiKey());
        assertEquals("shared-volc-key", resolver.resolveVideoProfile("seedance-v1").apiKey());
        assertEquals("admin-text-key", resolver.resolveTextProfile("deepseek-v4-pro", 42L).apiKey());
        assertEquals("admin-volc-key", resolver.resolveImageProfile("seedream-v1", 42L).apiKey());
        assertEquals("admin-volc-key", resolver.resolveVideoProfile("seedance-v1", 42L).apiKey());
        assertEquals("user-db", resolver.resolveTextProfile("deepseek-v4-pro", 42L).source());
        assertEquals("user-db", resolver.resolveVideoProfile("seedance-v1", 42L).source());
    }

    @Test
    void userScopedProfileUsesRuntimeCredentialLookupOnly() throws Exception {
        Path configDir = tempDir.resolve("config");
        writeConfig(configDir, "0.20");

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        RuntimeModelCredentialProvider repository = mock(RuntimeModelCredentialProvider.class);
        when(repository.findRuntimeApiKey(eq(7L), anyList())).thenReturn("");

        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env), repository);

        assertEquals("", resolver.resolveTextProfile("deepseek-v4-pro", 7L).apiKey());
        assertTrue(resolver.resolveTextProfile("deepseek-v4-pro", 7L).source().startsWith("file:"));
    }

    /**
     * 处理写入配置。
     * @param configDir 配置目录值
     * @param temperature temperature值
     */
    private void writeConfig(Path configDir, String temperature) throws IOException {
        Path defaultsFile = configDir.resolve("model").resolve("defaults.yml");
        Path providerFile = configDir.resolve("model").resolve("providers").resolve("deepseek.yml");
        Path modelsFile = configDir.resolve("model").resolve("models.yml");
        Files.createDirectories(defaultsFile.getParent());
        Files.createDirectories(providerFile.getParent());
        Files.writeString(
            defaultsFile,
            """
                model:
                  timeout_seconds: 120
                  temperature: %s
                  max_tokens: 2000
                """.formatted(temperature)
        );
        Files.writeString(
            providerFile,
            """
                model:
                  providers:
                    deepseek:
                      vendor: "deepseek"
                      api_key: "test-key"
                      base_url: "https://api.deepseek.com/v1"
                    seedream:
                      vendor: "volcengine"
                      api_key: ""
                      base_url: "https://image.example.com/api"
                    seedance:
                      vendor: "volcengine"
                      api_key: "video-key"
                      base_url: "https://video.example.com/api"
                      extras:
                        task_base_url: "https://video.example.com/tasks"
                """
        );
        Files.writeString(
            modelsFile,
            """
                model:
                  models:
                    "deepseek-v4-pro":
                      provider: "deepseek"
                      vendor: "deepseek"
                      kind: "text"
                      provider_model: "deepseek-v4-pro"
                    "seedream-v1":
                      provider: "seedream"
                      vendor: "volcengine"
                      kind: "image"
                      provider_model: "seedream-v1-upstream"
                    "seedance-v1":
                      provider: "seedance"
                      vendor: "volcengine"
                      kind: "video"
                      provider_model: "seedance-v1-upstream"
                      supports_seed: true
                """
        );
    }
}
