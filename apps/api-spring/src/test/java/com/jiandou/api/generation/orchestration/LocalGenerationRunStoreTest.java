package com.jiandou.api.generation.orchestration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.config.JiandouStorageProperties;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LocalGenerationRunStoreTest {

    @TempDir
    Path tempDir;

    @Test
    void persistLoadAndListRunsUseFilesystemStore() {
        LocalGenerationRunStore store = newStore();
        Map<String, Object> older = new LinkedHashMap<>(Map.of(
            "id", "run_1",
            "status", "queued",
            "updatedAt", "2026-04-16T10:00:00Z"
        ));
        Map<String, Object> newer = new LinkedHashMap<>(Map.of(
            "id", "run_2",
            "status", "completed",
            "updatedAt", "2026-04-16T12:00:00Z"
        ));

        store.persistRun("run_1", older);
        store.persistRun("run_2", newer);

        assertEquals(newer, store.loadRun("run_2"));
        assertEquals(List.of(newer), store.listRuns(1));
        assertEquals(List.of(newer, older), store.listRuns(10));
    }

    @Test
    void missingRunsReturnNullAndEmptyLists() {
        LocalGenerationRunStore store = newStore();

        assertNull(store.loadRun("missing"));
        assertEquals(List.of(), store.listRuns(20));
    }

    private LocalGenerationRunStore newStore() {
        JiandouStorageProperties storageProperties = new JiandouStorageProperties();
        storageProperties.setRootDir(tempDir.toString());
        return new LocalGenerationRunStore(storageProperties, new ObjectMapper());
    }
}
