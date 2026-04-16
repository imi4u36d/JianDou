package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class JiandouStoragePropertiesTest {

    @TempDir
    Path tempDir;

    @Test
    void resolvePublicUrlRejectsTraversalOutsideRoot() {
        JiandouStorageProperties properties = storageProperties(tempDir);

        assertNull(properties.resolvePublicUrl("/storage/../../etc/passwd"));
    }

    @Test
    void resolvePublicUrlSupportsStorageRootAndNestedPaths() {
        JiandouStorageProperties properties = storageProperties(tempDir);

        assertEquals(tempDir.toAbsolutePath().normalize(), properties.resolvePublicUrl("/storage"));
        assertEquals(
            tempDir.resolve("uploads/demo.png").toAbsolutePath().normalize(),
            properties.resolvePublicUrl("/storage/uploads/demo.png")
        );
    }

    private JiandouStorageProperties storageProperties(Path rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir.toString());
        return properties;
    }
}
