package com.jiandou.api.task.infrastructure.mybatis;

import com.jiandou.api.task.domain.ExecutionMode;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.persistence.TaskRecordAssembler;
import java.util.Map;

/**
 * 任务MyBatis写入MyBatis Mapper。
 */
final class TaskMybatisWriteMapper {

    private static final int DEFAULT_TIMEZONE_OFFSET_MINUTES = 480;

    /**
     * 处理转为任务实体。
     * @param model 模型值
     * @return 处理结果
     */
    TaskEntity toTaskEntity(TaskRecordAssembler.TaskWriteModel model) {
        TaskEntity entity = new TaskEntity();
        entity.setTaskId(model.taskId());
        entity.setTaskType("generation");
        entity.setTitle(model.title());
        entity.setDescription("");
        entity.setAspectRatio(model.aspectRatio());
        entity.setMinDurationSeconds(model.minDurationSeconds());
        entity.setMaxDurationSeconds(model.maxDurationSeconds());
        entity.setOutputCount(model.completedOutputCount());
        entity.setSourcePrimaryAssetId("");
        entity.setSourceFileName(model.sourceFileName());
        entity.setSourceAssetIdsJson(MybatisJsonSupport.write(model.sourceAssetIds()));
        entity.setSourceFileNamesJson(MybatisJsonSupport.write(model.sourceFileNames()));
        entity.setRequestPayloadJson(MybatisJsonSupport.write(model.requestPayload()));
        entity.setContextJson(MybatisJsonSupport.write(model.context()));
        entity.setIntroTemplate(model.introTemplate());
        entity.setOutroTemplate(model.outroTemplate());
        entity.setCreativePrompt(model.creativePrompt());
        entity.setTaskSeed(model.taskSeed());
        entity.setEffectRating(model.effectRating());
        entity.setEffectRatingNote(model.effectRatingNote());
        entity.setRatedAt(model.ratedAt());
        entity.setModelProvider("");
        entity.setExecutionMode(ExecutionMode.QUEUE.value());
        entity.setEditingMode(model.editingMode());
        entity.setStatus(model.status());
        entity.setProgress(model.progress());
        entity.setErrorCode("");
        entity.setErrorMessage(model.errorMessage());
        entity.setPlanJson("");
        entity.setRetryCount(model.retryCount());
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setStartedAt(model.startedAt());
        entity.setFinishedAt(model.finishedAt());
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为尝试实体。
     * @param taskId 任务标识
     * @param attempt 尝试值
     * @return 处理结果
     */
    TaskAttemptEntity toAttemptEntity(String taskId, Map<String, Object> attempt) {
        TaskAttemptEntity entity = new TaskAttemptEntity();
        entity.setTaskAttemptId(TaskMybatisValueSupport.stringValue(attempt.get("attemptId")));
        entity.setTaskId(taskId);
        entity.setAttemptNo(TaskMybatisValueSupport.intValue(attempt.get("attemptNo"), 1));
        entity.setTriggerType(TaskMybatisValueSupport.stringValue(attempt.get("triggerType")));
        entity.setStatus(TaskMybatisValueSupport.stringValue(attempt.get("status")));
        entity.setQueueName(TaskMybatisValueSupport.stringValue(attempt.get("queueName")));
        entity.setWorkerInstanceId(TaskMybatisValueSupport.stringValue(attempt.get("workerInstanceId")));
        entity.setQueueEnteredAt(TaskMybatisValueSupport.offsetValue(attempt.get("queueEnteredAt")));
        entity.setQueueLeftAt(TaskMybatisValueSupport.offsetValue(attempt.get("queueLeftAt")));
        entity.setClaimedAt(TaskMybatisValueSupport.offsetValue(attempt.get("claimedAt")));
        entity.setStartedAt(TaskMybatisValueSupport.offsetValue(attempt.get("startedAt")));
        entity.setFinishedAt(TaskMybatisValueSupport.offsetValue(attempt.get("finishedAt")));
        entity.setResumeFromStage(TaskMybatisValueSupport.stringValue(attempt.get("resumeFromStage")));
        entity.setResumeFromClipIndex(TaskMybatisValueSupport.intValue(attempt.get("resumeFromClipIndex"), 0));
        entity.setFailureCode(TaskMybatisValueSupport.stringValue(attempt.get("failureCode")));
        entity.setFailureMessage(TaskMybatisValueSupport.stringValue(attempt.get("failureMessage")));
        entity.setPayloadJson(MybatisJsonSupport.write(attempt.get("payload")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为状态History实体。
     * @param taskId 任务标识
     * @param statusHistory 状态History值
     * @return 处理结果
     */
    TaskStatusHistoryEntity toStatusHistoryEntity(String taskId, Map<String, Object> statusHistory) {
        TaskStatusHistoryEntity entity = new TaskStatusHistoryEntity();
        entity.setTaskStatusHistoryId(TaskMybatisValueSupport.stringValue(statusHistory.get("statusHistoryId")));
        entity.setTaskId(taskId);
        entity.setPreviousStatus(TaskMybatisValueSupport.stringValue(statusHistory.get("previousStatus")));
        entity.setCurrentStatus(TaskMybatisValueSupport.stringValue(statusHistory.get("nextStatus")));
        entity.setProgress(TaskMybatisValueSupport.intValue(statusHistory.get("progress"), 0));
        entity.setStage(TaskMybatisValueSupport.stringValue(statusHistory.get("stage")));
        entity.setEvent(TaskMybatisValueSupport.stringValue(statusHistory.get("event")));
        entity.setMessage(TaskMybatisValueSupport.stringValue(statusHistory.get("reason")));
        entity.setPayloadJson(MybatisJsonSupport.write(statusHistory.get("payload")));
        entity.setChangeTime(TaskMybatisValueSupport.offsetValue(statusHistory.get("changedAt")));
        entity.setOperatorType(TaskMybatisValueSupport.stringValue(statusHistory.get("operator")));
        entity.setOperatorId("");
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为系统日志实体。
     * @param taskId 任务标识
     * @param trace 追踪值
     * @return 处理结果
     */
    SystemLogEntity toSystemLogEntity(String taskId, Map<String, Object> trace) {
        SystemLogEntity entity = new SystemLogEntity();
        entity.setSystemLogId(TaskMybatisValueSupport.stringValue(trace.getOrDefault("traceId", trace.get("systemLogId"))));
        entity.setTaskId(taskId);
        entity.setTraceId(TaskMybatisValueSupport.stringValue(trace.getOrDefault("traceId", entity.getSystemLogId())));
        entity.setModule("task");
        entity.setStage(TaskMybatisValueSupport.stringValue(trace.get("stage")));
        entity.setEvent(TaskMybatisValueSupport.stringValue(trace.get("event")));
        entity.setLevel(TaskMybatisValueSupport.stringValue(trace.get("level")));
        entity.setMessage(TaskMybatisValueSupport.stringValue(trace.get("message")));
        entity.setPayloadJson(MybatisJsonSupport.write(trace.get("payload")));
        entity.setSource("spring-api");
        entity.setServiceName("api-spring");
        entity.setHostName("");
        entity.setLoggedAt(TaskMybatisValueSupport.offsetValue(trace.get("timestamp")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为阶段运行实体。
     * @param taskId 任务标识
     * @param stageRun 阶段运行值
     * @return 处理结果
     */
    TaskStageRunEntity toStageRunEntity(String taskId, Map<String, Object> stageRun) {
        TaskStageRunEntity entity = new TaskStageRunEntity();
        entity.setTaskStageRunId(TaskMybatisValueSupport.stringValue(stageRun.get("stageRunId")));
        entity.setTaskId(taskId);
        entity.setAttemptId(TaskMybatisValueSupport.stringValue(stageRun.get("attemptId")));
        entity.setStageName(TaskMybatisValueSupport.stringValue(stageRun.get("stageName")));
        entity.setStageSeq(TaskMybatisValueSupport.intValue(stageRun.get("stageSeq"), 1));
        entity.setClipIndex(TaskMybatisValueSupport.intValue(stageRun.get("clipIndex"), 0));
        entity.setStatus(TaskMybatisValueSupport.stringValue(stageRun.get("status")));
        entity.setWorkerInstanceId(TaskMybatisValueSupport.stringValue(stageRun.get("workerInstanceId")));
        entity.setStartedAt(TaskMybatisValueSupport.offsetValue(stageRun.get("startedAt")));
        entity.setFinishedAt(TaskMybatisValueSupport.offsetValue(stageRun.get("finishedAt")));
        entity.setDurationMs(TaskMybatisValueSupport.intValue(stageRun.get("durationMs"), 0));
        entity.setInputSummaryJson(MybatisJsonSupport.write(stageRun.get("inputSummary")));
        entity.setOutputSummaryJson(MybatisJsonSupport.write(stageRun.get("outputSummary")));
        entity.setErrorCode(TaskMybatisValueSupport.stringValue(stageRun.get("errorCode")));
        entity.setErrorMessage(TaskMybatisValueSupport.stringValue(stageRun.get("errorMessage")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为任务队列事件实体。
     * @param taskId 任务标识
     * @param queueEvent 队列事件值
     * @return 处理结果
     */
    TaskQueueEventEntity toTaskQueueEventEntity(String taskId, Map<String, Object> queueEvent) {
        TaskQueueEventEntity entity = new TaskQueueEventEntity();
        entity.setTaskQueueEventId(TaskMybatisValueSupport.stringValue(queueEvent.get("taskQueueEventId")));
        entity.setTaskId(taskId);
        entity.setAttemptId(TaskMybatisValueSupport.stringValue(queueEvent.get("attemptId")));
        entity.setQueueName(TaskMybatisValueSupport.stringValue(queueEvent.getOrDefault("queueName", "default")));
        entity.setEventType(TaskMybatisValueSupport.stringValue(queueEvent.get("eventType")));
        entity.setWorkerInstanceId(TaskMybatisValueSupport.stringValue(queueEvent.get("workerInstanceId")));
        entity.setQueuePositionHint(TaskMybatisValueSupport.intValue(queueEvent.get("queuePositionHint"), 0));
        entity.setPayloadJson(MybatisJsonSupport.write(queueEvent.get("payload")));
        entity.setEventTime(TaskMybatisValueSupport.offsetValue(queueEvent.get("eventTime")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为工作节点Instance实体。
     * @param workerInstance 工作节点Instance值
     * @return 处理结果
     */
    WorkerInstanceEntity toWorkerInstanceEntity(Map<String, Object> workerInstance) {
        WorkerInstanceEntity entity = new WorkerInstanceEntity();
        entity.setWorkerInstanceId(TaskMybatisValueSupport.stringValue(workerInstance.get("workerInstanceId")));
        entity.setWorkerType(TaskMybatisValueSupport.stringValue(workerInstance.getOrDefault("workerType", "spring_queue_worker")));
        entity.setQueueName(TaskMybatisValueSupport.stringValue(workerInstance.getOrDefault("queueName", "default")));
        entity.setHostName(TaskMybatisValueSupport.stringValue(workerInstance.get("hostName")));
        entity.setProcessId(TaskMybatisValueSupport.intValue(workerInstance.get("processId"), 0));
        entity.setStatus(TaskMybatisValueSupport.stringValue(workerInstance.getOrDefault("status", "RUNNING")));
        entity.setStartedAt(TaskMybatisValueSupport.offsetValue(workerInstance.get("startedAt")));
        entity.setLastHeartbeatAt(TaskMybatisValueSupport.offsetValue(workerInstance.get("lastHeartbeatAt")));
        entity.setStoppedAt(TaskMybatisValueSupport.offsetValue(workerInstance.get("stoppedAt")));
        entity.setMetadataJson(MybatisJsonSupport.write(workerInstance.get("metadata")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为模型调用实体。
     * @param taskId 任务标识
     * @param modelCall 模型调用值
     * @return 处理结果
     */
    TaskModelCallEntity toModelCallEntity(String taskId, Map<String, Object> modelCall) {
        TaskModelCallEntity entity = new TaskModelCallEntity();
        entity.setTaskModelCallId(TaskMybatisValueSupport.stringValue(modelCall.get("modelCallId")));
        entity.setTaskId(taskId);
        entity.setCallKind(TaskMybatisValueSupport.stringValue(modelCall.get("callKind")));
        entity.setStage(TaskMybatisValueSupport.stringValue(modelCall.get("stage")));
        entity.setOperation(TaskMybatisValueSupport.stringValue(modelCall.get("operation")));
        entity.setProvider(TaskMybatisValueSupport.stringValue(modelCall.get("provider")));
        entity.setProviderModel(TaskMybatisValueSupport.stringValue(modelCall.get("providerModel")));
        entity.setRequestedModel(TaskMybatisValueSupport.stringValue(modelCall.get("requestedModel")));
        entity.setResolvedModel(TaskMybatisValueSupport.stringValue(modelCall.get("resolvedModel")));
        entity.setModelName(TaskMybatisValueSupport.stringValue(modelCall.get("modelName")));
        entity.setModelAlias(TaskMybatisValueSupport.stringValue(modelCall.get("modelAlias")));
        entity.setEndpointHost(TaskMybatisValueSupport.stringValue(modelCall.get("endpointHost")));
        entity.setRequestId(TaskMybatisValueSupport.stringValue(modelCall.get("requestId")));
        entity.setRequestPayloadJson(MybatisJsonSupport.write(modelCall.get("requestPayload")));
        entity.setResponsePayloadJson(MybatisJsonSupport.write(modelCall.get("responsePayload")));
        entity.setHttpStatus(TaskMybatisValueSupport.intValue(modelCall.get("httpStatus"), 0));
        entity.setResponseStatusCode(TaskMybatisValueSupport.intValue(
            modelCall.get("responseCode"),
            TaskMybatisValueSupport.intValue(modelCall.get("httpStatus"), 0)
        ));
        entity.setSuccess(TaskMybatisValueSupport.boolValue(modelCall.get("success")) ? 1 : 0);
        entity.setErrorCode(TaskMybatisValueSupport.stringValue(modelCall.get("errorCode")));
        entity.setErrorMessage(TaskMybatisValueSupport.stringValue(modelCall.get("errorMessage")));
        entity.setLatencyMs(TaskMybatisValueSupport.intValue(modelCall.get("latencyMs"), 0));
        entity.setDurationMs(TaskMybatisValueSupport.intValue(modelCall.get("latencyMs"), 0));
        entity.setInputTokens(TaskMybatisValueSupport.intValue(modelCall.get("inputTokens"), 0));
        entity.setOutputTokens(TaskMybatisValueSupport.intValue(modelCall.get("outputTokens"), 0));
        entity.setStartedAt(TaskMybatisValueSupport.offsetValue(modelCall.get("startedAt")));
        entity.setFinishedAt(TaskMybatisValueSupport.offsetValue(modelCall.get("finishedAt")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为素材素材实体。
     * @param taskId 任务标识
     * @param material 素材值
     * @return 处理结果
     */
    MaterialAssetEntity toMaterialAssetEntity(String taskId, Map<String, Object> material) {
        MaterialAssetEntity entity = new MaterialAssetEntity();
        entity.setMaterialAssetId(TaskMybatisValueSupport.stringValue(material.get("id")));
        entity.setTaskId(taskId);
        entity.setSourceTaskId(TaskMybatisValueSupport.stringValue(material.getOrDefault("sourceTaskId", "")));
        entity.setSourceMaterialId(TaskMybatisValueSupport.stringValue(material.getOrDefault("sourceMaterialId", "")));
        entity.setAssetRole(TaskMybatisValueSupport.stringValue(material.get("kind")));
        entity.setMediaType(TaskMybatisValueSupport.stringValue(material.get("mediaType")));
        entity.setTitle(TaskMybatisValueSupport.stringValue(material.get("title")));
        entity.setOriginProvider(TaskMybatisValueSupport.stringValue(material.get("originProvider")));
        entity.setOriginModel(TaskMybatisValueSupport.stringValue(material.get("originModel")));
        entity.setRemoteTaskId(TaskMybatisValueSupport.stringValue(material.get("remoteTaskId")));
        entity.setRemoteAssetId(TaskMybatisValueSupport.stringValue(material.get("remoteAssetId")));
        entity.setOriginalFileName(TaskMybatisValueSupport.stringValue(material.get("originalFileName")));
        entity.setStoredFileName(TaskMybatisValueSupport.stringValue(material.get("storedFileName")));
        entity.setFileExt(TaskMybatisValueSupport.stringValue(material.get("fileExt")));
        entity.setStorageProvider(TaskMybatisValueSupport.stringValue(material.getOrDefault("storageProvider", "local")));
        entity.setMimeType(TaskMybatisValueSupport.stringValue(material.get("mimeType")));
        entity.setSizeBytes(TaskMybatisValueSupport.longValue(material.get("sizeBytes"), 0L));
        entity.setSha256(TaskMybatisValueSupport.stringValue(material.get("sha256")));
        entity.setDurationSeconds(TaskMybatisValueSupport.doubleValue(material.get("durationSeconds"), 0.0));
        entity.setWidth(TaskMybatisValueSupport.intValue(material.get("width"), 0));
        entity.setHeight(TaskMybatisValueSupport.intValue(material.get("height"), 0));
        entity.setHasAudio(TaskMybatisValueSupport.boolValue(material.get("hasAudio")) ? 1 : 0);
        entity.setLocalStoragePath(TaskMybatisValueSupport.stringValue(material.get("storagePath")));
        entity.setLocalFilePath(TaskMybatisValueSupport.stringValue(material.get("localFilePath")));
        entity.setPublicUrl(TaskMybatisValueSupport.stringValue(material.get("fileUrl")));
        entity.setThirdPartyUrl(TaskMybatisValueSupport.stringValue(material.get("thirdPartyUrl")));
        entity.setRemoteUrl(TaskMybatisValueSupport.stringValue(material.get("remoteUrl")));
        entity.setMetadataJson(MybatisJsonSupport.write(material.get("metadata")));
        entity.setCapturedAt(TaskMybatisValueSupport.offsetValue(material.get("createdAt")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }

    /**
     * 处理转为结果实体。
     * @param taskId 任务标识
     * @param result 结果值
     * @return 处理结果
     */
    TaskResultEntity toResultEntity(String taskId, Map<String, Object> result) {
        TaskResultEntity entity = new TaskResultEntity();
        entity.setTaskResultId(TaskMybatisValueSupport.stringValue(result.get("id")));
        entity.setTaskId(taskId);
        entity.setResultType(TaskMybatisValueSupport.stringValue(result.getOrDefault("resultType", TaskResultTypes.VIDEO)));
        entity.setClipIndex(TaskMybatisValueSupport.intValue(result.get("clipIndex"), 0));
        entity.setTitle(TaskMybatisValueSupport.stringValue(result.get("title")));
        entity.setReason(TaskMybatisValueSupport.stringValue(result.get("reason")));
        entity.setSourceModelCallId(TaskMybatisValueSupport.stringValue(result.get("sourceModelCallId")));
        entity.setMaterialAssetId(TaskMybatisValueSupport.stringValue(result.get("materialAssetId")));
        entity.setStartSeconds(TaskMybatisValueSupport.doubleValue(result.get("startSeconds"), 0.0));
        entity.setEndSeconds(TaskMybatisValueSupport.doubleValue(result.get("endSeconds"), 0.0));
        entity.setDurationSeconds(TaskMybatisValueSupport.doubleValue(result.get("durationSeconds"), 0.0));
        entity.setPreviewPath(TaskMybatisValueSupport.stringValue(result.get("previewUrl")));
        entity.setDownloadPath(TaskMybatisValueSupport.stringValue(result.get("downloadUrl")));
        entity.setWidth(TaskMybatisValueSupport.intValue(result.get("width"), 0));
        entity.setHeight(TaskMybatisValueSupport.intValue(result.get("height"), 0));
        entity.setMimeType(TaskMybatisValueSupport.stringValue(result.get("mimeType")));
        entity.setSizeBytes(TaskMybatisValueSupport.longValue(result.get("sizeBytes"), 0L));
        entity.setRemoteUrl(TaskMybatisValueSupport.stringValue(result.get("remoteUrl")));
        entity.setExtraJson(MybatisJsonSupport.write(result.get("extra")));
        entity.setProducedAt(TaskMybatisValueSupport.offsetValue(result.get("createdAt")));
        entity.setTimezoneOffsetMinutes(DEFAULT_TIMEZONE_OFFSET_MINUTES);
        entity.setIsDeleted(0);
        return entity;
    }
}
