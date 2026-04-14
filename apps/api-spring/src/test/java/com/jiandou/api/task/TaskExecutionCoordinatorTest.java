package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskExecutionCoordinatorTest {

    @Test
    void transitionTaskPersistsTaskTraceAndStatusHistoryInSingleMutation() {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(new NoopQueuePort(), repository);
        TaskRecord task = task("task_transition", "PENDING");

        coordinator.transitionTask(
            task,
            TaskStateTransition.info("ANALYZING", 10, "analysis", "task.analyzing", "任务开始分析。", Map.of("worker", "w1"))
        );

        assertEquals("ANALYZING", task.status);
        assertEquals(10, task.progress);
        assertEquals(1, task.traceView().size());
        assertEquals(1, task.statusHistory.size());
        assertNotNull(task.updatedAt);
        assertSame(task, repository.lastMutation.task());
        assertEquals(1, repository.lastMutation.traceRows().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());
        assertEquals(0, repository.lastMutation.attempts().size());
        assertEquals(0, repository.lastMutation.queueEventRows().size());
    }

    @Test
    void transitionTaskCanFinishActiveAttemptAtomically() {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(new NoopQueuePort(), repository);
        TaskRecord task = task("task_failed", "RENDERING");
        task.activeAttemptId = "att_1";
        Map<String, Object> attempt = new LinkedHashMap<>();
        attempt.put("attemptId", "att_1");
        attempt.put("status", "RUNNING");
        task.attempts.add(attempt);

        coordinator.transitionTask(
            task,
            TaskStateTransition.error("FAILED", 77, "pipeline", "task.failed", "执行失败。", Map.of("error", "boom")).withAttempt("FAILED", "boom"),
            currentTask -> {
                currentTask.errorMessage = "boom";
                currentTask.finishedAt = currentTask.nowIso();
            }
        );

        assertEquals("FAILED", task.status);
        assertEquals("boom", task.errorMessage);
        assertEquals("FAILED", attempt.get("status"));
        assertNotNull(attempt.get("finishedAt"));
        assertSame(task, repository.lastMutation.task());
        assertEquals(1, repository.lastMutation.attempts().size());
        assertEquals(1, repository.lastMutation.queueEventRows().size());
        assertEquals(1, repository.lastMutation.traceRows().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());
    }

    private TaskRecord task(String id, String status) {
        TaskRecord task = new TaskRecord();
        task.id = id;
        task.title = id;
        task.status = status;
        task.createdAt = "2026-04-14T00:00:00Z";
        task.updatedAt = task.createdAt;
        return task;
    }

    private static final class NoopQueuePort implements TaskQueuePort {

        @Override
        public void enqueue(String taskId) {
        }

        @Override
        public void remove(String taskId) {
        }

        @Override
        public String claimNext(String workerInstanceId) {
            return "";
        }

        @Override
        public List<String> snapshot() {
            return List.of();
        }
    }

    private static final class FakeTaskRepository implements TaskRepository {

        private TaskPersistenceMutation lastMutation;

        @Override
        public void save(TaskRecord task) {
        }

        @Override
        public void saveMutation(TaskPersistenceMutation mutation) {
            lastMutation = mutation;
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
            return null;
        }

        @Override
        public Collection<TaskRecord> findAll() {
            return List.of();
        }

        @Override
        public void delete(String taskId) {
        }
    }
}
