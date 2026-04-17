package com.jiandou.api.task.runtime;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;

import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.persistence.TaskPersistenceMutation;
import com.jiandou.api.task.persistence.TaskRepository;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class JoinOutputServiceTest {

    private JoinOutputService service;

    @AfterEach
    void tearDown() {
        if (service != null) {
            service.shutdown();
        }
    }

    @Test
    void scheduleJoinIgnoresInvalidInputs() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        service = new JoinOutputService(repository, mediaArtifactService);

        service.scheduleJoin(null, 2);
        service.scheduleJoin(" ", 2);
        service.scheduleJoin("task_1", 1);

        Thread.sleep(150L);

        assertEquals(0, repository.saveCalls);
        assertEquals(0, repository.saveMutationCalls);
    }

    @Test
    void scheduleJoinBuildsJoinArtifactsAndPersistsTask() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join", List.of(1, 2));
        repository.tasks.put(task.id(), task);
        repository.saveMutationLatch = new CountDownLatch(1);

        LocalMediaArtifactService.StoredArtifact artifact = new LocalMediaArtifactService.StoredArtifact(
            "join.mp4",
            "/tmp/join.mp4",
            "/storage/join.mp4",
            1234L
        );
        org.mockito.Mockito.when(mediaArtifactService.concatVideos(any(), any(), any())).thenReturn(artifact);
        service = new JoinOutputService(repository, mediaArtifactService);

        service.scheduleJoin(task.id(), 2);

        assertTrue(repository.saveMutationLatch.await(2, TimeUnit.SECONDS));
        assertEquals(1, repository.modelCallRows.size());
        assertEquals(1, repository.materialRows.size());
        assertEquals(1, repository.resultRows.size());
        assertEquals(1, repository.stageRunRows.size());
        assertEquals(1, repository.traceRows.size());
        assertEquals("join-1-2", repository.resultRows.get(0).get("title"));
    }

    @Test
    void scheduleJoinReloadsLatestTaskBeforeSaveToAvoidOverwritingCompletedStatus() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join_completed", List.of(1, 2));
        repository.tasks.put(task.id(), repository.copy(task));
        repository.saveMutationLatch = new CountDownLatch(1);

        LocalMediaArtifactService.StoredArtifact artifact = new LocalMediaArtifactService.StoredArtifact(
            "join.mp4",
            "/tmp/join.mp4",
            "/storage/join.mp4",
            1234L
        );
        doAnswer(invocation -> {
            TaskRecord latest = repository.tasks.get(task.id());
            latest.setStatus("COMPLETED");
            latest.setProgress(100);
            latest.setFinishedAt("2026-04-17T00:00:00Z");
            return artifact;
        }).when(mediaArtifactService).concatVideos(any(), any(), any());
        service = new JoinOutputService(repository, mediaArtifactService);

        service.scheduleJoin(task.id(), 2);

        assertTrue(repository.saveMutationLatch.await(2, TimeUnit.SECONDS));
        TaskRecord saved = repository.tasks.get(task.id());
        assertEquals("COMPLETED", saved.status());
        assertEquals(100, saved.progress());
        assertEquals(0, repository.saveCalls);
    }

    @Test
    void scheduleJoinSkipsWhenClipsAreIncomplete() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join_gap", List.of(1, 3));
        repository.tasks.put(task.id(), task);
        service = new JoinOutputService(repository, mediaArtifactService);

        service.scheduleJoin(task.id(), 3);

        Thread.sleep(200L);

        assertEquals(0, repository.saveCalls);
        assertEquals(0, repository.saveMutationCalls);
    }

    @Test
    void shutdownStopsExecutor() {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        service = new JoinOutputService(repository, mediaArtifactService);

        assertDoesNotThrow(() -> service.shutdown());
    }

    @Test
    void scheduleJoinRunsWhileTaskIsStillRendering() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join_rendering", List.of(1, 2));
        repository.tasks.put(task.id(), task);
        repository.saveMutationLatch = new CountDownLatch(1);
        LocalMediaArtifactService.StoredArtifact artifact = new LocalMediaArtifactService.StoredArtifact(
            "join.mp4",
            "/tmp/join.mp4",
            "/storage/join.mp4",
            1234L
        );
        org.mockito.Mockito.when(mediaArtifactService.concatVideos(any(), any(), any())).thenReturn(artifact);
        service = new JoinOutputService(repository, mediaArtifactService);

        service.scheduleJoin(task.id(), 2);

        assertTrue(repository.saveMutationLatch.await(2, TimeUnit.SECONDS));
        assertEquals(0, repository.saveCalls);
        assertEquals(1, repository.resultRows.size());
    }

    private TaskRecord renderableTask(String taskId, List<Integer> clipIndices) {
        TaskRecord task = new TaskRecord();
        task.setId(taskId);
        task.setTitle("Task " + taskId);
        task.setStatus("RENDERING");
        task.setActiveAttemptId("att_1");
        for (Integer clipIndex : clipIndices) {
            task.addOutput(Map.of(
                "resultType", TaskResultTypes.VIDEO,
                "clipIndex", clipIndex,
                "downloadUrl", "/storage/clip-" + clipIndex + ".mp4",
                "durationSeconds", 2.0,
                "width", 720,
                "height", 1280,
                "extra", Map.of("hasAudio", true)
            ));
        }
        return task;
    }

    private static final class FakeTaskRepository implements TaskRepository {

        private final Map<String, TaskRecord> tasks = new LinkedHashMap<>();
        private int saveCalls;
        private int saveMutationCalls;
        private CountDownLatch saveMutationLatch;
        private final List<Map<String, Object>> modelCallRows = new java.util.ArrayList<>();
        private final List<Map<String, Object>> materialRows = new java.util.ArrayList<>();
        private final List<Map<String, Object>> resultRows = new java.util.ArrayList<>();
        private final List<Map<String, Object>> stageRunRows = new java.util.ArrayList<>();
        private final List<Map<String, Object>> traceRows = new java.util.ArrayList<>();

        @Override
        public void save(TaskRecord task) {
            saveCalls += 1;
            tasks.put(task.id(), copy(task));
            if (saveLatch != null) {
                saveLatch.countDown();
            }
        }

        @Override
        public void saveMutation(TaskPersistenceMutation mutation) {
            saveMutationCalls += 1;
            modelCallRows.addAll(copyRows(mutation.modelCallRows()));
            materialRows.addAll(copyRows(mutation.materialRows()));
            resultRows.addAll(copyRows(mutation.resultRows()));
            stageRunRows.addAll(copyRows(mutation.stageRunRows()));
            traceRows.addAll(copyRows(mutation.traceRows()));
            if (saveMutationLatch != null) {
                saveMutationLatch.countDown();
            }
        }

        @Override
        public Map<String, Object> findWorkerInstance(String workerInstanceId) {
            return Map.of();
        }

        @Override
        public List<Map<String, Object>> listWorkerInstances(int limit) {
            return List.of();
        }

        @Override
        public void removeQueuedTask(String taskId) {
        }

        @Override
        public String claimNextQueuedTask(String workerInstanceId) {
            return "";
        }

        @Override
        public List<String> listQueuedTaskIds(int limit) {
            return List.of();
        }

        @Override
        public List<Map<String, Object>> listStaleRunningClaims(OffsetDateTime staleBefore, int limit) {
            return List.of();
        }

        @Override
        public List<String> listStaleWorkerInstanceIds(OffsetDateTime staleBefore, int limit) {
            return List.of();
        }

        @Override
        public List<Map<String, Object>> listQueueEvents(String taskId, int limit) {
            return List.of();
        }

        @Override
        public List<Map<String, Object>> listTraces(String taskId, String stage, String level, String query, int limit) {
            return List.of();
        }

        @Override
        public TaskRecord findById(String taskId) {
            TaskRecord task = tasks.get(taskId);
            return task == null ? null : copy(task);
        }

        @Override
        public Collection<TaskRecord> findAll() {
            return tasks.values();
        }

        @Override
        public void delete(String taskId) {
            tasks.remove(taskId);
        }

        private TaskRecord copy(TaskRecord source) {
            TaskRecord target = new TaskRecord();
            target.setId(source.id());
            target.setTitle(source.title());
            target.setStatus(source.status());
            target.setProgress(source.progress());
            target.setCreatedAt(source.createdAt());
            target.setUpdatedAt(source.updatedAt());
            target.setSourceFileName(source.sourceFileName());
            target.setAspectRatio(source.aspectRatio());
            target.setMinDurationSeconds(source.minDurationSeconds());
            target.setMaxDurationSeconds(source.maxDurationSeconds());
            target.setRetryCount(source.retryCount());
            target.setStartedAt(source.startedAt());
            target.setFinishedAt(source.finishedAt());
            target.setCompletedOutputCount(source.completedOutputCount());
            target.setCurrentAttemptNo(source.currentAttemptNo());
            target.setHasTranscript(source.hasTranscript());
            target.setHasTimedTranscript(source.hasTimedTranscript());
            target.setSourceAssetCount(source.sourceAssetCount());
            target.setEditingMode(source.editingMode());
            target.setQueued(source.isQueued());
            target.setQueuePosition(source.queuePosition());
            target.setActiveAttemptId(source.activeAttemptId());
            target.setIntroTemplate(source.introTemplate());
            target.setOutroTemplate(source.outroTemplate());
            target.setCreativePrompt(source.creativePrompt());
            target.setTaskSeed(source.taskSeed());
            target.setEffectRating(source.effectRating());
            target.setEffectRatingNote(source.effectRatingNote());
            target.setRatedAt(source.ratedAt());
            target.setErrorMessage(source.errorMessage());
            target.setTranscriptText(source.transcriptText());
            target.setStoryboardScript(source.storyboardScript());
            target.setExecutionContext(new LinkedHashMap<>(source.executionContext()));
            target.setRequestSnapshot(source.requestSnapshot());
            source.traceView().forEach(item -> target.addTrace(new LinkedHashMap<>(item)));
            source.statusHistory().forEach(item -> target.addStatusHistory(new LinkedHashMap<>(item)));
            source.attemptsView().forEach(item -> target.prependAttempt(new LinkedHashMap<>(item)));
            source.stageRunsView().forEach(item -> target.addStageRun(new LinkedHashMap<>(item)));
            source.modelCallsView().forEach(item -> target.addModelCall(new LinkedHashMap<>(item)));
            source.materialsView().forEach(item -> target.addMaterial(new LinkedHashMap<>(item)));
            source.outputsView().forEach(item -> target.addOutput(new LinkedHashMap<>(item)));
            return target;
        }

        private List<Map<String, Object>> copyRows(List<Map<String, Object>> rows) {
            List<Map<String, Object>> copies = new java.util.ArrayList<>();
            for (Map<String, Object> row : rows) {
                copies.add(new LinkedHashMap<>(row));
            }
            return copies;
        }
    }
}
