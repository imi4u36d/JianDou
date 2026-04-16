package com.jiandou.api.media;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LocalMediaArtifactServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void writesAndCopiesLocalArtifacts() throws Exception {
        LocalMediaArtifactService service = new LocalMediaArtifactService(storageProperties(), "ffmpeg");

        LocalMediaArtifactService.TextArtifact text = service.writeText("gen/text", "note.md", "hello");
        LocalMediaArtifactService.StoredArtifact binary = service.writeBinary("gen/bin", "data.bin", new byte[] {1, 2, 3});
        LocalMediaArtifactService.StoredArtifact copied = service.copyArtifact(binary.publicUrl(), "gen/copy", "copy.bin");

        assertEquals("note.md", text.fileName());
        assertEquals("text/markdown", text.mimeType());
        assertEquals(5L, text.sizeBytes());
        assertEquals("hello", Files.readString(Path.of(text.absolutePath())));
        assertEquals(binary.absolutePath(), service.resolveAbsolutePath(binary.publicUrl()));
        assertEquals("copy.bin", copied.fileName());
        assertArrayEquals(new byte[] {1, 2, 3}, Files.readAllBytes(Path.of(copied.absolutePath())));
    }

    @Test
    void materializesLocalArtifactsAndValidatesSourceUrls() throws Exception {
        LocalMediaArtifactService service = new LocalMediaArtifactService(storageProperties(), "ffmpeg");
        LocalMediaArtifactService.StoredArtifact binary = service.writeBinary("gen/bin", "data.bin", new byte[] {4, 5, 6});
        LocalMediaArtifactService.StoredArtifact materialized = service.materializeArtifact(
            binary.publicUrl(),
            "gen/materialized",
            "materialized.bin"
        );

        assertEquals("materialized.bin", materialized.fileName());
        assertArrayEquals(new byte[] {4, 5, 6}, Files.readAllBytes(Path.of(materialized.absolutePath())));
        assertEquals(materialized.absolutePath(), service.resolveAbsolutePath(materialized.publicUrl()));

        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> service.materializeArtifact("   ", "gen/materialized", "blank.bin")
        );
        assertEquals("source url is required", ex.getMessage());

        IllegalArgumentException copyEx = assertThrows(
            IllegalArgumentException.class,
            () -> service.copyArtifact("https://example.com/file.bin", "gen/copy", "copy.bin")
        );
        assertEquals("source public url is not a local storage path", copyEx.getMessage());
    }

    @Test
    void concatValidationBehavesAsExpected() throws Exception {
        LocalMediaArtifactService service = new LocalMediaArtifactService(storageProperties(), "ffmpeg");
        LocalMediaArtifactService.StoredArtifact first = service.writeBinary("gen/video", "first.mp4", new byte[] {1});

        IllegalArgumentException tooFewSources = assertThrows(
            IllegalArgumentException.class,
            () -> service.concatVideos("gen/video", "join.mp4", List.of("/storage/a.mp4"))
        );
        assertEquals("at least two source videos are required", tooFewSources.getMessage());

        IllegalStateException nonLocalSource = assertThrows(
            IllegalStateException.class,
            () -> service.concatVideos("gen/video", "join.mp4", List.of(first.publicUrl(), "https://example.com/second.mp4"))
        );
        assertTrue(nonLocalSource.getMessage().contains("source public url is not a local storage path"));
    }

    private JiandouStorageProperties storageProperties() {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(tempDir.toString());
        return properties;
    }
}
