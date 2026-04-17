package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.PromptTemplateResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 提示词模板相关测试。
 */
class PromptTemplateResolverTest {

    @TempDir
    Path tempDir;

    /**
     * 处理returns提示词文本When模板AndKeyExist。
     */
    @Test
    void returnsPromptTextWhenTemplateAndKeyExist() throws IOException {
        Path configDir = writeAppConfig("prompts");
        writePrompt(configDir.resolve("prompts").resolve("script.yml"), "short_drama_script", "hello world");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", configDir.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "false");

        PromptTemplateResolver resolver = buildResolver(env);

        assertEquals("hello world", resolver.systemPrompt("script", "short_drama_script"));
        assertTrue(resolver.promptErrors().isEmpty());
    }

    /**
     * 处理missingKeyIsObservableWhen失败FastDisabled。
     */
    @Test
    void missingKeyIsObservableWhenFailFastDisabled() throws IOException {
        Path configDir = writeAppConfig("prompts");
        writePrompt(configDir.resolve("prompts").resolve("core.yml"), "another_key", "value");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", configDir.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "false");

        PromptTemplateResolver resolver = buildResolver(env);

        assertEquals("", resolver.systemPrompt("core", "missing_key"));
        assertFalse(resolver.promptErrors().isEmpty());
        assertTrue(resolver.promptErrors().get(0).contains("Prompt key not found"));
    }

    /**
     * 处理missing提示词文件Can失败Fast。
     */
    @Test
    void missingPromptFileCanFailFast() throws IOException {
        Path configDir = writeAppConfig("missing-prompts");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", configDir.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "true");

        PromptTemplateResolver resolver = buildResolver(env);

        assertThrows(GenerationConfigurationException.class, () -> resolver.systemPrompt("script", "short_drama_script"));
    }

    /**
     * 构建解析器。
     * @param env env值
     * @return 处理结果
     */
    private PromptTemplateResolver buildResolver(MockEnvironment env) {
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(env, locator);
        return new PromptTemplateResolver(env, modelResolver, locator);
    }

    /**
     * 处理写入App配置。
     * @param promptDir 提示词Dir值
     * @return 处理结果
     */
    private Path writeAppConfig(String promptDir) throws IOException {
        Path configDir = tempDir.resolve("config");
        Path configFile = configDir.resolve("app").resolve("runtime.yml");
        Files.createDirectories(configFile.getParent());
        Files.writeString(
            configFile,
            """
                prompt:
                  file: "%s"
                """.formatted(promptDir)
        );
        return configDir;
    }

    /**
     * 处理写入提示词。
     * @param promptFile 提示词文件值
     * @param key key值
     * @param value 待处理的值
     */
    private void writePrompt(Path promptFile, String key, String value) throws IOException {
        Files.createDirectories(promptFile.getParent());
        Files.writeString(
            promptFile,
            """
                system_prompts:
                  %s: "%s"
                """.formatted(key, value)
        );
    }
}
