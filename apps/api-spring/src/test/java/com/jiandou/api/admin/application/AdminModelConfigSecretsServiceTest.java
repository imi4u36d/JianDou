package com.jiandou.api.admin.application;

import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class AdminModelConfigSecretsServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void saveApiKeysWritesSecretsOverlayFile() throws IOException {
        Path configDir = tempDir.resolve("config");
        Path providerFile = configDir.resolve("model").resolve("providers").resolve("qwen.yml");
        Files.createDirectories(providerFile.getParent());
        Files.writeString(providerFile, "model:\n  providers:\n    qwen:\n      base_url: \"https://example.com/v1\"\n");
        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        AdminModelConfigSecretsService service = new AdminModelConfigSecretsService(new GenerationConfigPathLocator(env));

        service.saveApiKeys(Map.of("qwen", "secret-key", "seedream", "image-key"));

        Path secretsFile = configDir.resolve("model").resolve("providers.secrets.yml");
        String content = Files.readString(secretsFile);
        assertTrue(content.contains("qwen"));
        assertTrue(content.contains("secret-key"));
        assertTrue(content.contains("seedream"));
        assertTrue(content.contains("image-key"));
    }

    @Test
    void saveApiKeysPreservesExistingSecrets() throws IOException {
        Path configDir = tempDir.resolve("config");
        Path providerFile = configDir.resolve("model").resolve("providers").resolve("qwen.yml");
        Files.createDirectories(providerFile.getParent());
        Files.writeString(providerFile, "model:\n  providers:\n    qwen:\n      base_url: \"https://example.com/v1\"\n");
        Path secretsFile = configDir.resolve("model").resolve("providers.secrets.yml");
        Files.writeString(
            secretsFile,
            """
                model:
                  providers:
                    qwen:
                      api_key: "old-secret"
                    seedream:
                      api_key: "image-key"
                """
        );
        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        AdminModelConfigSecretsService service = new AdminModelConfigSecretsService(new GenerationConfigPathLocator(env));

        service.saveApiKeys(Map.of("qwen", "new-secret"));

        String content = Files.readString(secretsFile);
        assertTrue(content.contains("new-secret"));
        assertTrue(content.contains("seedream"));
        assertTrue(content.contains("image-key"));
    }
}
