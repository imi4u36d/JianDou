package com.jiandou.api.task.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.domain.AttemptTriggerType;
import com.jiandou.api.task.domain.TaskStateTransition;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.domain.WorkerStatus;
import com.jiandou.api.task.persistence.TaskPersistenceMutation;
import com.jiandou.api.task.persistence.TaskRepository;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * 任务执行相关测试。
 */
class TaskExecutionCoordinatorTest {

    /**
     * 执行任务Persists任务追踪And状态HistoryInSingle变更流转。
     */
    @Test
    void transitionTaskPersistsTaskTraceAndStatusHistoryInSingleMutation() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_transition", "PENDING");

        coordinator.transitionTask(
            task,
            TaskStateTransition.info("ANALYZING", 10, "analysis", "task.analyzing", "任务开始分析。", Map.of("worker", "w1"))
        );

        assertEquals("ANALYZING", task.status());
        assertEquals(10, task.progress());
        assertEquals(1, task.traceView().size());
        assertEquals(1, task.statusHistory().size());
        assertNotNull(task.updatedAt());
        assertSame(task, repository.lastMutation.task());
        assertEquals(1, repository.lastMutation.traceRows().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());
        assertEquals(0, repository.lastMutation.attempts().size());
        assertEquals(0, repository.lastMutation.queueEventRows().size());
    }

    /**
     * 执行任务CanFinishActive尝试Atomically流转。
     */
    @Test
    void transitionTaskCanFinishActiveAttemptAtomically() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_failed", "RENDERING");
        task.setActiveAttemptId("att_1");
        Map<String, Object> attempt = new LinkedHashMap<>();
        attempt.put("attemptId", "att_1");
        attempt.put("status", "RUNNING");
        task.prependAttempt(attempt);

        coordinator.transitionTask(
            task,
            TaskStateTransition.error("FAILED", 77, "pipeline", "task.failed", "执行失败。", Map.of("error", "boom")).withAttempt("FAILED", "boom"),
            currentTask -> {
                currentTask.setErrorMessage("boom");
                currentTask.setFinishedAt(currentTask.nowIso());
            }
        );

        assertEquals("FAILED", task.status());
        assertEquals("boom", task.errorMessage());
        assertEquals("FAILED", attempt.get("status"));
        assertNotNull(attempt.get("finishedAt"));
        assertSame(task, repository.lastMutation.task());
        assertEquals(1, repository.lastMutation.attempts().size());
        assertEquals(1, repository.lastMutation.queueEventRows().size());
        assertEquals(1, repository.lastMutation.traceRows().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());
    }

    @Test
    void enqueueMarksTaskQueuedAndPersistsRows() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_enqueue", "FAILED");
        task.setActiveAttempt("att_2", 2);
        Map<String, Object> attempt = new LinkedHashMap<>();
        attempt.put("attemptId", "att_2");
        task.prependAttempt(attempt);

        coordinator.enqueue(task, "dispatch", "task.enqueued", "queued");

        assertEquals(TaskStatus.PENDING.value(), task.status());
        assertEquals("", task.errorMessage());
        assertEquals(true, task.isQueued());
        assertEquals(List.of("task_enqueue"), coordinator.queueSnapshot());
        assertEquals("QUEUED", attempt.get("status"));
        assertEquals(1, repository.lastMutation.traceRows().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());
        assertEquals(1, repository.lastMutation.queueEventRows().size());
        assertEquals(1, repository.lastMutation.attempts().size());
    }

    @Test
    void dequeueRemovesTaskAndPersistsQueueEvent() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        queuePort.enqueue("task_dequeue");
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_dequeue", "PENDING");
        task.setQueued(true);
        task.setQueuePosition(1);

        coordinator.dequeue(task);

        assertEquals(false, task.isQueued());
        assertNull(task.queuePosition());
        assertEquals(List.of(), coordinator.queueSnapshot());
        assertEquals(1, repository.lastMutation.queueEventRows().size());
    }

    @Test
    void recomputeQueuePositionsAndSnapshotReflectQueueOrder() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        queuePort.enqueue("task_a");
        queuePort.enqueue("task_b");
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord a = task("task_a", "PENDING");
        TaskRecord b = task("task_b", "PENDING");
        TaskRecord c = task("task_c", "PENDING");

        coordinator.recomputeQueuePositions(List.of(a, b, c));

        assertEquals(List.of("task_a", "task_b"), coordinator.queueSnapshot());
        assertEquals(1, a.queuePosition());
        assertEquals(2, b.queuePosition());
        assertNull(c.queuePosition());
        assertEquals(false, c.isQueued());
    }

    @Test
    void createAttemptAndAttemptLifecycleMethodsPersistUpdates() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_attempt", "PENDING");

        Map<String, Object> attempt = coordinator.createAttempt(task, AttemptTriggerType.CREATE, Map.of("resumeFromClipIndex", 3));

        assertEquals("create", attempt.get("triggerType"));
        assertEquals(task.activeAttemptId(), attempt.get("attemptId"));
        assertEquals(1, task.attempts().size());
        assertEquals(1, repository.lastMutation.attempts().size());

        coordinator.markActiveAttemptQueued(task);
        assertEquals("QUEUED", attempt.get("status"));
        coordinator.markActiveAttemptRunning(task, "worker_1");
        assertEquals(WorkerStatus.RUNNING.value(), attempt.get("status"));
        assertEquals("worker_1", attempt.get("workerInstanceId"));
        coordinator.markActiveAttemptFinished(task, "FAILED", "boom");
        assertEquals("FAILED", attempt.get("status"));
        assertEquals("boom", attempt.get("failureMessage"));
    }

    @Test
    void recordMethodsPersistRows() {
        FakeTaskRepository repository = new FakeTaskRepository();
        InMemoryQueuePort queuePort = new InMemoryQueuePort();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(queuePort, repository);
        TaskRecord task = task("task_record", "PENDING");
        task.setActiveAttemptId("att_1");

        coordinator.recordTrace(task, "analysis", "trace.event", "msg", "INFO", Map.of("k", "v"));
        assertEquals(1, task.trace().size());
        assertEquals(1, repository.lastMutation.traceRows().size());

        coordinator.recordStatusHistory(task, "PENDING", "RUNNING", "dispatch", "status.event", "reason");
        assertEquals(1, task.statusHistory().size());
        assertEquals(1, repository.lastMutation.statusHistoryRows().size());

        coordinator.recordStageRun(task, Map.of("stageRunId", "run_1"));
        assertEquals(1, task.stageRuns().size());
        assertEquals(1, repository.lastMutation.stageRunRows().size());

        coordinator.recordModelCall(task, Map.of("modelCallId", "call_1"));
        assertEquals(1, task.modelCalls().size());
        assertEquals(1, repository.lastMutation.modelCallRows().size());

        coordinator.recordMaterial(task, Map.of("id", "asset_1"));
        assertEquals(1, task.materials().size());
        assertEquals(1, repository.lastMutation.materialRows().size());

        coordinator.recordResult(task, Map.of("id", "result_1"));
        assertEquals(1, task.outputs().size());
        assertEquals(1, repository.lastMutation.resultRows().size());

        coordinator.recordQueueEvent(task, "manual", Map.of("source", "test"));
        assertEquals(1, repository.lastMutation.queueEventRows().size());
    }

    @Test
    void upsertAndTouchWorkerInstancePersistWorkerRows() {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(new InMemoryQueuePort(), repository);

        coordinator.upsertWorkerInstance("worker_1", "render", WorkerStatus.RUNNING.value(), Map.of("host", "a"));
        Map<String, Object> created = repository.findWorkerInstance("worker_1");
        assertEquals(WorkerStatus.RUNNING.value(), created.get("status"));
        assertEquals("render", created.get("workerType"));

        coordinator.touchWorkerInstance("worker_1", "render", WorkerStatus.STOPPED.value(), Map.of("host", "b"));
        Map<String, Object> updated = repository.findWorkerInstance("worker_1");
        assertEquals(WorkerStatus.STOPPED.value(), updated.get("status"));
        assertEquals(Map.of("host", "b"), updated.get("metadata"));
        assertTrue(String.valueOf(updated.get("stoppedAt")).length() > 10);
    }

    @Test
    void recoverStaleClaimsMarksWorkerStaleAndRequeuesTask() {
        FakeTaskRepository repository = new FakeTaskRepository();
        TaskExecutionCoordinator coordinator = new TaskExecutionCoordinator(new InMemoryQueuePort(), repository);
        repository.workerInstances.put("worker_stale", new LinkedHashMap<>(Map.of(
            "workerInstanceId", "worker_stale",
            "status", WorkerStatus.RUNNING.value()
        )));
        repository.staleWorkerIds = List.of("worker_stale");
        repository.staleClaims = List.of(Map.of(
            "taskId", "task_recover",
            "workerInstanceId", "worker_stale"
        ));

        TaskRecord task = task("task_recover", "RUNNING");
        task.setActiveAttempt("att_recover", 1);
        Map<String, Object> attempt = new LinkedHashMap<>();
        attempt.put("attemptId", "att_recover");
        attempt.put("status", WorkerStatus.RUNNING.value());
        task.prependAttempt(attempt);
        task.mutableExecutionContext().put("workerInstanceId", "worker_stale");
        repository.tasksById.put(task.id(), task);

        int recovered = coordinator.recoverStaleClaims(OffsetDateTime.now(), 10);

        assertEquals(1, recovered);
        assertEquals(TaskStatus.PENDING.value(), task.status());
        assertEquals(true, task.isQueued());
        assertEquals("worker_stale", task.executionContext().get("recoveredFromWorkerInstanceId"));
        assertEquals(null, task.executionContext().get("workerInstanceId"));
        assertEquals("QUEUED", attempt.get("status"));
        assertEquals(WorkerStatus.STALE.value(), repository.findWorkerInstance("worker_stale").get("status"));
        assertEquals(1, repository.lastMutation.queueEventRows().size());
    }

    /**
     * 处理任务。
     * @param id 标识值
     * @param status 状态值
     * @return 处理结果
     */
    private TaskRecord task(String id, String status) {
        TaskRecord task = new TaskRecord();
        task.setId(id);
        task.setTitle(id);
        task.setStatus(status);
        task.setCreatedAt("2026-04-14T00:00:00Z");
        task.setUpdatedAt(task.createdAt());
        return task;
    }

    private static final class InMemoryQueuePort implements TaskQueuePort {

        private final LinkedHashSet<String> queue = new LinkedHashSet<>();

        /**
         * 将enqueue加入队列。
         * @param taskId 任务标识
         */
        @Override
        public void enqueue(String taskId) {
            queue.add(taskId);
        }

        /**
         * 移除remove。
         * @param taskId 任务标识
         */
        @Override
        public void remove(String taskId) {
            queue.remove(taskId);
        }

        /**
         * 领取Next。
         * @param workerInstanceId 工作节点实例标识
         * @return 处理结果
         */
        @Override
        public String claimNext(String workerInstanceId) {
            if (queue.isEmpty()) {
                return "";
            }
            String next = queue.iterator().next();
            queue.remove(next);
            return next;
        }

        /**
         * 处理快照。
         * @return 处理结果
         */
        @Override
        public List<String> snapshot() {
            return new ArrayList<>(queue);
        }
    }

    private static final class FakeTaskRepository implements TaskRepository {

        private TaskPersistenceMutation lastMutation;
        private final Map<String, TaskRecord> tasksById = new LinkedHashMap<>();
        private final Map<String, Map<String, Object>> workerInstances = new LinkedHashMap<>();
        private List<Map<String, Object>> staleClaims = List.of();
        private List<String> staleWorkerIds = List.of();

        /**
         * 保存save。
         * @param task 要处理的任务对象
         */
        @Override
        public void save(TaskRecord task) {
            tasksById.put(task.id(), task);
        }

        /**
         * 保存变更。
         * @param mutation 变更值
         */
        @Override
        public void saveMutation(TaskPersistenceMutation mutation) {
            lastMutation = mutation;
            if (mutation.task() != null) {
                tasksById.put(mutation.task().id(), mutation.task());
            }
            for (Map<String, Object> workerRow : mutation.workerInstanceRows()) {
                workerInstances.put(String.valueOf(workerRow.get("workerInstanceId")), new LinkedHashMap<>(workerRow));
            }
        }

        /**
         * 查找工作节点Instance。
         * @param workerInstanceId 工作节点实例标识
         * @return 处理结果
         */
        @Override
        public Map<String, Object> findWorkerInstance(String workerInstanceId) {
            return workerInstances.get(workerInstanceId);
        }

        /**
         * 列出工作节点Instances。
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<Map<String, Object>> listWorkerInstances(int limit) {
            return workerInstances.values().stream().limit(limit).toList();
        }

        /**
         * 移除Queued任务。
         * @param taskId 任务标识
         */
        @Override
        public void removeQueuedTask(String taskId) {
        }

        /**
         * 领取NextQueued任务。
         * @param workerInstanceId 工作节点实例标识
         * @return 处理结果
         */
        @Override
        public String claimNextQueuedTask(String workerInstanceId) {
            return "";
        }

        /**
         * 列出Queued任务标识列表。
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<String> listQueuedTaskIds(int limit) {
            return List.of();
        }

        /**
         * 列出StaleRunningClaims。
         * @param staleBefore staleBefore值
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<Map<String, Object>> listStaleRunningClaims(OffsetDateTime staleBefore, int limit) {
            return staleClaims.stream().limit(limit).toList();
        }

        /**
         * 列出Stale工作节点Instance标识列表。
         * @param staleBefore staleBefore值
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<String> listStaleWorkerInstanceIds(OffsetDateTime staleBefore, int limit) {
            return staleWorkerIds.stream().limit(limit).toList();
        }

        /**
         * 列出队列Events。
         * @param taskId 任务标识
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<Map<String, Object>> listQueueEvents(String taskId, int limit) {
            return List.of();
        }

        /**
         * 列出Traces。
         * @param taskId 任务标识
         * @param stage 阶段名称
         * @param level level值
         * @param query 查询值
         * @param limit 返回的最大条目数
         * @return 处理结果
         */
        @Override
        public List<Map<String, Object>> listTraces(String taskId, String stage, String level, String query, int limit) {
            return List.of();
        }

        /**
         * 查找By标识。
         * @param taskId 任务标识
         * @return 处理结果
         */
        @Override
        public TaskRecord findById(String taskId) {
            return tasksById.get(taskId);
        }

        /**
         * 查找All。
         * @return 处理结果
         */
        @Override
        public Collection<TaskRecord> findAll() {
            return tasksById.values();
        }

        /**
         * 删除删除。
         * @param taskId 任务标识
         */
        @Override
        public void delete(String taskId) {
            tasksById.remove(taskId);
        }
    }
}
