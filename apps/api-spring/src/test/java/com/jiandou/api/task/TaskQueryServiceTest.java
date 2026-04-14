package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class TaskQueryServiceTest {

    private FakeTaskRepository taskRepository;
    private RecordingTaskExecutionCoordinator executionCoordinator;
    private TaskQueryService service;

    @BeforeEach
    void setUp() {
        taskRepository = new FakeTaskRepository();
        executionCoordinator = new RecordingTaskExecutionCoordinator(taskRepository);
        TaskViewMapper taskViewMapper = new TaskViewMapper("../../storage");
        TaskDiagnosisService diagnosisService = new TaskDiagnosisService(taskViewMapper);
        service = new TaskQueryService(taskRepository, taskViewMapper, executionCoordinator, diagnosisService);
    }

    @Test
    void listTasksSupportsRunningAliasStatusFilter() {
        TaskRecord running = task("task_running", "RUNNING", "2026-04-14T00:00:02Z");
        TaskRecord planning = task("task_planning", "PLANNING", "2026-04-14T00:00:01Z");
        TaskRecord pending = task("task_pending", "PENDING", "2026-04-14T00:00:00Z");
        taskRepository.tasks = List.of(running, planning, pending);

        List<Map<String, Object>> rows = service.listTasks(null, "RUNNING", "updated_desc");

        assertEquals(2, rows.size());
        assertEquals("task_running", rows.get(0).get("id"));
        assertEquals("task_planning", rows.get(1).get("id"));
        assertEquals(1, executionCoordinator.recomputeCalls);
    }

    @Test
    void listTasksSupportsQueuedAliasStatusFilter() {
        TaskRecord queued = task("task_queued", "PENDING", "2026-04-14T00:00:02Z");
        queued.isQueued = true;
        queued.queuePosition = 1;
        TaskRecord pending = task("task_not_queued", "PENDING", "2026-04-14T00:00:01Z");
        taskRepository.tasks = List.of(queued, pending);
        executionCoordinator.snapshot = List.of("task_queued");

        List<Map<String, Object>> rows = service.listTasks(null, "queued", "updated_desc");

        assertEquals(1, rows.size());
        assertEquals("task_queued", rows.get(0).get("id"));
    }

    @Test
    void adminOverviewCountsRunningTasksWithRunningStatusAlias() {
        TaskRecord running = task("task_running", "RUNNING", "2026-04-14T00:00:02Z");
        TaskRecord rendering = task("task_rendering", "RENDERING", "2026-04-14T00:00:01Z");
        TaskRecord completed = task("task_completed", "COMPLETED", "2026-04-14T00:00:00Z");
        taskRepository.tasks = List.of(running, rendering, completed);
        taskRepository.queueEvents = List.of();
        taskRepository.workerInstances = List.of(Map.of("status", "RUNNING"));
        taskRepository.traces = List.of();
        taskRepository.tasksById.put("task_running", running);
        executionCoordinator.snapshot = List.of("task_running");

        Map<String, Object> payload = service.adminOverview();

        Map<?, ?> counts = assertInstanceOf(Map.class, payload.get("counts"));
        assertEquals(2, counts.get("runningTasks"));
        List<?> recentRunningTasks = assertInstanceOf(List.class, payload.get("recentRunningTasks"));
        assertEquals(2, recentRunningTasks.size());
    }

    private TaskRecord task(String id, String status, String updatedAt) {
        TaskRecord task = new TaskRecord();
        task.id = id;
        task.title = id;
        task.status = status;
        task.createdAt = updatedAt;
        task.updatedAt = updatedAt;
        task.executionContext = new LinkedHashMap<>();
        taskRepository.tasksById.put(id, task);
        return task;
    }

    private static final class RecordingTaskExecutionCoordinator extends TaskExecutionCoordinator {

        private int recomputeCalls;
        private List<String> snapshot = List.of();

        private RecordingTaskExecutionCoordinator(TaskRepository taskRepository) {
            super(new NoopQueuePort(), taskRepository);
        }

        @Override
        public void recomputeQueuePositions(Collection<TaskRecord> tasks) {
            recomputeCalls += 1;
            super.recomputeQueuePositions(tasks);
        }

        @Override
        public List<String> queueSnapshot() {
            return new ArrayList<>(snapshot);
        }
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

        private Collection<TaskRecord> tasks = List.of();
        private final Map<String, TaskRecord> tasksById = new LinkedHashMap<>();
        private List<Map<String, Object>> queueEvents = List.of();
        private List<Map<String, Object>> workerInstances = List.of();
        private List<Map<String, Object>> traces = List.of();

        @Override
        public Collection<TaskRecord> findAll() {
            return tasks;
        }

        @Override
        public TaskRecord findById(String taskId) {
            return tasksById.get(taskId);
        }

        @Override
        public List<Map<String, Object>> listQueueEvents(String taskId, int limit) {
            return queueEvents;
        }

        @Override
        public List<Map<String, Object>> listWorkerInstances(int limit) {
            return workerInstances;
        }

        @Override
        public List<Map<String, Object>> listTraces(String taskId, String stage, String level, String query, int limit) {
            return traces;
        }

        @Override
        public Map<String, Object> findWorkerInstance(String workerInstanceId) {
            return Map.of();
        }

        @Override
        public void save(TaskRecord task) {
        }

        @Override
        public void saveMutation(TaskPersistenceMutation mutation) {
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
        public void delete(String taskId) {
        }
    }
}
