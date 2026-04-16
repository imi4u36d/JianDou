package com.jiandou.api.task.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskDomainSnapshotsTest {

    @Test
    void snapshotsAndAggregateCopyMutableCollections() {
        Map<String, Object> payload = new LinkedHashMap<>(Map.of("resumeFromClipIndex", 2));
        Map<String, Object> input = new LinkedHashMap<>(Map.of("prompt", "x"));
        Map<String, Object> output = new LinkedHashMap<>(Map.of("url", "/a.png"));
        List<String> assetIds = new ArrayList<>(List.of("asset_1"));
        List<TaskAttemptSnapshot> attempts = new ArrayList<>();
        List<TaskStageRunSnapshot> stageRuns = new ArrayList<>();

        TaskAttemptSnapshot attempt = new TaskAttemptSnapshot(
            "attempt_1",
            "task_1",
            1,
            "create",
            TaskStatus.PENDING,
            "default",
            "worker_1",
            OffsetDateTime.parse("2026-04-16T00:00:00Z"),
            null,
            null,
            null,
            null,
            "render",
            2,
            "",
            "",
            payload
        );
        TaskStageRunSnapshot stageRun = new TaskStageRunSnapshot(
            "stage_1",
            "task_1",
            "attempt_1",
            "render",
            1,
            2,
            "DONE",
            "worker_1",
            OffsetDateTime.parse("2026-04-16T00:00:00Z"),
            null,
            300,
            input,
            output,
            "",
            ""
        );
        attempts.add(attempt);
        stageRuns.add(stageRun);
        TaskAggregate aggregate = new TaskAggregate(
            "task_1",
            "generation",
            "title",
            "desc",
            "9:16",
            4,
            8,
            2,
            "asset_1",
            "source.txt",
            assetIds,
            new ArrayList<>(List.of("source.txt")),
            new LinkedHashMap<>(Map.of("seed", 1)),
            new LinkedHashMap<>(Map.of("stage", "render")),
            "intro",
            "outro",
            "prompt",
            "openai",
            "queue",
            "drama",
            TaskStatus.PENDING,
            10,
            "",
            "",
            "[]",
            0,
            480,
            null,
            null,
            attempts,
            stageRuns
        );

        payload.put("resumeFromClipIndex", 9);
        input.put("prompt", "changed");
        output.put("url", "/b.png");
        assetIds.add("asset_2");
        attempts.clear();
        stageRuns.clear();

        assertEquals(2, attempt.payload().get("resumeFromClipIndex"));
        assertEquals("x", stageRun.inputSummary().get("prompt"));
        assertEquals("/a.png", stageRun.outputSummary().get("url"));
        assertEquals(List.of("asset_1"), aggregate.sourceAssetIds());
        assertEquals(1, aggregate.attempts().size());
        assertEquals(1, aggregate.stageRuns().size());
        assertNotSame(payload, attempt.payload());
        assertNotSame(input, stageRun.inputSummary());
        assertNotSame(output, stageRun.outputSummary());
    }

    @Test
    void workerAndTraceEnumsExposeExpectedDefaults() {
        assertEquals("api", TaskStage.API.code());
        assertEquals(WorkerStatus.RUNNING, WorkerStatus.from("running"));
        assertNull(WorkerStatus.from("missing"));
        assertTrue(WorkerStatus.RUNNING.matches("running"));
        assertFalse(WorkerStatus.STALE.matches("running"));
        assertEquals("WARN", TraceLevel.WARN.value());
    }
}
