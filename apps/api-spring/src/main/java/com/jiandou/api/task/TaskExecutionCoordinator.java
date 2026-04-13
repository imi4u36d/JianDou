package com.jiandou.api.task;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class TaskExecutionCoordinator {

    private final TaskQueuePort taskQueuePort;
    private final TaskRepository taskRepository;

    public TaskExecutionCoordinator(TaskQueuePort taskQueuePort, TaskRepository taskRepository) {
        this.taskQueuePort = taskQueuePort;
        this.taskRepository = taskRepository;
    }

    public void enqueue(TaskRecord task, String stage, String event, String message) {
        String previousStatus = task.status;
        dequeue(task);
        task.status = "PENDING";
        task.errorMessage = "";
        task.finishedAt = null;
        task.isQueued = true;
        markActiveAttemptQueued(task);
        taskQueuePort.enqueue(task.id);
        touch(task);
        recordTrace(task, stage, event, message, "INFO", Map.of("queue_mode", true));
        recordStatusHistory(task, previousStatus, "PENDING", stage, event, message);
        recordQueueEvent(task, "enqueued", Map.of("stage", stage, "event", event, "message", message));
        taskRepository.save(task);
    }

    public void dequeue(TaskRecord task) {
        boolean wasQueued = task.isQueued || task.queuePosition != null;
        taskQueuePort.remove(task.id);
        task.isQueued = false;
        task.queuePosition = null;
        if (wasQueued) {
            recordQueueEvent(task, "removed", Map.of("queue_mode", true));
        }
        taskRepository.save(task);
    }

    public void recomputeQueuePositions(Collection<TaskRecord> tasks) {
        Map<String, Integer> positions = new LinkedHashMap<>();
        List<String> snapshot = queueSnapshot();
        for (int index = 0; index < snapshot.size(); index++) {
            positions.put(snapshot.get(index), index + 1);
        }
        for (TaskRecord item : tasks) {
            Integer position = positions.get(item.id);
            item.queuePosition = position;
            item.isQueued = position != null;
        }
    }

    public List<String> queueSnapshot() {
        return new ArrayList<>(taskQueuePort.snapshot());
    }

    public Map<String, Object> createAttempt(TaskRecord task, String triggerType, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        task.currentAttemptNo += 1;
        String attemptId = "att_" + UUID.randomUUID().toString().replace("-", "");
        Map<String, Object> safePayload = payload == null ? Map.of() : payload;
        task.activeAttemptId = attemptId;
        row.put("attemptId", attemptId);
        row.put("taskId", task.id);
        row.put("attemptNo", task.currentAttemptNo);
        row.put("triggerType", triggerType);
        row.put("status", "PENDING");
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
        task.attempts.add(0, row);
        touch(task);
        taskRepository.save(task);
        taskRepository.saveAttempt(task.id, row);
        return row;
    }

    public void markActiveAttemptQueued(TaskRecord task) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return;
        }
        String now = nowIso();
        attempt.put("status", "QUEUED");
        attempt.put("queueEnteredAt", now);
        attempt.put("queueLeftAt", null);
        attempt.put("claimedAt", null);
        attempt.put("startedAt", null);
        attempt.put("workerInstanceId", "");
        attempt.put("finishedAt", null);
        attempt.put("failureMessage", "");
        taskRepository.saveAttempt(task.id, attempt);
    }

    public void markActiveAttemptRunning(TaskRecord task, String workerInstanceId) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return;
        }
        String now = nowIso();
        attempt.put("status", "RUNNING");
        attempt.put("workerInstanceId", workerInstanceId == null ? "" : workerInstanceId);
        attempt.put("claimedAt", now);
        attempt.put("queueLeftAt", now);
        attempt.put("startedAt", now);
        taskRepository.saveAttempt(task.id, attempt);
        recordQueueEvent(task, "claimed", Map.of("workerInstanceId", workerInstanceId == null ? "" : workerInstanceId));
    }

    public void markActiveAttemptFinished(TaskRecord task, String status, String errorMessage) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return;
        }
        String now = nowIso();
        attempt.put("status", status);
        attempt.put("finishedAt", now);
        if (errorMessage != null && !errorMessage.isBlank()) {
            attempt.put("failureMessage", errorMessage);
        }
        taskRepository.saveAttempt(task.id, attempt);
        recordQueueEvent(task, status == null ? "finished" : status.toLowerCase(), Map.of(
            "status", status == null ? "" : status,
            "errorMessage", errorMessage == null ? "" : errorMessage
        ));
    }

    public void recordTrace(TaskRecord task, String stage, String event, String message, String level, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("traceId", "trace_" + java.util.UUID.randomUUID().toString().replace("-", ""));
        row.put("timestamp", nowIso());
        row.put("level", level);
        row.put("stage", stage);
        row.put("event", event);
        row.put("message", message);
        row.put("payload", payload);
        task.trace.add(row);
        taskRepository.saveTrace(task.id, row);
        touch(task);
        taskRepository.save(task);
    }

    public void recordStatusHistory(TaskRecord task, String previousStatus, String nextStatus, String stage, String event, String reason) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("statusHistoryId", "sthis_" + java.util.UUID.randomUUID().toString().replace("-", ""));
        row.put("taskId", task.id);
        row.put("previousStatus", previousStatus);
        row.put("nextStatus", nextStatus);
        row.put("progress", task.progress);
        row.put("stage", stage);
        row.put("event", event);
        row.put("reason", reason);
        row.put("operator", "system");
        row.put("changedAt", nowIso());
        row.put("payload", Map.of());
        task.statusHistory.add(row);
        taskRepository.saveStatusHistory(task.id, row);
        taskRepository.save(task);
    }

    public void recordStageRun(TaskRecord task, Map<String, Object> stageRun) {
        task.stageRuns.add(stageRun);
        taskRepository.saveStageRun(task.id, stageRun);
        touch(task);
        taskRepository.save(task);
    }

    public void recordModelCall(TaskRecord task, Map<String, Object> modelCall) {
        task.modelCalls.add(modelCall);
        taskRepository.saveModelCall(task.id, modelCall);
        touch(task);
        taskRepository.save(task);
    }

    public void recordMaterial(TaskRecord task, Map<String, Object> material) {
        task.materials.add(material);
        taskRepository.saveMaterial(task.id, material);
        touch(task);
        taskRepository.save(task);
    }

    public void recordResult(TaskRecord task, Map<String, Object> result) {
        task.outputs.add(result);
        taskRepository.saveResult(task.id, result);
        touch(task);
        taskRepository.save(task);
    }

    public void recordQueueEvent(TaskRecord task, String eventType, Map<String, Object> payload) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskQueueEventId", "queueevt_" + java.util.UUID.randomUUID().toString().replace("-", ""));
        row.put("taskId", task.id);
        row.put("attemptId", task.activeAttemptId == null ? "" : task.activeAttemptId);
        row.put("queueName", "default");
        row.put("eventType", eventType);
        row.put("workerInstanceId", activeAttemptWorkerId(task));
        row.put("queuePositionHint", task.queuePosition == null ? 0 : task.queuePosition);
        row.put("payload", payload == null ? Map.of() : payload);
        row.put("eventTime", nowIso());
        taskRepository.saveQueueEvent(task.id, row);
    }

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
        taskRepository.saveWorkerInstance(row);
    }

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
        row.put("stoppedAt", "STOPPED".equalsIgnoreCase(status) || "FAILED".equalsIgnoreCase(status) ? nowIso() : "");
        row.put("metadata", metadata == null ? (existing == null ? Map.of() : existing.getOrDefault("metadata", Map.of())) : metadata);
        taskRepository.saveWorkerInstance(row);
    }

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
            if (attempt == null || !"RUNNING".equals(String.valueOf(attempt.getOrDefault("status", "")))) {
                continue;
            }
            String staleWorkerInstanceId = String.valueOf(claim.getOrDefault("workerInstanceId", ""));
            String previousStatus = task.status;
            task.status = "PENDING";
            task.progress = 0;
            task.errorMessage = "";
            task.finishedAt = null;
            task.isQueued = true;
            task.queuePosition = null;
            if (task.executionContext != null) {
                task.executionContext.put("recoveredFromWorkerInstanceId", staleWorkerInstanceId);
                task.executionContext.remove("workerInstanceId");
            }
            markActiveAttemptQueued(task);
            recordQueueEvent(task, "retry_enqueued", Map.of(
                "reason", "stale_claim_recovered",
                "staleWorkerInstanceId", staleWorkerInstanceId
            ));
            recordTrace(task, "dispatch", "task.recovered_from_stale_claim", "检测到失效 worker，任务已重新入队。", "WARN", Map.of(
                "staleWorkerInstanceId", staleWorkerInstanceId
            ));
            recordStatusHistory(task, previousStatus, "PENDING", "dispatch", "task.recovered_from_stale_claim", "检测到失效 worker，任务已重新入队。");
            touch(task);
            taskRepository.save(task);
            recovered += 1;
        }
        return recovered;
    }

    private void touch(TaskRecord task) {
        task.updatedAt = nowIso();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

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

    private Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId == null || task.activeAttemptId.isBlank()) {
            return null;
        }
        for (Map<String, Object> row : task.attempts) {
            if (task.activeAttemptId.equals(row.get("attemptId"))) {
                return row;
            }
        }
        return null;
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    private String activeAttemptWorkerId(TaskRecord task) {
        Map<String, Object> attempt = activeAttempt(task);
        if (attempt == null) {
            return "";
        }
        Object value = attempt.get("workerInstanceId");
        return value == null ? "" : String.valueOf(value);
    }

    private void markWorkerInstanceStale(String workerInstanceId) {
        if (workerInstanceId == null || workerInstanceId.isBlank()) {
            return;
        }
        Map<String, Object> existing = taskRepository.findWorkerInstance(workerInstanceId);
        if (existing == null || existing.isEmpty()) {
            return;
        }
        if (!"RUNNING".equalsIgnoreCase(String.valueOf(existing.getOrDefault("status", "")))) {
            return;
        }
        Map<String, Object> row = new LinkedHashMap<>(existing);
        row.put("status", "STALE");
        row.put("stoppedAt", nowIso());
        taskRepository.saveWorkerInstance(row);
    }
}
