package com.jiandou.api.task.application;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.domain.AttemptStatus;
import com.jiandou.api.task.domain.AttemptTriggerType;
import com.jiandou.api.task.domain.QueueEventType;
import com.jiandou.api.task.domain.TaskStateTransition;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.domain.WorkerStatus;
import com.jiandou.api.task.persistence.TaskPersistenceMutation;
import com.jiandou.api.task.persistence.TaskRepository;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import org.springframework.stereotype.Component;

/**
 * 任务执行协调器。
 */
@Component
public class TaskExecutionCoordinator {

    private final TaskQueuePort taskQueuePort;
    private final TaskRepository taskRepository;

    /**
     * 创建新的任务执行协调器。
     * @param taskQueuePort 任务队列端口值
     * @param taskRepository 任务仓储值
     */
    public TaskExecutionCoordinator(TaskQueuePort taskQueuePort, TaskRepository taskRepository) {
        this.taskQueuePort = taskQueuePort;
        this.taskRepository = taskRepository;
    }

    /**
     * 将enqueue加入队列。
     * @param task 要处理的任务对象
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     */
    public void enqueue(TaskRecord task, String stage, String event, String message) {
        String previousStatus = task.status();
        taskQueuePort.remove(task.id());
        task.setStatus(TaskStatus.PENDING);
        task.setErrorMessage("");
        task.setFinishedAt(null);
        task.setQueued(true);
        Map<String, Object> attempt = markActiveAttemptQueuedInMemory(task);
        taskQueuePort.enqueue(task.id());
        touch(task);

        Map<String, Object> trace = newTraceRow(stage, event, message, "INFO", Map.of("queue_mode", true));
        Map<String, Object> statusHistory = newStatusHistoryRow(task, previousStatus, TaskStatus.PENDING.value(), stage, event, message);
        Map<String, Object> queueEvent = newQueueEventRow(task, QueueEventType.ENQUEUED, Map.of("stage", stage, "event", event, "message", message));
        task.addTrace(trace);
        task.addStatusHistory(statusHistory);

        TaskPersistenceMutation mutation = new TaskPersistenceMutation()
            .task(task)
            .addTrace(trace)
            .addStatusHistory(statusHistory)
            .addQueueEvent(queueEvent);
        if (attempt != null) {
            mutation.addAttempt(attempt);
        }
        taskRepository.saveMutation(mutation);
    }

    /**
     * 将dequeue移出队列。
     * @param task 要处理的任务对象
     */
    public void dequeue(TaskRecord task) {
        boolean wasQueued = task.isQueued() || task.queuePosition() != null;
        taskQueuePort.remove(task.id());
        task.setQueued(false);
        task.setQueuePosition(null);
        touch(task);
        TaskPersistenceMutation mutation = new TaskPersistenceMutation().task(task);
        if (wasQueued) {
            mutation.addQueueEvent(newQueueEventRow(task, QueueEventType.REMOVED, Map.of("queue_mode", true)));
        }
        taskRepository.saveMutation(mutation);
    }

    /**
     * 重新计算队列Positions。
     * @param tasks 任务值
     */
    public void recomputeQueuePositions(Collection<TaskRecord> tasks) {
        Map<String, Integer> positions = new LinkedHashMap<>();
        List<String> snapshot = queueSnapshot();
        for (int index = 0; index < snapshot.size(); index++) {
            positions.put(snapshot.get(index), index + 1);
        }
        for (TaskRecord item : tasks) {
            Integer position = positions.get(item.id());
            item.setQueuePosition(position);
            item.setQueued(position != null);
        }
    }

    /**
     * 处理队列快照。
     * @return 处理结果
     */
    public List<String> queueSnapshot() {
        return new ArrayList<>(taskQueuePort.snapshot());
    }

    /**
     * 创建尝试。
     * @param task 要处理的任务对象
     * @param triggerType trigger类型值
     * @param payload 附加负载数据
     * @return 处理结果
     */
    public Map<String, Object> createAttempt(TaskRecord task, String triggerType, Map<String, Object> payload) {
        AttemptTriggerType normalized = AttemptTriggerType.from(triggerType);
        return createAttemptInternal(task, normalized == null ? stringValue(triggerType).toLowerCase(Locale.ROOT) : normalized.value(), payload);
    }

    public Map<String, Object> createAttempt(TaskRecord task, AttemptTriggerType triggerType, Map<String, Object> payload) {
        return createAttemptInternal(task, triggerType == null ? "" : triggerType.value(), payload);
    }

    private Map<String, Object> createAttemptInternal(TaskRecord task, String triggerType, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        task.setCurrentAttemptNo(task.currentAttemptNo() + 1);
        String attemptId = "att_" + UUID.randomUUID().toString().replace("-", "");
        Map<String, Object> safePayload = payload == null ? Map.of() : payload;
        task.setActiveAttemptId(attemptId);
        row.put("attemptId", attemptId);
        row.put("taskId", task.id());
        row.put("attemptNo", task.currentAttemptNo());
        row.put("triggerType", triggerType == null ? "" : triggerType);
        row.put("status", AttemptStatus.PENDING.value());
        row.put("queueName", "default");
        row.put("workerInstanceId", "");
        row.put("queueEnteredAt", null);
        row.put("queueLeftAt", null);
        row.put("claimedAt", null);
        row.put("startedAt", null);
        row.put("finishedAt", null);
        row.put("resumeFromStage", stringValue(safePayload.get("resumeFromStage")));
        row.put("resumeFromClipIndex", intValue(safePayload.get("resumeFromClipIndex"), 0));
        row.put("failureCode", "");
        row.put("failureMessage", "");
        row.put("payload", safePayload);
        task.prependAttempt(row);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addAttempt(row));
        return row;
    }

    /**
     * 标记Active尝试Queued。
     * @param task 要处理的任务对象
     */
    public void markActiveAttemptQueued(TaskRecord task) {
        Map<String, Object> attempt = markActiveAttemptQueuedInMemory(task);
        if (attempt == null) {
            return;
        }
        taskRepository.saveMutation(new TaskPersistenceMutation().taskId(task.id()).addAttempt(attempt));
    }

    /**
     * 标记Active尝试Running。
     * @param task 要处理的任务对象
     * @param workerInstanceId 工作节点实例标识
     */
    public void markActiveAttemptRunning(TaskRecord task, String workerInstanceId) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return;
        }
        String now = nowIso();
        attempt.put("status", AttemptStatus.RUNNING.value());
        attempt.put("workerInstanceId", workerInstanceId == null ? "" : workerInstanceId);
        attempt.put("claimedAt", now);
        attempt.put("queueLeftAt", now);
        attempt.put("startedAt", now);
        Map<String, Object> queueEvent = newQueueEventRow(task, QueueEventType.CLAIMED, Map.of(
            "workerInstanceId", workerInstanceId == null ? "" : workerInstanceId
        ));
        taskRepository.saveMutation(new TaskPersistenceMutation()
            .taskId(task.id())
            .addAttempt(attempt)
            .addQueueEvent(queueEvent));
    }

    /**
     * 标记Active尝试Finished。
     * @param task 要处理的任务对象
     * @param status 状态值
     * @param errorMessage errorMessage值
     */
    public void markActiveAttemptFinished(TaskRecord task, AttemptStatus status, String errorMessage) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return;
        }
        String now = nowIso();
        attempt.put("status", status == null ? "" : status.value());
        attempt.put("finishedAt", now);
        if (errorMessage != null && !errorMessage.isBlank()) {
            attempt.put("failureMessage", errorMessage);
        }
        Map<String, Object> queueEvent = newQueueEventRow(task, QueueEventType.fromAttemptStatus(status), Map.of(
            "status", status == null ? "" : status.value(),
            "errorMessage", errorMessage == null ? "" : errorMessage
        ));
        taskRepository.saveMutation(new TaskPersistenceMutation()
            .taskId(task.id())
            .addAttempt(attempt)
            .addQueueEvent(queueEvent));
    }

    public void markActiveAttemptFinished(TaskRecord task, String status, String errorMessage) {
        markActiveAttemptFinished(task, AttemptStatus.from(status), errorMessage);
    }

    /**
     * 执行任务流转。
     * @param task 要处理的任务对象
     * @param transition transition值
     */
    public void transitionTask(TaskRecord task, TaskStateTransition transition) {
        transitionTask(task, transition, null);
    }

    /**
     * 执行任务流转。
     * @param task 要处理的任务对象
     * @param transition transition值
     * @param taskMutator 任务Mutator值
     */
    public void transitionTask(TaskRecord task, TaskStateTransition transition, Consumer<TaskRecord> taskMutator) {
        if (task == null || transition == null) {
            return;
        }
        String previousStatus = task.status();
        // 先执行外部变更，再统一落状态、trace 和队列事件，避免同一次转移拆成多次持久化。
        if (taskMutator != null) {
            taskMutator.accept(task);
        }
        task.setStatus(transition.nextStatus());
        task.setProgress(transition.progress());
        Map<String, Object> trace = newTraceRow(
            transition.stage(),
            transition.event(),
            transition.message(),
            transition.level(),
            transition.payload()
        );
        Map<String, Object> statusHistory = newStatusHistoryRow(
            task,
            previousStatus,
            transition.nextStatus(),
            transition.stage(),
            transition.event(),
            transition.message()
        );
        task.addTrace(trace);
        task.addStatusHistory(statusHistory);
        touch(task);

        TaskPersistenceMutation mutation = new TaskPersistenceMutation()
            .task(task)
            .addTrace(trace)
            .addStatusHistory(statusHistory);
        // attempt 的状态变更必须和任务主状态放在同一个 mutation 中，避免前端看到短暂不一致。
        Map<String, Object> attempt = applyAttemptTransition(task, transition);
        if (attempt != null) {
            mutation
                .addAttempt(attempt)
                .addQueueEvent(newQueueEventRow(task, QueueEventType.fromAttemptStatus(transition.attemptStatusEnum()), Map.of(
                    "status", transition.attemptStatus(),
                    "errorMessage", transition.attemptErrorMessage()
                )));
        }
        taskRepository.saveMutation(mutation);
    }

    /**
     * 记录追踪。
     * @param task 要处理的任务对象
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     * @param level level值
     * @param payload 附加负载数据
     */
    public void recordTrace(TaskRecord task, String stage, String event, String message, String level, Map<String, Object> payload) {
        Map<String, Object> row = newTraceRow(stage, event, message, level, payload);
        task.addTrace(row);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addTrace(row));
    }

    /**
     * 记录状态History。
     * @param task 要处理的任务对象
     * @param previousStatus previous状态值
     * @param nextStatus next状态值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param reason reason值
     */
    public void recordStatusHistory(TaskRecord task, String previousStatus, String nextStatus, String stage, String event, String reason) {
        Map<String, Object> row = newStatusHistoryRow(task, previousStatus, nextStatus, stage, event, reason);
        task.addStatusHistory(row);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addStatusHistory(row));
    }

    /**
     * 记录阶段运行。
     * @param task 要处理的任务对象
     * @param stageRun 阶段运行值
     */
    public void recordStageRun(TaskRecord task, Map<String, Object> stageRun) {
        task.addStageRun(stageRun);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addStageRun(stageRun));
    }

    /**
     * 记录模型调用。
     * @param task 要处理的任务对象
     * @param modelCall 模型调用值
     */
    public void recordModelCall(TaskRecord task, Map<String, Object> modelCall) {
        task.addModelCall(modelCall);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addModelCall(modelCall));
    }

    /**
     * 记录素材。
     * @param task 要处理的任务对象
     * @param material 素材值
     */
    public void recordMaterial(TaskRecord task, Map<String, Object> material) {
        task.addMaterial(material);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addMaterial(material));
    }

    /**
     * 记录结果。
     * @param task 要处理的任务对象
     * @param result 结果值
     */
    public void recordResult(TaskRecord task, Map<String, Object> result) {
        task.addOutput(result);
        touch(task);
        taskRepository.saveMutation(new TaskPersistenceMutation().task(task).addResult(result));
    }

    /**
     * 记录队列事件。
     * @param task 要处理的任务对象
     * @param eventType 事件类型值
     * @param payload 附加负载数据
     */
    public void recordQueueEvent(TaskRecord task, String eventType, Map<String, Object> payload) {
        Map<String, Object> row = newQueueEventRow(task, eventType, payload);
        taskRepository.saveMutation(new TaskPersistenceMutation().taskId(task.id()).addQueueEvent(row));
    }

    public void recordQueueEvent(TaskRecord task, QueueEventType eventType, Map<String, Object> payload) {
        Map<String, Object> row = newQueueEventRow(task, eventType, payload);
        taskRepository.saveMutation(new TaskPersistenceMutation().taskId(task.id()).addQueueEvent(row));
    }

    /**
     * 处理upsert工作节点Instance。
     * @param workerInstanceId 工作节点实例标识
     * @param workerType 工作节点类型值
     * @param status 状态值
     * @param metadata metadata值
     */
    public void upsertWorkerInstance(String workerInstanceId, String workerType, String status, Map<String, Object> metadata) {
        String now = nowIso();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("workerInstanceId", workerInstanceId);
        row.put("workerType", workerType);
        row.put("queueName", "default");
        row.put("hostName", "");
        row.put("processId", ProcessHandle.current().pid());
        row.put("status", status);
        row.put("startedAt", now);
        row.put("lastHeartbeatAt", now);
        row.put("stoppedAt", "");
        row.put("metadata", metadata == null ? Map.of() : metadata);
        taskRepository.saveMutation(new TaskPersistenceMutation().addWorkerInstance(row));
    }

    /**
     * 刷新工作节点Instance。
     * @param workerInstanceId 工作节点实例标识
     * @param workerType 工作节点类型值
     * @param status 状态值
     * @param metadata metadata值
     */
    public void touchWorkerInstance(String workerInstanceId, String workerType, String status, Map<String, Object> metadata) {
        Map<String, Object> existing = taskRepository.findWorkerInstance(workerInstanceId);
        String startedAt = existing == null ? nowIso() : String.valueOf(existing.getOrDefault("startedAt", nowIso()));
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("workerInstanceId", workerInstanceId);
        row.put("workerType", workerType);
        row.put("queueName", String.valueOf(existing == null ? "default" : existing.getOrDefault("queueName", "default")));
        row.put("hostName", String.valueOf(existing == null ? "" : existing.getOrDefault("hostName", "")));
        row.put("processId", existing == null ? ProcessHandle.current().pid() : existing.getOrDefault("processId", ProcessHandle.current().pid()));
        row.put("status", status);
        row.put("startedAt", startedAt);
        row.put("lastHeartbeatAt", nowIso());
        row.put("stoppedAt", WorkerStatus.STOPPED.matches(status) || WorkerStatus.FAILED.matches(status) ? nowIso() : "");
        row.put("metadata", metadata == null ? (existing == null ? Map.of() : existing.getOrDefault("metadata", Map.of())) : metadata);
        taskRepository.saveMutation(new TaskPersistenceMutation().addWorkerInstance(row));
    }

    /**
     * 处理recoverStaleClaims。
     * @param staleBefore staleBefore值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public int recoverStaleClaims(OffsetDateTime staleBefore, int limit) {
        int recovered = 0;
        for (String workerInstanceId : taskRepository.listStaleWorkerInstanceIds(staleBefore, Math.max(1, limit))) {
            markWorkerInstanceStale(workerInstanceId);
        }
        for (Map<String, Object> claim : taskRepository.listStaleRunningClaims(staleBefore, Math.max(1, limit))) {
            String taskId = String.valueOf(claim.getOrDefault("taskId", ""));
            if (taskId.isBlank()) {
                continue;
            }
            TaskRecord task = taskRepository.findById(taskId);
            if (task == null) {
                continue;
            }
            Map<String, Object> attempt = activeAttempt(task);
            if (attempt == null || !AttemptStatus.RUNNING.matches(String.valueOf(attempt.getOrDefault("status", "")))) {
                continue;
            }
            String staleWorkerInstanceId = String.valueOf(claim.getOrDefault("workerInstanceId", ""));
            String previousStatus = task.status();
            task.setStatus(TaskStatus.PENDING);
            task.setProgress(0);
            task.setErrorMessage("");
            task.setFinishedAt(null);
            task.setQueued(true);
            task.setQueuePosition(null);
            if (task.executionContext() != null) {
                task.mutableExecutionContext().put("recoveredFromWorkerInstanceId", staleWorkerInstanceId);
                task.mutableExecutionContext().remove("workerInstanceId");
            }
            Map<String, Object> queuedAttempt = markActiveAttemptQueuedInMemory(task);
            Map<String, Object> queueEvent = newQueueEventRow(task, QueueEventType.RETRY_ENQUEUED, Map.of(
                "reason", "stale_claim_recovered",
                "staleWorkerInstanceId", staleWorkerInstanceId
            ));
            Map<String, Object> trace = newTraceRow(
                TaskStage.DISPATCH.code(),
                "task.recovered_from_stale_claim",
                "检测到失效 worker，任务已重新入队。",
                "WARN",
                Map.of("staleWorkerInstanceId", staleWorkerInstanceId)
            );
            Map<String, Object> statusHistory = newStatusHistoryRow(
                task,
                previousStatus,
                TaskStatus.PENDING.value(),
                TaskStage.DISPATCH.code(),
                "task.recovered_from_stale_claim",
                "检测到失效 worker，任务已重新入队。"
            );
            task.addTrace(trace);
            task.addStatusHistory(statusHistory);
            touch(task);
            TaskPersistenceMutation mutation = new TaskPersistenceMutation()
                .task(task)
                .addTrace(trace)
                .addStatusHistory(statusHistory)
                .addQueueEvent(queueEvent);
            if (queuedAttempt != null) {
                mutation.addAttempt(queuedAttempt);
            }
            taskRepository.saveMutation(mutation);
            recovered += 1;
        }
        return recovered;
    }

    /**
     * 刷新touch。
     * @param task 要处理的任务对象
     */
    private void touch(TaskRecord task) {
        task.setUpdatedAt(nowIso());
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return fallback;
    }

    /**
     * 处理active尝试。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId() == null || task.activeAttemptId().isBlank()) {
            return null;
        }
        for (Map<String, Object> row : task.attempts()) {
            if (task.activeAttemptId().equals(row.get("attemptId"))) {
                return row;
            }
        }
        return null;
    }

    /**
     * 处理当前Iso。
     * @return 处理结果
     */
    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    /**
     * 处理active尝试工作节点标识。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private String activeAttemptWorkerId(TaskRecord task) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return "";
        }
        Object value = attempt.get("workerInstanceId");
        return value == null ? "" : String.valueOf(value);
    }

    /**
     * 标记工作节点InstanceStale。
     * @param workerInstanceId 工作节点实例标识
     */
    private void markWorkerInstanceStale(String workerInstanceId) {
        if (workerInstanceId == null || workerInstanceId.isBlank()) {
            return;
        }
        Map<String, Object> existing = taskRepository.findWorkerInstance(workerInstanceId);
        if (existing == null || existing.isEmpty()) {
            return;
        }
        if (!WorkerStatus.RUNNING.matches(String.valueOf(existing.getOrDefault("status", "")))) {
            return;
        }
        Map<String, Object> row = new LinkedHashMap<>(existing);
        row.put("status", WorkerStatus.STALE.value());
        row.put("stoppedAt", nowIso());
        taskRepository.saveMutation(new TaskPersistenceMutation().addWorkerInstance(row));
    }

    /**
     * 标记Active尝试QueuedInMemory。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> markActiveAttemptQueuedInMemory(TaskRecord task) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return null;
        }
        String now = nowIso();
        attempt.put("status", AttemptStatus.QUEUED.value());
        attempt.put("queueEnteredAt", now);
        attempt.put("queueLeftAt", null);
        attempt.put("claimedAt", null);
        attempt.put("startedAt", null);
        attempt.put("workerInstanceId", "");
        attempt.put("finishedAt", null);
        attempt.put("failureMessage", "");
        return attempt;
    }

    /**
     * 应用尝试Transition。
     * @param task 要处理的任务对象
     * @param transition transition值
     * @return 处理结果
     */
    private Map<String, Object> applyAttemptTransition(TaskRecord task, TaskStateTransition transition) {
        if (task == null || transition == null || !transition.updatesAttempt()) {
            return null;
        }
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return null;
        }
        String now = nowIso();
        AttemptStatus status = transition.attemptStatusEnum();
        attempt.put("status", transition.attemptStatus());
        if (status == AttemptStatus.QUEUED) {
            attempt.put("queueEnteredAt", now);
            attempt.put("queueLeftAt", null);
            attempt.put("claimedAt", null);
            attempt.put("startedAt", null);
            attempt.put("workerInstanceId", "");
            attempt.put("finishedAt", null);
            attempt.put("failureMessage", "");
            return attempt;
        }
        if (status == AttemptStatus.RUNNING) {
            attempt.put("queueLeftAt", now);
            attempt.put("claimedAt", now);
            attempt.put("startedAt", now);
            attempt.put("finishedAt", null);
            attempt.put("failureMessage", "");
            return attempt;
        }
        attempt.put("finishedAt", now);
        attempt.put("failureMessage", transition.attemptErrorMessage());
        return attempt;
    }

    /**
     * 处理new追踪行。
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     * @param level level值
     * @param payload 附加负载数据
     * @return 处理结果
     */
    private Map<String, Object> newTraceRow(String stage, String event, String message, String level, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("traceId", "trace_" + UUID.randomUUID().toString().replace("-", ""));
        row.put("timestamp", nowIso());
        row.put("level", level);
        row.put("stage", stage);
        row.put("event", event);
        row.put("message", message);
        row.put("payload", payload == null ? Map.of() : payload);
        return row;
    }

    /**
     * 处理new状态History行。
     * @param task 要处理的任务对象
     * @param previousStatus previous状态值
     * @param nextStatus next状态值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param reason reason值
     * @return 处理结果
     */
    private Map<String, Object> newStatusHistoryRow(
        TaskRecord task,
        String previousStatus,
        String nextStatus,
        String stage,
        String event,
        String reason
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("statusHistoryId", "sthis_" + UUID.randomUUID().toString().replace("-", ""));
        row.put("taskId", task.id());
        row.put("previousStatus", previousStatus);
        row.put("nextStatus", nextStatus);
        row.put("progress", task.progress());
        row.put("stage", stage);
        row.put("event", event);
        row.put("reason", reason);
        row.put("operator", "system");
        row.put("changedAt", nowIso());
        row.put("payload", Map.of());
        return row;
    }

    /**
     * 处理new队列事件行。
     * @param task 要处理的任务对象
     * @param eventType 事件类型值
     * @param payload 附加负载数据
     * @return 处理结果
     */
    private Map<String, Object> newQueueEventRow(TaskRecord task, String eventType, Map<String, Object> payload) {
        QueueEventType normalized = QueueEventType.from(eventType);
        if (normalized != null) {
            return newQueueEventRow(task, normalized, payload);
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskQueueEventId", "queueevt_" + UUID.randomUUID().toString().replace("-", ""));
        row.put("taskId", task.id());
        row.put("attemptId", task.activeAttemptId() == null ? "" : task.activeAttemptId());
        row.put("queueName", "default");
        row.put("eventType", eventType);
        row.put("workerInstanceId", activeAttemptWorkerId(task));
        row.put("queuePositionHint", task.queuePosition() == null ? 0 : task.queuePosition());
        row.put("payload", payload == null ? Map.of() : payload);
        row.put("eventTime", nowIso());
        return row;
    }

    private Map<String, Object> newQueueEventRow(TaskRecord task, QueueEventType eventType, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskQueueEventId", "queueevt_" + UUID.randomUUID().toString().replace("-", ""));
        row.put("taskId", task.id());
        row.put("attemptId", task.activeAttemptId() == null ? "" : task.activeAttemptId());
        row.put("queueName", "default");
        row.put("eventType", eventType == null ? "" : eventType.value());
        row.put("workerInstanceId", activeAttemptWorkerId(task));
        row.put("queuePositionHint", task.queuePosition() == null ? 0 : task.queuePosition());
        row.put("payload", payload == null ? Map.of() : payload);
        row.put("eventTime", nowIso());
        return row;
    }
}
