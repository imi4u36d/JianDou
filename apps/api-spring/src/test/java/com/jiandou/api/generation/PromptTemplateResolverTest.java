package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class PromptTemplateResolverTest {

    @TempDir
    Path tempDir;

    @Test
    void returnsPromptTextWhenTemplateAndKeyExist() throws IOException {
        Path configFile = writeAppConfig("prompts");
        writePrompt(tempDir.resolve("prompts").resolve("script.yml"), "short_drama_script", "hello world");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", configFile.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "false");

        PromptTemplateResolver resolver = buildResolver(env);

        assertEquals("hello world", resolver.systemPrompt("script", "short_drama_script"));
        assertTrue(resolver.promptErrors().isEmpty());
    }

    @Test
    void missingKeyIsObservableWhenFailFastDisabled() throws IOException {
        Path configFile = writeAppConfig("prompts");
        writePrompt(tempDir.resolve("prompts").resolve("core.yml"), "another_key", "value");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", configFile.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "false");

        PromptTemplateResolver resolver = buildResolver(env);

        assertEquals("", resolver.systemPrompt("core", "missing_key"));
        assertFalse(resolver.promptErrors().isEmpty());
        assertTrue(resolver.promptErrors().get(0).contains("Prompt key not found"));
    }

    @Test
    void missingPromptFileCanFailFast() throws IOException {
        Path configFile = writeAppConfig("missing-prompts");
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", configFile.toString())
            .withProperty("JIANDOU_PROMPT_FAIL_FAST", "true");

        PromptTemplateResolver resolver = buildResolver(env);

        assertThrows(GenerationConfigurationException.class, () -> resolver.systemPrompt("script", "short_drama_script"));
    }

    private PromptTemplateResolver buildResolver(MockEnvironment env) {
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(env, locator);
        return new PromptTemplateResolver(env, modelResolver, locator);
    }

    private Path writeAppConfig(String promptDir) throws IOException {
        Path configFile = tempDir.resolve("app.yml");
        Files.writeString(
            configFile,
            """
                prompt:
                  file: "%s"
                """.formatted(promptDir)
        );
        return configFile;
    }

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
