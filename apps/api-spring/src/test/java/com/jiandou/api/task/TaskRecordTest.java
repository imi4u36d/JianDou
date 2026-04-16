package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskRecordTest {

    @Test
    void settersAndGettersExposeAllCoreFields() {
        TaskRecord task = new TaskRecord();

        task.setId("task_1");
        task.setTitle("title");
        task.setStatus("RUNNING");
        task.setProgress(25);
        task.setCreatedAt("2026-04-16T00:00:00Z");
        task.setUpdatedAt("2026-04-16T00:01:00Z");
        task.setSourceFileName("source.md");
        task.setAspectRatio("9:16");
        task.setMinDurationSeconds(4);
        task.setMaxDurationSeconds(8);
        task.setRetryCount(2);
        task.setStartedAt("2026-04-16T00:02:00Z");
        task.setFinishedAt("2026-04-16T00:03:00Z");
        task.setCompletedOutputCount(3);
        task.setCurrentAttemptNo(4);
        task.setHasTranscript(true);
        task.setHasTimedTranscript(true);
        task.setSourceAssetCount(5);
        task.setEditingMode("fast");
        task.setQueued(true);
        task.setQueuePosition(6);
        task.setActiveAttemptId("att_1");
        task.setIntroTemplate("intro");
        task.setOutroTemplate("outro");
        task.setCreativePrompt("prompt");
        task.setTaskSeed(7);
        task.setEffectRating(4);
        task.setEffectRatingNote("note");
        task.setRatedAt("2026-04-16T00:04:00Z");
        task.setErrorMessage("error");
        task.setTranscriptText("transcript");
        task.setStoryboardScript("storyboard");

        assertEquals("task_1", task.id());
        assertEquals("title", task.title());
        assertEquals("RUNNING", task.status());
        assertEquals(25, task.progress());
        assertEquals("2026-04-16T00:00:00Z", task.createdAt());
        assertEquals("2026-04-16T00:01:00Z", task.updatedAt());
        assertEquals("source.md", task.sourceFileName());
        assertEquals("9:16", task.aspectRatio());
        assertEquals(4, task.minDurationSeconds());
        assertEquals(8, task.maxDurationSeconds());
        assertEquals(2, task.retryCount());
        assertEquals("2026-04-16T00:02:00Z", task.startedAt());
        assertEquals("2026-04-16T00:03:00Z", task.finishedAt());
        assertEquals(3, task.completedOutputCount());
        assertEquals(4, task.currentAttemptNo());
        assertTrue(task.hasTranscript());
        assertTrue(task.hasTimedTranscript());
        assertEquals(5, task.sourceAssetCount());
        assertEquals("fast", task.editingMode());
        assertTrue(task.isQueued());
        assertEquals(6, task.queuePosition());
        assertEquals("att_1", task.activeAttemptId());
        assertEquals("intro", task.introTemplate());
        assertEquals("outro", task.outroTemplate());
        assertEquals("prompt", task.creativePrompt());
        assertEquals(7, task.taskSeed());
        assertEquals(4, task.effectRating());
        assertEquals("note", task.effectRatingNote());
        assertEquals("2026-04-16T00:04:00Z", task.ratedAt());
        assertEquals("error", task.errorMessage());
        assertEquals("transcript", task.transcriptText());
        assertEquals("storyboard", task.storyboardScript());
    }

    @Test
    void executionContextRequestSnapshotCollectionsAndViewsStayConsistent() {
        TaskRecord task = new TaskRecord();
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("k", "v");
        GenerationRequestSnapshot snapshot = GenerationRequestSnapshot.empty();
        Map<String, Object> row = Map.of("id", "row_1");

        task.setExecutionContext(context);
        task.setRequestSnapshot(snapshot);
        task.addTrace(row);
        task.addStatusHistory(row);
        task.prependAttempt(row);
        task.addStageRun(row);
        task.addModelCall(row);
        task.addMaterial(row);
        task.addOutput(row);
        task.addSourceAsset(row);
        task.setActiveAttempt("att_2", 2);

        assertSame(context, task.executionContext());
        assertSame(snapshot, task.requestSnapshot());
        assertSame(task.trace(), task.traceView());
        assertSame(task.statusHistory(), task.statusHistory());
        assertSame(task.attempts(), task.attemptsView());
        assertSame(task.stageRuns(), task.stageRunsView());
        assertSame(task.modelCalls(), task.modelCallsView());
        assertSame(task.materials(), task.materialsView());
        assertSame(task.outputs(), task.outputsView());
        assertSame(task.sourceAssets(), task.sourceAssetsView());
        assertEquals(1, task.trace().size());
        assertEquals(1, task.statusHistory().size());
        assertEquals(1, task.attempts().size());
        assertEquals(1, task.stageRuns().size());
        assertEquals(1, task.modelCalls().size());
        assertEquals(1, task.materials().size());
        assertEquals(1, task.outputs().size());
        assertEquals(1, task.sourceAssets().size());
        assertEquals("att_2", task.activeAttemptId());
        assertEquals(2, task.currentAttemptNo());
    }

    @Test
    void nullNormalizationAndNowIsoRemainUsable() {
        TaskRecord task = new TaskRecord();

        task.setExecutionContext(null);
        task.setRequestSnapshot(null);
        Map<String, Object> mutableContext = task.mutableExecutionContext();
        mutableContext.put("created", true);

        assertNotNull(task.executionContext());
        assertEquals(true, task.executionContext().get("created"));
        assertEquals(GenerationRequestSnapshot.empty(), task.requestSnapshot());
        assertDoesNotThrow(() -> OffsetDateTime.parse(task.nowIso()));
    }
}
