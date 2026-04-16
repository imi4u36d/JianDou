package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
        Path configFile = tempDir.resolve("app.yml");
        writeConfig(configFile, "0.20");

        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", configFile.toString())
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "1");
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals(0.20d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);

        writeConfig(configFile, "0.95");
        assertEquals(0.20d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);

        Thread.sleep(1200L);
        assertEquals(0.95d, Double.parseDouble(resolver.value("model", "temperature", "fallback")), 0.0001d);
    }

    /**
     * 处理missing配置Can失败Fast。
     */
    @Test
    void missingConfigCanFailFast() {
        Path missingFile = tempDir.resolve("missing.yml");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", missingFile.toString())
            .withProperty("JIANDOU_CONFIG_FAIL_FAST", "true");
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertThrows(GenerationConfigurationException.class, () -> resolver.value("model", "temperature", "0.15"));
    }

    /**
     * 处理missing配置IsObservableWhen失败FastDisabled。
     */
    @Test
    void missingConfigIsObservableWhenFailFastDisabled() {
        Path missingFile = tempDir.resolve("missing.yml");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", missingFile.toString())
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
        Path configFile = tempDir.resolve("config").resolve("app.yml");
        Files.createDirectories(configFile.getParent());
        Files.writeString(
            configFile,
            """
                model:
                  timeout_seconds: 120
                  temperature: 0.20
                  max_tokens: 2000
                  providers:
                    qwen:
                      api_key: ""
                      base_url: "https://example.com/v1"
                  models:
                    "qwen-plus":
                      provider: "qwen"
                      kind: "text"
                """
        );
        Path secretsFile = configFile.getParent().resolve("app.secrets.yml");
        Files.writeString(
            secretsFile,
            """
                model:
                  providers:
                    qwen:
                      api_key: "secret-key"
                """
        );

        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_FILE", configFile.toString());
        ModelRuntimePropertiesResolver resolver = new ModelRuntimePropertiesResolver(env, new GenerationConfigPathLocator(env));

        assertEquals("secret-key", resolver.resolveTextProfile("qwen-plus").apiKey());
        assertTrue(resolver.configSource().contains("app.secrets.yml"));
    }

    /**
     * 处理写入配置。
     * @param configFile 配置文件值
     * @param temperature temperature值
     */
    private void writeConfig(Path configFile, String temperature) throws IOException {
        Files.writeString(
            configFile,
            """
                model:
                  timeout_seconds: 120
                  temperature: %s
                  max_tokens: 2000
                  providers:
                    qwen:
                      api_key: "test-key"
                      base_url: "https://example.com/v1"
                  models:
                    "qwen-plus":
                      provider: "qwen"
                      kind: "text"
                """.formatted(temperature)
        );
    }
}
