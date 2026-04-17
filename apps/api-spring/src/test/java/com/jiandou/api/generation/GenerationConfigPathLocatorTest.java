package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 生成配置路径Locator相关测试。
 */
class GenerationConfigPathLocatorTest {

    @TempDir
    Path tempDir;

    /**
     * 处理explicit配置文件HasHighestPriority。
     */
    @Test
    void explicitConfigDirectoryHasHighestPriority() throws IOException {
        Path explicit = writeConfigDir(tempDir.resolve("explicit"));
        Path additional = writeConfigDir(tempDir.resolve("additional"));

        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", explicit.toString())
            .withProperty("spring.config.additional-location", "file:" + additional + "/");

        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();

        assertEquals(explicit.toAbsolutePath().normalize(), located.configDir());
        assertEquals("explicit-dir", located.detail());
    }

    /**
     * 处理springAdditionalLocationSupportsDirectory。
     */
    @Test
    void springAdditionalLocationSupportsDirectory() throws IOException {
        Path configDir = writeConfigDir(tempDir.resolve("spring-config"));
        MockEnvironment env = new MockEnvironment()
            .withProperty("spring.config.additional-location", "optional:file:" + configDir + "/");

        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);
        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();

        assertEquals(configDir.toAbsolutePath().normalize(), located.configDir());
        assertEquals("spring.config.additional-location", located.detail());
    }

    /**
     * 处理解析Relative路径UsesLocated配置Directory。
     */
    @Test
    void resolveRelativePathUsesLocatedConfigDirectory() throws IOException {
        Path configDir = writeConfigDir(tempDir.resolve("config"));
        MockEnvironment env = new MockEnvironment().withProperty("JIANDOU_CONFIG_DIR", configDir.toString());
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);

        Path resolved = locator.resolvePath("prompts");
        assertNotNull(resolved);
        assertEquals(configDir.resolve("prompts").toAbsolutePath().normalize(), resolved);

        Path resolvedConfigPath = locator.resolvePath("config/prompts");
        assertNotNull(resolvedConfigPath);
        assertEquals(tempDir.resolve("config").resolve("prompts").toAbsolutePath().normalize(), resolvedConfigPath);
    }

    /**
     * 处理locateMissingIncludesCheckedCandidates。
     */
    @Test
    void locateMissingIncludesCheckedCandidates() {
        MockEnvironment env = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_DIR", tempDir.resolve("missing-config").toString());
        GenerationConfigPathLocator locator = new GenerationConfigPathLocator(env);

        GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();
        assertEquals("missing", located.source());
        assertTrue(located.detail().contains("checked config candidates"));
    }

    /**
     * 处理父级Directory配置IsUsedWhenStartedFromModuleDir。
     */
    @Test
    void parentDirectoryConfigIsUsedWhenStartedFromModuleDir() throws IOException {
        Path repoRoot = tempDir.resolve("repo");
        Path configDir = writeConfigDir(repoRoot.resolve("config"));
        Path moduleDir = repoRoot.resolve("apps").resolve("api-spring");
        Files.createDirectories(moduleDir);

        String originalUserDir = System.getProperty("user.dir");
        System.setProperty("user.dir", moduleDir.toString());
        try {
            GenerationConfigPathLocator locator = new GenerationConfigPathLocator(new MockEnvironment());
            GenerationConfigPathLocator.LocatedConfig located = locator.locateAppConfig();

            assertEquals(configDir.toAbsolutePath().normalize(), located.configDir());
            assertEquals("parent-default", located.detail());
        } finally {
            if (originalUserDir == null) {
                System.clearProperty("user.dir");
            } else {
                System.setProperty("user.dir", originalUserDir);
            }
        }
    }

    /**
     * 处理写入配置。
     * @param path 路径值
     * @return 处理结果
     */
    private Path writeConfigDir(Path path) throws IOException {
        Path runtimeFile = path.resolve("app").resolve("runtime.yml");
        Files.createDirectories(runtimeFile.getParent());
        Files.writeString(runtimeFile, "prompt:\n  file: \"prompts\"\n");
        return path;
    }
}
