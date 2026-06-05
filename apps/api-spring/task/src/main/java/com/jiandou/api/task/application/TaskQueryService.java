package com.jiandou.api.task.application;

import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.auth.security.SecurityCurrentUser;
import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.domain.WorkerStatus;
import com.jiandou.api.task.exception.TaskNotFoundException;
import com.jiandou.api.task.persistence.TaskRepository;
import com.jiandou.api.task.view.TaskViewMapper;
import com.jiandou.api.task.web.dto.TaskListItemResponse;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/**
 * 聚合任务读模型与管理端查询，避免应用服务同时承担命令和查询职责。
 */
@Service
public class TaskQueryService {

    private static final int SHOWCASE_LIMIT = 8;

    private final TaskRepository taskRepository;
    private final TaskViewMapper taskViewMapper;
    private final TaskExecutionCoordinator executionCoordinator;
    private final TaskDiagnosisService taskDiagnosisService;
    private final JiandouTaskOpsProperties taskOpsProperties;
    private final MybatisAuthRepository authRepository;

    /**
     * 创建新的任务查询服务。
     * @param taskRepository 任务仓储值
     * @param taskViewMapper 任务视图映射器值
     * @param executionCoordinator 执行协调器值
     * @param taskDiagnosisService 任务诊断服务值
     */
    public TaskQueryService(
        TaskRepository taskRepository,
        TaskViewMapper taskViewMapper,
        TaskExecutionCoordinator executionCoordinator,
        TaskDiagnosisService taskDiagnosisService,
        JiandouTaskOpsProperties taskOpsProperties,
        MybatisAuthRepository authRepository
    ) {
        this.taskRepository = taskRepository;
        this.taskViewMapper = taskViewMapper;
        this.executionCoordinator = executionCoordinator;
        this.taskDiagnosisService = taskDiagnosisService;
        this.taskOpsProperties = taskOpsProperties;
        this.authRepository = authRepository;
    }

    /**
     * 列出任务。
     * @param q 查询文本
     * @param status 状态值
     * @param sort 排序方式
     * @return 处理结果
     */
    public List<TaskListItemResponse> listTasks(String q, String status, String sort) {
        Long ownerUserId = requiredUserId();
        List<TaskRecord> tasks = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(tasks);
        List<TaskRecord> filteredTasks = tasks.stream()
            .filter(item -> ownedBy(item, ownerUserId))
            .sorted(taskComparator(sort))
            .filter(item -> q == null || q.isBlank() || containsIgnoreCase(item.title(), q) || containsIgnoreCase(item.creativePrompt(), q))
            .filter(item -> matchesStatus(item, status))
            .toList();
        return toListItemResponses(filteredTasks);
    }

    /**
     * 管理端列出全部任务。
     * @param q 查询文本
     * @param status 状态值
     * @param sort 排序方式
     * @return 处理结果
     */
    public List<TaskListItemResponse> adminListTasks(String q, String status, String sort) {
        List<TaskRecord> tasks = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(tasks);
        List<TaskRecord> filteredTasks = tasks.stream()
            .sorted(taskComparator(sort))
            .filter(item -> q == null || q.isBlank()
                || containsIgnoreCase(item.title(), q)
                || containsIgnoreCase(item.creativePrompt(), q)
                || containsIgnoreCase(item.sourceFileName(), q))
            .filter(item -> matchesStatus(item, status))
            .toList();
        return toListItemResponses(filteredTasks);
    }

    /**
     * 返回官网与工作台共用的公开案例数据。
     * 仅返回已完成且具备可公开预览结果的任务摘要。
     * @return 处理结果
     */
    public Map<String, Object> showcaseCases() {
        List<TaskRecord> tasks = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(tasks);
        List<Map<String, Object>> items = tasks.stream()
            .filter(this::eligibleForShowcase)
            .sorted(showcaseComparator())
            .map(taskViewMapper::toShowcaseItem)
            .filter(item -> !stringValue(item.get("previewUrl")).isBlank())
            .limit(SHOWCASE_LIMIT)
            .toList();

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("totalCompletedTasks", tasks.stream().filter(item -> TaskStatus.COMPLETED.matches(item.status())).count());
        payload.put("items", items);
        return payload;
    }

    /**
     * 返回任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public Map<String, Object> getTask(String taskId) {
        TaskRecord task = requireOwnedTask(taskId);
        executionCoordinator.recomputeQueuePositions(List.of(task));
        return enrichTaskRow(task, taskViewMapper.toDetail(task));
    }

    /**
     * 管理端返回任务详情。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public Map<String, Object> adminGetTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        executionCoordinator.recomputeQueuePositions(List.of(task));
        return enrichTaskRow(task, taskViewMapper.toDetail(task));
    }

    /**
     * 返回追踪。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> getTrace(String taskId, int limit) {
        TaskRecord task = requireOwnedTask(taskId);
        if (!task.trace().isEmpty()) {
            return tail(task.trace(), limit);
        }
        return chronological(taskRepository.listTraces(taskId, null, null, null, limit));
    }

    /**
     * 返回Logs。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> getLogs(String taskId, int limit) {
        return getTrace(taskId, limit);
    }

    /**
     * 返回状态History。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> getStatusHistory(String taskId, int limit) {
        return tail(requireOwnedTask(taskId).statusHistory(), limit);
    }

    /**
     * 返回模型Calls。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> getModelCalls(String taskId, int limit) {
        return tail(requireOwnedTask(taskId).modelCalls(), limit);
    }

    /**
     * 返回Results。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public List<Map<String, Object>> getResults(String taskId) {
        return new ArrayList<>(requireOwnedTask(taskId).outputs());
    }

    /**
     * 返回素材。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public List<Map<String, Object>> getMaterials(String taskId) {
        return new ArrayList<>(requireOwnedTask(taskId).materials());
    }

    /**
     * 处理管理概览。
     * @return 处理结果
     */
    public Map<String, Object> adminOverview() {
        List<String> queueSnapshot = executionCoordinator.queueSnapshot();
        List<TaskRecord> values = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(values);
        values = values.stream()
            .sorted(Comparator.comparing((TaskRecord item) -> item.createdAt()).reversed())
            .toList();
        int total = values.size();
        List<Map<String, Object>> listItems = enrichTaskRows(values, values.stream().map(taskViewMapper::toListItem).toList());
        List<Map<String, Object>> recentTasks = listItems.stream().limit(8).toList();
        List<TaskRecord> recentFailureRecords = values.stream()
            .filter(item -> TaskStatus.FAILED.matches(item.status()))
            .limit(6)
            .toList();
        List<Map<String, Object>> recentFailures = enrichTaskRows(
            recentFailureRecords,
            recentFailureRecords.stream().map(taskViewMapper::toListItem).toList()
        );
        List<TaskRecord> recentRunningRecords = values.stream()
            .filter(item -> isRunningStatus(item.status()))
            .limit(6)
            .toList();
        List<Map<String, Object>> recentRunning = enrichTaskRows(
            recentRunningRecords,
            recentRunningRecords.stream().map(taskViewMapper::toListItem).toList()
        );

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("counts", Map.of(
            "totalTasks", total,
            "queuedTasks", queueSnapshot.size(),
            "runningTasks", values.stream().mapToInt(item -> isRunningStatus(item.status()) ? 1 : 0).sum(),
            "completedTasks", values.stream().mapToInt(item -> TaskStatus.COMPLETED.matches(item.status()) ? 1 : 0).sum(),
            "failedTasks", values.stream().mapToInt(item -> TaskStatus.FAILED.matches(item.status()) ? 1 : 0).sum(),
            "highRiskTasks", listItems.stream().mapToInt(item -> "high".equals(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "riskyTasks", listItems.stream().mapToInt(item -> List.of("high", "medium").contains(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "semanticTasks", values.stream().mapToInt(item -> item.hasTranscript() ? 1 : 0).sum(),
            "timedSemanticTasks", values.stream().mapToInt(item -> item.hasTimedTranscript() ? 1 : 0).sum(),
            "averageProgress", total == 0 ? 0 : values.stream().mapToInt(item -> item.progress()).sum() / total
        ));
        payload.put("queue", adminQueueOverview(taskOpsProperties.getAdminOverviewQueuePreviewLimit()));
        payload.put("workers", Map.of(
            "items", adminWorkers(taskOpsProperties.getAdminOverviewWorkerPreviewLimit()),
            "onlineCount", taskRepository.listWorkerInstances(taskOpsProperties.getWorkerInstanceScanLimit()).stream()
                .map(item -> String.valueOf(item.getOrDefault("status", "")))
                .filter(WorkerStatus.RUNNING::matches)
                .count()
        ));
        payload.put("recentTasks", recentTasks);
        payload.put("recentFailures", recentFailures);
        payload.put("recentRunningTasks", recentRunning);
        payload.put("recentTraceCount", taskRepository.listTraces(null, null, null, null, taskOpsProperties.getRecentTraceScanLimit()).size());
        return payload;
    }

    private List<TaskListItemResponse> toListItemResponses(List<TaskRecord> tasks) {
        Map<Long, SysUserEntity> ownerMap = loadOwners(tasks);
        return tasks.stream().map(task -> {
            Long ownerUserId = task.ownerUserId();
            SysUserEntity owner = ownerUserId == null ? null : ownerMap.get(ownerUserId);
            return taskViewMapper.toListItemResponse(task,
                ownerUserId != null ? String.valueOf(ownerUserId) : null,
                owner == null ? "" : stringValue(owner.getUsername()),
                owner == null ? "" : stringValue(owner.getDisplayName()),
                owner == null ? "" : stringValue(owner.getRole()));
        }).collect(Collectors.toList());
    }

    private List<Map<String, Object>> enrichTaskRows(List<TaskRecord> tasks, List<Map<String, Object>> rows) {
        Map<Long, SysUserEntity> ownerMap = loadOwners(tasks);
        for (int index = 0; index < Math.min(tasks.size(), rows.size()); index++) {
            appendOwnerInfo(rows.get(index), tasks.get(index), ownerMap);
        }
        return rows;
    }

    private Map<String, Object> enrichTaskRow(TaskRecord task, Map<String, Object> row) {
        appendOwnerInfo(row, task, loadOwners(List.of(task)));
        return row;
    }

    private Map<Long, SysUserEntity> loadOwners(List<TaskRecord> tasks) {
        Set<Long> ownerIds = tasks.stream()
            .map(TaskRecord::ownerUserId)
            .filter(item -> item != null && item > 0)
            .collect(Collectors.toCollection(LinkedHashSet::new));
        return authRepository.findUsersByIds(ownerIds);
    }

    private void appendOwnerInfo(Map<String, Object> row, TaskRecord task, Map<Long, SysUserEntity> ownerMap) {
        Long ownerUserId = task.ownerUserId();
        SysUserEntity owner = ownerUserId == null ? null : ownerMap.get(ownerUserId);
        row.put("ownerUserId", ownerUserId);
        row.put("ownerUsername", owner == null ? "" : stringValue(owner.getUsername()));
        row.put("ownerDisplayName", owner == null ? "" : stringValue(owner.getDisplayName()));
        row.put("ownerRole", owner == null ? "" : stringValue(owner.getRole()));
    }

    /**
     * 处理管理Traces。
     * @param taskId 任务标识
     * @param stage 阶段名称
     * @param level level值
     * @param q 查询文本
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit) {
        int resolvedLimit = Math.max(1, limit);
        Map<String, TaskRecord> tasks = taskRepository.findAll().stream()
            .collect(Collectors.toMap(item -> item.id(), item -> item, (left, right) -> left, LinkedHashMap::new));
        return taskRepository.listTraces(taskId, stage, level, q, resolvedLimit).stream()
            .map(trace -> {
                Map<String, Object> row = new LinkedHashMap<>(trace);
                TaskRecord task = tasks.get(String.valueOf(trace.getOrDefault("taskId", "")));
                row.put("taskTitle", task == null ? "" : task.title());
                row.put("taskStatus", task == null ? "" : task.status());
                return row;
            })
            .toList();
    }

    /**
     * 处理管理Workers。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> adminWorkers(int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listWorkerInstances(resolvedLimit);
    }

    /**
     * 处理管理工作节点。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    public Map<String, Object> adminWorker(String workerInstanceId) {
        Map<String, Object> item = taskRepository.findWorkerInstance(workerInstanceId);
        if (item == null || item.isEmpty()) {
            throw new TaskNotFoundException(workerInstanceId);
        }
        return item;
    }

    /**
     * 处理管理队列Events。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> adminQueueEvents(String taskId, int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listQueueEvents(taskId, resolvedLimit);
    }

    /**
     * 处理管理队列概览。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public Map<String, Object> adminQueueOverview(int limit) {
        int resolvedLimit = Math.max(1, limit);
        List<String> snapshot = executionCoordinator.queueSnapshot();
        List<Map<String, Object>> events = taskRepository.listQueueEvents(null, resolvedLimit);
        List<Map<String, Object>> workers = taskRepository.listWorkerInstances(taskOpsProperties.getWorkerInstanceScanLimit());
        long runningWorkers = workers.stream()
            .map(item -> String.valueOf(item.getOrDefault("status", "")))
            .filter(WorkerStatus.RUNNING::matches)
            .count();
        String oldestQueuedTaskId = snapshot.isEmpty() ? "" : snapshot.get(0);
        TaskRecord oldestQueuedTask = oldestQueuedTaskId.isBlank() ? null : taskRepository.findById(oldestQueuedTaskId);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("queueLength", snapshot.size());
        payload.put("queueSnapshot", snapshot);
        payload.put("runningWorkers", runningWorkers);
        payload.put("userQueues", userQueueOverview());
        payload.put("latestEvents", events);
        payload.put("oldestQueuedTaskId", oldestQueuedTaskId);
        payload.put("oldestQueuedTaskTitle", oldestQueuedTask == null ? "" : oldestQueuedTask.title());
        payload.put("oldestQueuedTaskCreatedAt", oldestQueuedTask == null ? null : oldestQueuedTask.createdAt());
        return payload;
    }

    /**
     * 处理管理任务诊断。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public Map<String, Object> adminTaskDiagnosis(String taskId) {
        return taskDiagnosisService.diagnose(requireTask(taskId));
    }

    /**
     * 处理require任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public TaskRecord requireTask(String taskId) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null) {
            throw new TaskNotFoundException(taskId);
        }
        return task;
    }

    private List<Map<String, Object>> userQueueOverview() {
        List<Map<String, Object>> stats = taskRepository.listUserQueueStats();
        Set<Long> ownerIds = stats.stream()
            .map(item -> longObjectValue(item.get("ownerUserId")))
            .filter(item -> item != null && item > 0)
            .collect(Collectors.toCollection(LinkedHashSet::new));
        Map<Long, SysUserEntity> owners = authRepository.findUsersByIds(ownerIds);
        return stats.stream().map(item -> {
            Long ownerUserId = longObjectValue(item.get("ownerUserId"));
            SysUserEntity owner = ownerUserId == null ? null : owners.get(ownerUserId);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ownerUserId", ownerUserId);
            row.put("ownerUsername", owner == null ? "" : stringValue(owner.getUsername()));
            row.put("ownerDisplayName", owner == null ? "系统任务" : stringValue(owner.getDisplayName()));
            row.put("ownerRole", owner == null ? "SYSTEM" : stringValue(owner.getRole()));
            row.put("taskConcurrencyLimit", owner == null ? 1 : taskConcurrencyLimit(owner));
            row.put("runningTaskCount", longValue(item.get("runningTaskCount")));
            row.put("queuedTaskCount", longValue(item.get("queuedTaskCount")));
            row.put("oldestQueuedTaskId", stringValue(item.get("oldestQueuedTaskId")));
            row.put("oldestQueuedTaskTitle", stringValue(item.get("oldestQueuedTaskTitle")));
            row.put("oldestQueuedTaskCreatedAt", item.get("oldestQueuedTaskCreatedAt"));
            return row;
        }).toList();
    }

    private int taskConcurrencyLimit(SysUserEntity user) {
        Integer value = user == null ? null : user.getTaskConcurrencyLimit();
        return value == null || value < 1 ? 1 : value;
    }

    /**
     * 处理当前用户任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    public TaskRecord requireOwnedTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        if (!ownedBy(task, requiredUserId())) {
            throw new TaskNotFoundException(taskId);
        }
        return task;
    }

    private Long requiredUserId() {
        return SecurityCurrentUser.requireCurrentUserId();
    }

    private boolean ownedBy(TaskRecord task, Long ownerUserId) {
        return task != null && ownerUserId != null && ownerUserId.equals(task.ownerUserId());
    }

    /**
     * 处理任务Comparator。
     * @param sort 排序方式
     * @return 处理结果
     */
    private Comparator<TaskRecord> taskComparator(String sort) {
        String normalizedSort = trimmed(sort, "updated_desc").toLowerCase();
        Comparator<TaskRecord> updatedDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.updatedAt()),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        Comparator<TaskRecord> createdDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.createdAt()),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        return switch (normalizedSort) {
            case "created_desc" -> createdDesc;
            case "progress_desc" -> Comparator.comparingInt((TaskRecord item) -> item.progress()).reversed().thenComparing(updatedDesc);
            case "semantic_desc" -> Comparator.comparingInt(
                (TaskRecord item) -> item.hasTimedTranscript() || item.hasTranscript() ? 1 : 0
            ).reversed().thenComparing(updatedDesc);
            case "status_desc" -> Comparator.comparing((TaskRecord item) -> stringValue(item.status())).thenComparing(updatedDesc);
            case "effect_rating_desc", "rating_desc" -> Comparator
                .comparingInt((TaskRecord item) -> item.effectRating() == null ? Integer.MIN_VALUE : item.effectRating())
                .reversed()
                .thenComparing(updatedDesc);
            default -> updatedDesc;
        };
    }

    /**
     * 处理公开案例排序。
     * 优先展示评分更高、产出更完整且更近的已完成任务。
     * @return 处理结果
     */
    private Comparator<TaskRecord> showcaseComparator() {
        Comparator<TaskRecord> updatedDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.updatedAt()),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        return Comparator
            .comparingInt((TaskRecord item) -> item.effectRating() == null ? Integer.MIN_VALUE : item.effectRating())
            .reversed()
            .thenComparing(Comparator.comparingInt(TaskRecord::completedOutputCount).reversed())
            .thenComparing(updatedDesc);
    }

    /**
     * 处理tail。
     * @param items items值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    private List<Map<String, Object>> tail(List<Map<String, Object>> items, int limit) {
        if (limit <= 0 || items.isEmpty()) {
            return List.of();
        }
        int fromIndex = Math.max(0, items.size() - limit);
        return new ArrayList<>(items.subList(fromIndex, items.size()));
    }

    private List<Map<String, Object>> chronological(List<Map<String, Object>> items) {
        if (items.isEmpty()) {
            return List.of();
        }
        List<Map<String, Object>> rows = new ArrayList<>(items);
        rows.sort(Comparator.comparing(item -> stringValue(item.get("timestamp"))));
        return rows;
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private Long longObjectValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        String normalized = stringValue(value);
        if (normalized.isBlank()) {
            return null;
        }
        try {
            return Long.parseLong(normalized);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private long longValue(Object value) {
        Long parsed = longObjectValue(value);
        return parsed == null ? 0L : parsed;
    }

    /**
     * 检查是否containsIgnoreCase。
     * @param source 来源值
     * @param query 查询值
     * @return 是否满足条件
     */
    private boolean containsIgnoreCase(String source, String query) {
        return source != null && source.toLowerCase().contains(query.toLowerCase());
    }

    /**
     * 检查是否matches状态。
     * @param task 要处理的任务对象
     * @param statusFilter 状态筛选值
     * @return 是否满足条件
     */
    private boolean matchesStatus(TaskRecord task, String statusFilter) {
        return TaskStatus.matchesFilter(task.status(), task.isQueued(), statusFilter);
    }

    /**
     * 检查任务是否适合公开案例展示。
     * @param task 要处理的任务对象
     * @return 是否满足条件
     */
    private boolean eligibleForShowcase(TaskRecord task) {
        return TaskStatus.COMPLETED.matches(task.status())
            && (task.completedOutputCount() > 0 || !task.outputs().isEmpty());
    }

    /**
     * 检查是否Running状态。
     * @param status 状态值
     * @return 是否满足条件
     */
    private boolean isRunningStatus(String status) {
        return TaskStatus.isRunningLike(status);
    }

    /**
     * 规范化状态。
     * @param status 状态值
     * @return 处理结果
     */
    private String normalizeStatus(String status) {
        return TaskStatus.normalize(status);
    }

    /**
     * 处理trimmed。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }

    /**
     * 处理当前Iso。
     * @return 处理结果
     */
    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }
}
