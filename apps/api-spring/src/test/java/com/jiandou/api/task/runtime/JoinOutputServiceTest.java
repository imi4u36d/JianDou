package com.jiandou.api.task.runtime;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.TaskExecutionCoordinator;
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
import org.mockito.ArgumentCaptor;

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
        TaskExecutionCoordinator coordinator = mock(TaskExecutionCoordinator.class);
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        service = new JoinOutputService(repository, coordinator, mediaArtifactService);

        service.scheduleJoin(null, 2);
        service.scheduleJoin(" ", 2);
        service.scheduleJoin("task_1", 1);

        Thread.sleep(150L);

        verify(coordinator, never()).recordTrace(any(), any(), any(), any(), any(), any());
        assertEquals(0, repository.saveCalls);
    }

    @Test
    void scheduleJoinBuildsJoinArtifactsAndPersistsTask() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = mock(TaskExecutionCoordinator.class);
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join", List.of(1, 2));
        repository.tasks.put(task.id(), task);
        repository.saveLatch = new CountDownLatch(1);

        LocalMediaArtifactService.StoredArtifact artifact = new LocalMediaArtifactService.StoredArtifact(
            "join.mp4",
            "/tmp/join.mp4",
            "/storage/join.mp4",
            1234L
        );
        org.mockito.Mockito.when(mediaArtifactService.concatVideos(any(), any(), any())).thenReturn(artifact);
        service = new JoinOutputService(repository, coordinator, mediaArtifactService);

        service.scheduleJoin(task.id(), 2);

        assertTrue(repository.saveLatch.await(2, TimeUnit.SECONDS));
        assertEquals("join-1-2", task.executionContext().get("latestJoinName"));
        assertEquals("/storage/join.mp4", task.executionContext().get("latestJoinOutputUrl"));
        assertEquals(10002, task.executionContext().get("latestJoinClipIndex"));
        assertEquals(List.of(1, 2), task.executionContext().get("latestJoinClipIndices"));
        verify(coordinator).recordModelCall(any(), any());
        verify(coordinator).recordMaterial(any(), any());
        verify(coordinator).recordResult(any(), any());
        verify(coordinator).recordStageRun(any(), any());
        verify(coordinator).recordTrace(eqTask(task), org.mockito.ArgumentMatchers.eq("render"), org.mockito.ArgumentMatchers.eq("render.join_completed"), any(), org.mockito.ArgumentMatchers.eq("INFO"), any());
    }

    @Test
    void scheduleJoinSkipsWhenClipsAreIncomplete() throws Exception {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = mock(TaskExecutionCoordinator.class);
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        TaskRecord task = renderableTask("task_join_gap", List.of(1, 3));
        repository.tasks.put(task.id(), task);
        service = new JoinOutputService(repository, coordinator, mediaArtifactService);

        service.scheduleJoin(task.id(), 3);

        Thread.sleep(200L);

        verify(coordinator, never()).recordModelCall(any(), any());
        assertEquals(0, repository.saveCalls);
    }

    @Test
    void shutdownStopsExecutor() {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = mock(TaskExecutionCoordinator.class);
        LocalMediaArtifactService mediaArtifactService = mock(LocalMediaArtifactService.class);
        service = new JoinOutputService(repository, coordinator, mediaArtifactService);

        assertDoesNotThrow(() -> service.shutdown());
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

    private TaskRecord eqTask(TaskRecord task) {
        return org.mockito.ArgumentMatchers.eq(task);
    }

    private static final class FakeTaskRepository implements TaskRepository {

        private final Map<String, TaskRecord> tasks = new LinkedHashMap<>();
        private int saveCalls;
        private CountDownLatch saveLatch;

        @Override
        public void save(TaskRecord task) {
            saveCalls += 1;
            tasks.put(task.id(), task);
            if (saveLatch != null) {
                saveLatch.countDown();
            }
        }

        @Override
        public void saveMutation(TaskPersistenceMutation mutation) {
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
            return tasks.get(taskId);
        }

        @Override
        public Collection<TaskRecord> findAll() {
            return tasks.values();
        }

        @Override
        public void delete(String taskId) {
            tasks.remove(taskId);
        }
    }
}
