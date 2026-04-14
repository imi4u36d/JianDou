package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationConfigPathLocatorTest {

    @TempDir
    Path tempDir;

    @Test
    void explicitConfigFileHasHighestPriority() throws IOException {
        Path explicit = writeConfig(tempDir.resolve("explicit").resolve("app.yml"));
        Path additional = writeConfig(tempDir.resolve("additional").resolve("app.yml"));

        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", explicit.toString())
            .withProperty("spring.config.additional-location", "file:" + additional.getParent() + "/");

        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();

        assertEquals(explicit.toAbsolutePath().normalize(), located.configFile());
        assertEquals("explicit-file", located.detail());
    }

    @Test
    void springAdditionalLocationSupportsDirectory() throws IOException {
        Path app = writeConfig(tempDir.resolve("spring-config").resolve("app.yaml"));
        MockEnvironment env = new MockEnvironment()
            .withProperty("spring.config.additional-location", "optional:file:" + app.getParent() + "/");

        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();

        assertEquals(app.toAbsolutePath().normalize(), located.configFile());
        assertEquals("spring.config.additional-location", located.detail());
    }

    @Test
    void resolveRelativePathUsesLocatedConfigDirectory() throws IOException {
        Path app = writeConfig(tempDir.resolve("config").resolve("app.yml"));
        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_FILE", app.toString());
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);

        Path resolved = locator.resolvePath("prompts");
        assertNotNull(resolved);
        assertEquals(app.getParent().resolve("prompts").toAbsolutePath().normalize(), resolved);

        Path resolvedConfigPath = locator.resolvePath("config/prompts");
        assertNotNull(resolvedConfigPath);
        assertEquals(tempDir.resolve("config").resolve("prompts").toAbsolutePath().normalize(), resolvedConfigPath);
    }

    @Test
    void locateMissingIncludesCheckedCandidates() {
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_FILE", tempDir.resolve("missing.yml").toString());
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);

        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();
        assertEquals("missing", located.source());
        assertTrue(located.detail().contains("checked config candidates"));
    }

    private Path writeConfig(Path path) throws IOException {
        Files.createDirectories(path.getParent());
        Files.writeString(path, "prompt:\n  file: \"prompts\"\n");
        return path;
    }
}
