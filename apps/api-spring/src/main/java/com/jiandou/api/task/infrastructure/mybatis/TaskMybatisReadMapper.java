package com.jiandou.api.task.infrastructure.mybatis;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.persistence.TaskRow;
import com.jiandou.api.task.persistence.TaskStatusHistoryRow;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class TaskMybatisReadMapper {

    TaskRow toTaskRow(TaskEntity entity) {
        return new TaskRow(
            entity.getTaskId(),
            entity.getTaskType(),
            entity.getTitle(),
            entity.getDescription(),
            entity.getAspectRatio(),
            TaskMybatisValueSupport.defaultInt(entity.getMinDurationSeconds()),
            TaskMybatisValueSupport.defaultInt(entity.getMaxDurationSeconds()),
            TaskMybatisValueSupport.defaultInt(entity.getOutputCount()),
            entity.getSourcePrimaryAssetId(),
            entity.getSourceFileName(),
            MybatisJsonSupport.readStringList(entity.getSourceAssetIdsJson()),
            MybatisJsonSupport.readStringList(entity.getSourceFileNamesJson()),
            MybatisJsonSupport.readMap(entity.getRequestPayloadJson()),
            MybatisJsonSupport.readMap(entity.getContextJson()),
            entity.getIntroTemplate(),
            entity.getOutroTemplate(),
            entity.getCreativePrompt(),
            entity.getTaskSeed(),
            entity.getEffectRating(),
            entity.getEffectRatingNote(),
            entity.getRatedAt(),
            entity.getModelProvider(),
            entity.getExecutionMode(),
            entity.getEditingMode(),
            entity.getStatus(),
            TaskMybatisValueSupport.defaultInt(entity.getProgress()),
            entity.getErrorCode(),
            entity.getErrorMessage(),
            entity.getPlanJson(),
            TaskMybatisValueSupport.defaultInt(entity.getRetryCount()),
            TaskMybatisValueSupport.defaultInt(entity.getTimezoneOffsetMinutes()),
            entity.getStartedAt(),
            entity.getFinishedAt(),
            entity.getCreateTime(),
            entity.getUpdateTime()
        );
    }

    Map<String, Object> toStaleRunningClaimMap(StaleRunningTaskRow item) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskId", item.taskId());
        row.put("workerInstanceId", item.workerInstanceId());
        return row;
    }

    Map<String, Object> toQueueEventMap(TaskQueueEventEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskQueueEventId", entity.getTaskQueueEventId());
        row.put("taskId", entity.getTaskId());
        row.put("attemptId", entity.getAttemptId());
        row.put("queueName", entity.getQueueName());
        row.put("eventType", entity.getEventType());
        row.put("workerInstanceId", entity.getWorkerInstanceId());
        row.put("queuePositionHint", TaskMybatisValueSupport.defaultInt(entity.getQueuePositionHint()));
        row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
        row.put("eventTime", TaskMybatisValueSupport.format(entity.getEventTime()));
        row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
        return row;
    }

    Map<String, Object> toWorkerInstanceMap(WorkerInstanceEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("workerInstanceId", entity.getWorkerInstanceId());
        row.put("workerType", entity.getWorkerType());
        row.put("queueName", entity.getQueueName());
        row.put("hostName", entity.getHostName());
        row.put("processId", TaskMybatisValueSupport.defaultInt(entity.getProcessId()));
        row.put("status", entity.getStatus());
        row.put("startedAt", TaskMybatisValueSupport.format(entity.getStartedAt()));
        row.put("lastHeartbeatAt", TaskMybatisValueSupport.format(entity.getLastHeartbeatAt()));
        row.put("stoppedAt", TaskMybatisValueSupport.format(entity.getStoppedAt()));
        row.put("metadata", MybatisJsonSupport.readMap(entity.getMetadataJson()));
        row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
        row.put("updatedAt", TaskMybatisValueSupport.format(entity.getUpdateTime()));
        return row;
    }

    Map<String, Object> toTraceMap(SystemLogEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("traceId", entity.getTraceId());
        row.put("taskId", entity.getTaskId());
        row.put("timestamp", TaskMybatisValueSupport.format(entity.getLoggedAt()));
        row.put("level", entity.getLevel());
        row.put("stage", entity.getStage());
        row.put("event", entity.getEvent());
        row.put("message", entity.getMessage());
        row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
        row.put("source", entity.getSource());
        row.put("serviceName", entity.getServiceName());
        row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
        return row;
    }

    TaskStatusHistoryRow toStatusHistoryRow(TaskStatusHistoryEntity entity) {
        return new TaskStatusHistoryRow(
            entity.getTaskStatusHistoryId(),
            entity.getTaskId(),
            entity.getPreviousStatus(),
            entity.getCurrentStatus(),
            TaskMybatisValueSupport.defaultInt(entity.getProgress()),
            entity.getStage(),
            entity.getEvent(),
            entity.getMessage(),
            MybatisJsonSupport.readMap(entity.getPayloadJson()),
            entity.getChangeTime(),
            entity.getOperatorType(),
            entity.getOperatorId(),
            TaskMybatisValueSupport.defaultInt(entity.getTimezoneOffsetMinutes()),
            entity.getCreateTime(),
            entity.getUpdateTime()
        );
    }

    void applyAttempts(TaskRecord task, List<TaskAttemptEntity> entities) {
        task.attemptsView().clear();
        for (TaskAttemptEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("attemptId", entity.getTaskAttemptId());
            row.put("taskId", entity.getTaskId());
            row.put("attemptNo", entity.getAttemptNo());
            row.put("triggerType", entity.getTriggerType());
            row.put("status", entity.getStatus());
            row.put("queueName", entity.getQueueName());
            row.put("workerInstanceId", entity.getWorkerInstanceId());
            row.put("queueEnteredAt", TaskMybatisValueSupport.format(entity.getQueueEnteredAt()));
            row.put("queueLeftAt", TaskMybatisValueSupport.format(entity.getQueueLeftAt()));
            row.put("claimedAt", TaskMybatisValueSupport.format(entity.getClaimedAt()));
            row.put("startedAt", TaskMybatisValueSupport.format(entity.getStartedAt()));
            row.put("finishedAt", TaskMybatisValueSupport.format(entity.getFinishedAt()));
            row.put("resumeFromStage", entity.getResumeFromStage());
            row.put("resumeFromClipIndex", TaskMybatisValueSupport.defaultInt(entity.getResumeFromClipIndex()));
            row.put("failureCode", entity.getFailureCode());
            row.put("failureMessage", entity.getFailureMessage());
            row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
            task.attemptsView().add(row);
        }
        if (!entities.isEmpty()) {
            TaskAttemptEntity active = entities.get(0);
            task.setActiveAttempt(active.getTaskAttemptId(), TaskMybatisValueSupport.defaultInt(active.getAttemptNo()));
        }
    }

    void applyStageRuns(TaskRecord task, List<TaskStageRunEntity> entities) {
        task.stageRunsView().clear();
        for (TaskStageRunEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("stageRunId", entity.getTaskStageRunId());
            row.put("taskId", entity.getTaskId());
            row.put("attemptId", entity.getAttemptId());
            row.put("stageName", entity.getStageName());
            row.put("stageSeq", TaskMybatisValueSupport.defaultInt(entity.getStageSeq()));
            row.put("clipIndex", TaskMybatisValueSupport.defaultInt(entity.getClipIndex()));
            row.put("status", entity.getStatus());
            row.put("workerInstanceId", entity.getWorkerInstanceId());
            row.put("startedAt", TaskMybatisValueSupport.format(entity.getStartedAt()));
            row.put("finishedAt", TaskMybatisValueSupport.format(entity.getFinishedAt()));
            row.put("durationMs", TaskMybatisValueSupport.defaultInt(entity.getDurationMs()));
            row.put("inputSummary", MybatisJsonSupport.readMap(entity.getInputSummaryJson()));
            row.put("outputSummary", MybatisJsonSupport.readMap(entity.getOutputSummaryJson()));
            row.put("errorCode", entity.getErrorCode());
            row.put("errorMessage", entity.getErrorMessage());
            task.stageRunsView().add(row);
        }
    }

    void applyModelCalls(TaskRecord task, List<TaskModelCallEntity> entities) {
        task.modelCallsView().clear();
        for (TaskModelCallEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("modelCallId", entity.getTaskModelCallId());
            row.put("taskId", entity.getTaskId());
            row.put("provider", entity.getProvider());
            row.put("modelName", TaskMybatisValueSupport.stringValue(
                entity.getModelName().isBlank() ? entity.getModelAlias() : entity.getModelName()
            ));
            row.put("operationKind", entity.getOperation());
            row.put("status", TaskMybatisValueSupport.defaultInt(entity.getSuccess()) == 1 ? "success" : "failed");
            row.put("latencyMs", TaskMybatisValueSupport.defaultInt(entity.getLatencyMs()));
            row.put("requestPayload", MybatisJsonSupport.readMap(entity.getRequestPayloadJson()));
            row.put("responsePayload", MybatisJsonSupport.readMap(entity.getResponsePayloadJson()));
            row.put("responseCode", TaskMybatisValueSupport.defaultInt(entity.getResponseStatusCode()));
            row.put("errorCode", entity.getErrorCode());
            row.put("errorMessage", entity.getErrorMessage());
            row.put("startedAt", TaskMybatisValueSupport.format(entity.getStartedAt()));
            row.put("finishedAt", TaskMybatisValueSupport.format(entity.getFinishedAt()));
            row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
            task.modelCallsView().add(row);
        }
    }

    void applyMaterials(TaskRecord task, List<MaterialAssetEntity> entities) {
        task.materialsView().clear();
        for (MaterialAssetEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", entity.getMaterialAssetId());
            row.put("kind", entity.getAssetRole());
            row.put("mediaType", entity.getMediaType());
            row.put("title", entity.getTitle());
            row.put("originProvider", entity.getOriginProvider());
            row.put("originModel", entity.getOriginModel());
            row.put("remoteTaskId", entity.getRemoteTaskId());
            row.put("remoteAssetId", entity.getRemoteAssetId());
            row.put("originalFileName", entity.getOriginalFileName());
            row.put("storedFileName", entity.getStoredFileName());
            row.put("fileExt", entity.getFileExt());
            row.put("storageProvider", entity.getStorageProvider());
            row.put("fileUrl", entity.getPublicUrl());
            row.put("previewUrl", entity.getPublicUrl());
            row.put("mimeType", entity.getMimeType());
            row.put("durationSeconds", TaskMybatisValueSupport.defaultDouble(entity.getDurationSeconds()));
            row.put("width", TaskMybatisValueSupport.defaultInt(entity.getWidth()));
            row.put("height", TaskMybatisValueSupport.defaultInt(entity.getHeight()));
            row.put("hasAudio", TaskMybatisValueSupport.defaultInt(entity.getHasAudio()) == 1);
            row.put("sizeBytes", TaskMybatisValueSupport.defaultLong(entity.getSizeBytes()));
            row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
            row.put("storagePath", entity.getLocalStoragePath());
            row.put("localFilePath", entity.getLocalFilePath());
            row.put("remoteUrl", entity.getRemoteUrl());
            row.put("thirdPartyUrl", entity.getThirdPartyUrl());
            row.put("metadata", MybatisJsonSupport.readMap(entity.getMetadataJson()));
            task.materialsView().add(row);
        }
    }

    void applyResults(TaskRecord task, List<TaskResultEntity> entities) {
        task.outputsView().clear();
        for (TaskResultEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", entity.getTaskResultId());
            row.put("resultType", entity.getResultType());
            row.put("clipIndex", TaskMybatisValueSupport.defaultInt(entity.getClipIndex()));
            row.put("title", entity.getTitle());
            row.put("reason", entity.getReason());
            row.put("sourceModelCallId", entity.getSourceModelCallId());
            row.put("startSeconds", TaskMybatisValueSupport.defaultDouble(entity.getStartSeconds()));
            row.put("endSeconds", TaskMybatisValueSupport.defaultDouble(entity.getEndSeconds()));
            row.put("durationSeconds", TaskMybatisValueSupport.defaultDouble(entity.getDurationSeconds()));
            row.put("previewUrl", entity.getPreviewPath());
            row.put("downloadUrl", entity.getDownloadPath());
            row.put("mimeType", entity.getMimeType());
            row.put("width", TaskMybatisValueSupport.defaultInt(entity.getWidth()));
            row.put("height", TaskMybatisValueSupport.defaultInt(entity.getHeight()));
            row.put("sizeBytes", TaskMybatisValueSupport.defaultLong(entity.getSizeBytes()));
            row.put("materialAssetId", entity.getMaterialAssetId());
            row.put("remoteUrl", entity.getRemoteUrl());
            row.put("extra", MybatisJsonSupport.readMap(entity.getExtraJson()));
            row.put("createdAt", TaskMybatisValueSupport.format(entity.getCreateTime()));
            task.outputsView().add(row);
        }
    }

    void applyTrace(TaskRecord task, List<SystemLogEntity> entities) {
        task.traceView().clear();
        for (SystemLogEntity entity : entities) {
            task.traceView().add(toTraceMap(entity));
        }
    }
}
