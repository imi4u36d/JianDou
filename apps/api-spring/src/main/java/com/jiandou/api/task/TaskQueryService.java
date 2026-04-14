package com.jiandou.api.task;

import com.jiandou.api.task.exception.TaskNotFoundException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/**
 * 聚合任务读模型与管理端查询，避免应用服务同时承担命令和查询职责。
 */
@Service
public class TaskQueryService {

    private final TaskRepository taskRepository;
    private final TaskViewMapper taskViewMapper;
    private final TaskExecutionCoordinator executionCoordinator;
    private final TaskDiagnosisService taskDiagnosisService;

    public TaskQueryService(
        TaskRepository taskRepository,
        TaskViewMapper taskViewMapper,
        TaskExecutionCoordinator executionCoordinator,
        TaskDiagnosisService taskDiagnosisService
    ) {
        this.taskRepository = taskRepository;
        this.taskViewMapper = taskViewMapper;
        this.executionCoordinator = executionCoordinator;
        this.taskDiagnosisService = taskDiagnosisService;
    }

    public List<Map<String, Object>> listTasks(String q, String status, String sort) {
        List<TaskRecord> tasks = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(tasks);
        return tasks.stream()
            .sorted(taskComparator(sort))
            .filter(item -> q == null || q.isBlank() || containsIgnoreCase(item.title, q) || containsIgnoreCase(item.creativePrompt, q))
            .filter(item -> matchesStatus(item, status))
            .map(taskViewMapper::toListItem)
            .collect(Collectors.toList());
    }

    public Map<String, Object> getTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        executionCoordinator.recomputeQueuePositions(List.of(task));
        return taskViewMapper.toDetail(task);
    }

    public List<Map<String, Object>> getTrace(String taskId, int limit) {
        return tail(requireTask(taskId).trace, limit);
    }

    public List<Map<String, Object>> getLogs(String taskId, int limit) {
        return getTrace(taskId, limit);
    }

    public List<Map<String, Object>> getStatusHistory(String taskId, int limit) {
        return tail(requireTask(taskId).statusHistory, limit);
    }

    public List<Map<String, Object>> getModelCalls(String taskId, int limit) {
        return tail(requireTask(taskId).modelCalls, limit);
    }

    public List<Map<String, Object>> getResults(String taskId) {
        return new ArrayList<>(requireTask(taskId).outputs);
    }

    public List<Map<String, Object>> getMaterials(String taskId) {
        return new ArrayList<>(requireTask(taskId).materials);
    }

    public Map<String, Object> adminOverview() {
        List<String> queueSnapshot = executionCoordinator.queueSnapshot();
        List<TaskRecord> values = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(values);
        values = values.stream()
            .sorted(Comparator.comparing((TaskRecord item) -> item.createdAt).reversed())
            .toList();
        int total = values.size();
        List<Map<String, Object>> listItems = values.stream().map(taskViewMapper::toListItem).toList();
        List<Map<String, Object>> recentTasks = listItems.stream().limit(8).toList();
        List<Map<String, Object>> recentFailures = values.stream()
            .filter(item -> "FAILED".equals(item.status))
            .limit(6)
            .map(taskViewMapper::toListItem)
            .toList();
        List<Map<String, Object>> recentRunning = values.stream()
            .filter(item -> isRunningStatus(item.status))
            .limit(6)
            .map(taskViewMapper::toListItem)
            .toList();

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("counts", Map.of(
            "totalTasks", total,
            "queuedTasks", queueSnapshot.size(),
            "runningTasks", values.stream().mapToInt(item -> isRunningStatus(item.status) ? 1 : 0).sum(),
            "completedTasks", values.stream().mapToInt(item -> "COMPLETED".equals(item.status) ? 1 : 0).sum(),
            "failedTasks", values.stream().mapToInt(item -> "FAILED".equals(item.status) ? 1 : 0).sum(),
            "highRiskTasks", listItems.stream().mapToInt(item -> "high".equals(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "riskyTasks", listItems.stream().mapToInt(item -> List.of("high", "medium").contains(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "semanticTasks", values.stream().mapToInt(item -> item.hasTranscript ? 1 : 0).sum(),
            "timedSemanticTasks", values.stream().mapToInt(item -> item.hasTimedTranscript ? 1 : 0).sum(),
            "averageProgress", total == 0 ? 0 : values.stream().mapToInt(item -> item.progress).sum() / total
        ));
        payload.put("queue", adminQueueOverview(50));
        payload.put("workers", Map.of(
            "items", adminWorkers(20),
            "onlineCount", taskRepository.listWorkerInstances(200).stream()
                .map(item -> String.valueOf(item.getOrDefault("status", "")))
                .filter(statusValue -> "RUNNING".equalsIgnoreCase(statusValue))
                .count()
        ));
        payload.put("recentTasks", recentTasks);
        payload.put("recentFailures", recentFailures);
        payload.put("recentRunningTasks", recentRunning);
        payload.put("recentTraceCount", taskRepository.listTraces(null, null, null, null, 1000).size());
        return payload;
    }

    public List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit) {
        int resolvedLimit = Math.max(1, limit);
        Map<String, TaskRecord> tasks = taskRepository.findAll().stream()
            .collect(Collectors.toMap(item -> item.id, item -> item, (left, right) -> left, LinkedHashMap::new));
        return taskRepository.listTraces(taskId, stage, level, q, resolvedLimit).stream()
            .map(trace -> {
                Map<String, Object> row = new LinkedHashMap<>(trace);
                TaskRecord task = tasks.get(String.valueOf(trace.getOrDefault("taskId", "")));
                row.put("taskTitle", task == null ? "" : task.title);
                row.put("taskStatus", task == null ? "" : task.status);
                return row;
            })
            .toList();
    }

    public List<Map<String, Object>> adminWorkers(int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listWorkerInstances(resolvedLimit);
    }

    public Map<String, Object> adminWorker(String workerInstanceId) {
        Map<String, Object> item = taskRepository.findWorkerInstance(workerInstanceId);
        if (item == null || item.isEmpty()) {
            throw new TaskNotFoundException(workerInstanceId);
        }
        return item;
    }

    public List<Map<String, Object>> adminQueueEvents(String taskId, int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listQueueEvents(taskId, resolvedLimit);
    }

    public Map<String, Object> adminQueueOverview(int limit) {
        int resolvedLimit = Math.max(1, limit);
        List<String> snapshot = executionCoordinator.queueSnapshot();
        List<Map<String, Object>> events = taskRepository.listQueueEvents(null, resolvedLimit);
        List<Map<String, Object>> workers = taskRepository.listWorkerInstances(200);
        long runningWorkers = workers.stream()
            .map(item -> String.valueOf(item.getOrDefault("status", "")))
            .filter(statusValue -> "RUNNING".equalsIgnoreCase(statusValue))
            .count();
        String oldestQueuedTaskId = snapshot.isEmpty() ? "" : snapshot.get(0);
        TaskRecord oldestQueuedTask = oldestQueuedTaskId.isBlank() ? null : taskRepository.findById(oldestQueuedTaskId);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("queueLength", snapshot.size());
        payload.put("queueSnapshot", snapshot);
        payload.put("runningWorkers", runningWorkers);
        payload.put("latestEvents", events);
        payload.put("oldestQueuedTaskId", oldestQueuedTaskId);
        payload.put("oldestQueuedTaskTitle", oldestQueuedTask == null ? "" : oldestQueuedTask.title);
        payload.put("oldestQueuedTaskCreatedAt", oldestQueuedTask == null ? null : oldestQueuedTask.createdAt);
        return payload;
    }

    public Map<String, Object> adminTaskDiagnosis(String taskId) {
        return taskDiagnosisService.diagnose(requireTask(taskId));
    }

    public TaskRecord requireTask(String taskId) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null) {
            throw new TaskNotFoundException(taskId);
        }
        return task;
    }

    private Comparator<TaskRecord> taskComparator(String sort) {
        String normalizedSort = trimmed(sort, "updated_desc").toLowerCase();
        Comparator<TaskRecord> updatedDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.updatedAt),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        Comparator<TaskRecord> createdDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.createdAt),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        return switch (normalizedSort) {
            case "created_desc" -> createdDesc;
            case "progress_desc" -> Comparator.comparingInt((TaskRecord item) -> item.progress).reversed().thenComparing(updatedDesc);
            case "semantic_desc" -> Comparator.comparingInt(
                (TaskRecord item) -> item.hasTimedTranscript || item.hasTranscript ? 1 : 0
            ).reversed().thenComparing(updatedDesc);
            case "status_desc" -> Comparator.comparing((TaskRecord item) -> stringValue(item.status)).thenComparing(updatedDesc);
            case "effect_rating_desc", "rating_desc" -> Comparator
                .comparingInt((TaskRecord item) -> item.effectRating == null ? Integer.MIN_VALUE : item.effectRating)
                .reversed()
                .thenComparing(updatedDesc);
            default -> updatedDesc;
        };
    }

    private List<Map<String, Object>> tail(List<Map<String, Object>> items, int limit) {
        if (limit <= 0 || items.isEmpty()) {
            return List.of();
        }
        int fromIndex = Math.max(0, items.size() - limit);
        return new ArrayList<>(items.subList(fromIndex, items.size()));
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean containsIgnoreCase(String source, String query) {
        return source != null && source.toLowerCase().contains(query.toLowerCase());
    }

    private boolean matchesStatus(TaskRecord task, String statusFilter) {
        String normalizedFilter = normalizeStatus(statusFilter);
        if (normalizedFilter.isBlank()) {
            return true;
        }
        if ("RUNNING".equals(normalizedFilter)) {
            return isRunningStatus(task.status);
        }
        if ("QUEUED".equals(normalizedFilter)) {
            return task.isQueued;
        }
        return Objects.equals(normalizeStatus(task.status), normalizedFilter);
    }

    private boolean isRunningStatus(String status) {
        return switch (normalizeStatus(status)) {
            case "ANALYZING", "PLANNING", "RENDERING", "RUNNING", "DISPATCHING", "PROCESSING", "JOINING" -> true;
            default -> false;
        };
    }

    private String normalizeStatus(String status) {
        if (status == null) {
            return "";
        }
        return status.trim().toUpperCase();
    }

    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }
}
