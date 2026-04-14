package com.jiandou.api.task;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
final class TaskWorkerStatusStageService {

    private final TaskRepository taskRepository;
    private final TaskQueuePort taskQueuePort;
    private final TaskExecutionCoordinator executionCoordinator;

    TaskWorkerStatusStageService(
        TaskRepository taskRepository,
        TaskQueuePort taskQueuePort,
        TaskExecutionCoordinator executionCoordinator
    ) {
        this.taskRepository = taskRepository;
        this.taskQueuePort = taskQueuePort;
        this.executionCoordinator = executionCoordinator;
    }

    void updateStatus(
        TaskRecord task,
        TaskWorkerExecutionContext runContext,
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message
    ) {
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.info(
                nextStatus,
                progress,
                stage,
                event,
                message,
                Map.of("workerInstanceId", runContext.workerInstanceId())
            )
        );
    }

    void recordStageRun(
        TaskRecord task,
        TaskWorkerExecutionContext runContext,
        int seq,
        String stageName,
        int clipIndex,
        Map<String, Object> inputSummary,
        Map<String, Object> outputSummary
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        String now = nowIso();
        row.put("stageRunId", stableId("stgrun", task.id, stageName, String.valueOf(clipIndex)));
        row.put("attemptId", task.activeAttemptId);
        row.put("stageName", stageName);
        row.put("stageSeq", seq);
        row.put("clipIndex", clipIndex);
        row.put("status", "COMPLETED");
        row.put("workerInstanceId", runContext.workerInstanceId());
        row.put("startedAt", now);
        row.put("finishedAt", now);
        row.put("durationMs", 0);
        row.put("inputSummary", inputSummary);
        row.put("outputSummary", outputSummary);
        row.put("errorCode", "");
        row.put("errorMessage", "");
        executionCoordinator.recordStageRun(task, row);
    }

    Map<String, Object> createModelCall(
        TaskRecord task,
        String stage,
        String operation,
        Map<String, Object> requestPayload,
        Map<String, Object> run,
        Map<String, Object> result,
        int clipIndex,
        String kind
    ) {
        Map<String, Object> modelInfo = mapValue(result.get("modelInfo"));
        String now = nowIso();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", stableId("mdlcall", task.id, stage, kind, String.valueOf(clipIndex)));
        row.put("callKind", stage);
        row.put("stage", stage);
        row.put("operation", operation);
        row.put("provider", stringValue(modelInfo.getOrDefault("provider", "spring-placeholder")));
        row.put("providerModel", stringValue(modelInfo.get("providerModel")));
        row.put("requestedModel", stringValue(modelInfo.get("requestedModel")));
        row.put("resolvedModel", stringValue(modelInfo.get("resolvedModel")));
        row.put("modelName", stringValue(modelInfo.getOrDefault("modelName", modelInfo.get("resolvedModel"))));
        row.put("modelAlias", stringValue(modelInfo.getOrDefault("modelName", modelInfo.get("resolvedModel"))));
        row.put("endpointHost", stringValue(modelInfo.get("endpointHost")));
        row.put("requestId", stringValue(run.get("id")));
        row.put("requestPayload", requestPayload);
        row.put("responsePayload", Map.of("runId", stringValue(run.get("id")), "result", result));
        row.put("httpStatus", 200);
        row.put("responseCode", 200);
        row.put("success", true);
        row.put("errorCode", "");
        row.put("errorMessage", "");
        row.put("latencyMs", 0);
        row.put("inputTokens", 0);
        row.put("outputTokens", 0);
        row.put("startedAt", stringValue(run.getOrDefault("createdAt", now)));
        row.put("finishedAt", stringValue(run.getOrDefault("updatedAt", row.get("startedAt"))));
        return row;
    }

    void recordRunCallChain(TaskRecord task, String fallbackStage, Map<String, Object> run, Map<String, Object> result) {
        Object raw = result.get("callChain");
        if (!(raw instanceof List<?> items)) {
            return;
        }
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            String stage = stringValue(map.get("stage"));
            String event = stringValue(map.get("event"));
            String message = stringValue(map.get("message"));
            String status = stringValue(map.get("status"));
            String level = "success".equalsIgnoreCase(status) ? "INFO" : "WARN";
            executionCoordinator.recordTrace(task,
                stage.isBlank() ? fallbackStage : stage,
                event.isBlank() ? "generation.call" : event,
                message.isBlank() ? "generation run completed" : message,
                level,
                Map.of(
                    "runId", stringValue(run.get("id")),
                    "status", status,
                    "details", mapValue(map.get("details"))
                )
            );
        }
    }

    void completeTask(
        TaskRecord task,
        TaskWorkerExecutionContext runContext,
        Map<String, Object> scriptRun,
        List<String> imageRunIds,
        List<String> videoRunIds,
        int clipCount,
        String latestVideoOutputUrl
    ) {
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.info(
                "COMPLETED",
                100,
                "pipeline",
                "task.completed",
                "Spring worker 已通过 generation 服务完成分镜视频生成。",
                Map.of(
                    "scriptRunId", stringValue(scriptRun.get("id")),
                    "imageRunIds", imageRunIds,
                    "videoRunIds", videoRunIds,
                    "clipCount", clipCount,
                    "outputUrl", latestVideoOutputUrl
                )
            ).withAttempt("COMPLETED", ""),
            currentTask -> currentTask.finishedAt = nowIso()
        );
        executionCoordinator.touchWorkerInstance(
            runContext.workerInstanceId(),
            runContext.workerType(),
            "RUNNING",
            Map.of("lastTaskId", task.id, "lastTaskStatus", "COMPLETED")
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
    }

    void handleAbort(TaskRecord task, TaskWorkerExecutionContext runContext, String taskStatus) {
        executionCoordinator.touchWorkerInstance(
            runContext.workerInstanceId(),
            runContext.workerType(),
            "RUNNING",
            Map.of("lastTaskId", task.id, "lastTaskStatus", taskStatus)
        );
    }

    void failTask(TaskRecord task, TaskWorkerExecutionContext runContext, Exception ex) {
        try {
            taskQueuePort.remove(task.id);
            task.isQueued = false;
            task.queuePosition = null;
            String errorMessage = ex.getMessage() == null ? "Spring worker 执行失败" : ex.getMessage();
            executionCoordinator.transitionTask(
                task,
                TaskStateTransition.error(
                    "FAILED",
                    task.progress,
                    "pipeline",
                    "task.failed",
                    "Spring worker 执行失败。",
                    Map.of("error", errorMessage)
                ).withAttempt("FAILED", errorMessage),
                currentTask -> {
                    currentTask.errorMessage = errorMessage;
                    currentTask.finishedAt = nowIso();
                }
            );
            executionCoordinator.touchWorkerInstance(
                runContext.workerInstanceId(),
                runContext.workerType(),
                "RUNNING",
                Map.of("lastTaskId", task.id, "lastTaskStatus", "FAILED")
            );
        } catch (Exception ignored) {
            executionCoordinator.touchWorkerInstance(
                runContext.workerInstanceId(),
                runContext.workerType(),
                "FAILED",
                Map.of("executionMode", runContext.executionMode())
            );
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String stableId(String prefix, String... parts) {
        String seed = prefix + ":" + String.join(":", parts);
        return prefix + "_" + UUID.nameUUIDFromBytes(seed.getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }
}
