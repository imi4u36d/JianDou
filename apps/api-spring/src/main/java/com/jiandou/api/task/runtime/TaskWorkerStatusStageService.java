package com.jiandou.api.task.runtime;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.TaskExecutionCoordinator;
import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.domain.AttemptStatus;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStateTransition;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.domain.WorkerStatus;
import com.jiandou.api.task.persistence.TaskRepository;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * 任务工作节点状态阶段服务。
 */
@Component
class TaskWorkerStatusStageService {

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

    /**
     * 更新状态。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param nextStatus next状态值
     * @param progress 进度值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     */
    void updateStatus(
        TaskRecord task,
        TaskWorkerExecutionContext runContext,
        TaskStatus nextStatus,
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

    void updateStatus(
        TaskRecord task,
        TaskWorkerExecutionContext runContext,
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message
    ) {
        updateStatus(task, runContext, TaskStatus.from(nextStatus), progress, stage, event, message);
    }

    /**
     * 记录阶段运行。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param seq seq值
     * @param stageName 阶段Name值
     * @param clipIndex 片段索引值
     * @param inputSummary 输入摘要值
     * @param outputSummary 输出摘要值
     */
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
        row.put("stageRunId", stableId("stgrun", task.id(), stageName, String.valueOf(clipIndex)));
        row.put("attemptId", task.activeAttemptId());
        row.put("stageName", stageName);
        row.put("stageSeq", seq);
        row.put("clipIndex", clipIndex);
        row.put("status", TaskStatus.COMPLETED.value());
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

    /**
     * 创建模型调用。
     * @param task 要处理的任务对象
     * @param stage 阶段名称
     * @param operation operation值
     * @param requestPayload 请求负载值
     * @param run 运行值
     * @param result 结果值
     * @param clipIndex 片段索引值
     * @param kind 类型值
     * @return 处理结果
     */
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
        row.put("modelCallId", stableId("mdlcall", task.id(), stage, kind, String.valueOf(clipIndex)));
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

    /**
     * 记录运行调用Chain。
     * @param task 要处理的任务对象
     * @param fallbackStage 兜底阶段值
     * @param run 运行值
     * @param result 结果值
     */
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
                    /**
                     * 处理string值。
                     * @param run.get("id" 运行.get("标识"值
                     * @return 处理结果
                     */
                    "runId", stringValue(run.get("id")),
                    "status", status,
                    /**
                     * 映射值。
                     * @param map.get("details" map.get("details"值
                     * @return 处理结果
                     */
                    "details", mapValue(map.get("details"))
                )
            );
        }
    }

    /**
     * 将任务标记为完成。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param scriptRun 脚本运行值
     * @param imageRunIds 图像运行标识列表值
     * @param videoRunIds 视频运行标识列表值
     * @param clipCount 片段数量值
     * @param latestVideoOutputUrl latest视频输出URL值
     */
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
                TaskStatus.COMPLETED,
                100,
                TaskStage.PIPELINE.code(),
                "task.completed",
                "Spring worker 已通过 generation 服务完成分镜视频生成。",
                Map.of(
                    "scriptRunId", stringValue(scriptRun.get("id")),
                    "imageRunIds", imageRunIds,
                    "videoRunIds", videoRunIds,
                    "clipCount", clipCount,
                    "outputUrl", latestVideoOutputUrl
                )
            ).withAttempt(AttemptStatus.COMPLETED, ""),
            currentTask -> currentTask.setFinishedAt(nowIso())
        );
        executionCoordinator.touchWorkerInstance(
            runContext.workerInstanceId(),
            runContext.workerType(),
            WorkerStatus.RUNNING.value(),
            Map.of("lastTaskId", task.id(), "lastTaskStatus", TaskStatus.COMPLETED.value())
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
    }

    /**
     * 处理处理Abort。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param taskStatus 任务状态值
     */
    void handleAbort(TaskRecord task, TaskWorkerExecutionContext runContext, String taskStatus) {
        executionCoordinator.touchWorkerInstance(
            runContext.workerInstanceId(),
            runContext.workerType(),
            WorkerStatus.RUNNING.value(),
            Map.of("lastTaskId", task.id(), "lastTaskStatus", taskStatus)
        );
    }

    /**
     * 将任务标记为失败。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param ex ex值
     */
    void failTask(TaskRecord task, TaskWorkerExecutionContext runContext, Exception ex) {
        try {
            taskQueuePort.remove(task.id());
            task.setQueued(false);
            task.setQueuePosition(null);
            String errorMessage = ex.getMessage() == null ? "Spring worker 执行失败" : ex.getMessage();
            executionCoordinator.transitionTask(
                task,
                TaskStateTransition.error(
                    TaskStatus.FAILED,
                    task.progress(),
                    TaskStage.PIPELINE.code(),
                    "task.failed",
                    "Spring worker 执行失败。",
                    Map.of("error", errorMessage)
                ).withAttempt(AttemptStatus.FAILED, errorMessage),
                currentTask -> {
                    currentTask.setErrorMessage(errorMessage);
                    currentTask.setFinishedAt(nowIso());
                }
            );
            executionCoordinator.touchWorkerInstance(
                runContext.workerInstanceId(),
                runContext.workerType(),
                WorkerStatus.RUNNING.value(),
                Map.of("lastTaskId", task.id(), "lastTaskStatus", TaskStatus.FAILED.value())
            );
        } catch (Exception ignored) {
            executionCoordinator.touchWorkerInstance(
                runContext.workerInstanceId(),
                runContext.workerType(),
                WorkerStatus.FAILED.value(),
                Map.of("executionMode", runContext.executionMode())
            );
        }
    }

    /**
     * 映射值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
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
     * 处理stable标识。
     * @param prefix prefix值
     * @param parts parts值
     * @return 处理结果
     */
    private String stableId(String prefix, String... parts) {
        String seed = prefix + ":" + String.join(":", parts);
        return prefix + "_" + UUID.nameUUIDFromBytes(seed.getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
    }

    /**
     * 处理当前Iso。
     * @return 处理结果
     */
    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }
}
