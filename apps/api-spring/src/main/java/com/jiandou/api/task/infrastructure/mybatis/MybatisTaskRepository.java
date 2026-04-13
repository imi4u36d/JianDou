package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.TaskRecordAssembler;
import com.jiandou.api.task.TaskRepository;
import com.jiandou.api.task.persistence.TaskRow;
import com.jiandou.api.task.persistence.TaskStatusHistoryRow;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.springframework.stereotype.Repository;

@Repository
public class MybatisTaskRepository implements TaskRepository {

    private final SqlSessionFactory sqlSessionFactory;
    private final TaskRecordAssembler taskRecordAssembler;

    public MybatisTaskRepository(
        SqlSessionFactory sqlSessionFactory,
        TaskRecordAssembler taskRecordAssembler
    ) {
        this.sqlSessionFactory = sqlSessionFactory;
        this.taskRecordAssembler = taskRecordAssembler;
    }

    @Override
    public void save(TaskRecord task) {
        TaskRecordAssembler.TaskWriteModel model = taskRecordAssembler.toWriteModel(task);
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskMapper taskMapper = session.getMapper(TaskMapper.class);
            TaskEntity entity = toTaskEntity(model);
            TaskEntity existing = taskMapper.selectOne(
                Wrappers.<TaskEntity>lambdaQuery()
                    .eq(TaskEntity::getTaskId, model.taskId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                taskMapper.insert(entity);
            } else {
                taskMapper.update(entity, Wrappers.<TaskEntity>lambdaUpdate().eq(TaskEntity::getTaskId, model.taskId()));
            }
        }
    }

    @Override
    public void saveAttempt(String taskId, Map<String, Object> attempt) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskAttemptMapper taskAttemptMapper = session.getMapper(TaskAttemptMapper.class);
            TaskAttemptEntity entity = toAttemptEntity(taskId, attempt);
            TaskAttemptEntity existing = taskAttemptMapper.selectOne(
                Wrappers.<TaskAttemptEntity>lambdaQuery()
                    .eq(TaskAttemptEntity::getTaskAttemptId, entity.getTaskAttemptId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                taskAttemptMapper.insert(entity);
            } else {
                taskAttemptMapper.update(entity, Wrappers.<TaskAttemptEntity>lambdaUpdate().eq(TaskAttemptEntity::getTaskAttemptId, entity.getTaskAttemptId()));
            }
        }
    }

    @Override
    public void saveStatusHistory(String taskId, Map<String, Object> statusHistory) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskStatusHistoryMapper taskStatusHistoryMapper = session.getMapper(TaskStatusHistoryMapper.class);
            TaskStatusHistoryEntity entity = toStatusHistoryEntity(taskId, statusHistory);
            TaskStatusHistoryEntity existing = taskStatusHistoryMapper.selectOne(
                Wrappers.<TaskStatusHistoryEntity>lambdaQuery()
                    .eq(TaskStatusHistoryEntity::getTaskStatusHistoryId, entity.getTaskStatusHistoryId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                taskStatusHistoryMapper.insert(entity);
            } else {
                taskStatusHistoryMapper.update(entity, Wrappers.<TaskStatusHistoryEntity>lambdaUpdate().eq(TaskStatusHistoryEntity::getTaskStatusHistoryId, entity.getTaskStatusHistoryId()));
            }
        }
    }

    @Override
    public void saveTrace(String taskId, Map<String, Object> trace) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            SystemLogMapper mapper = session.getMapper(SystemLogMapper.class);
            SystemLogEntity entity = toSystemLogEntity(taskId, trace);
            SystemLogEntity existing = mapper.selectOne(
                Wrappers.<SystemLogEntity>lambdaQuery()
                    .eq(SystemLogEntity::getSystemLogId, entity.getSystemLogId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<SystemLogEntity>lambdaUpdate().eq(SystemLogEntity::getSystemLogId, entity.getSystemLogId()));
            }
        }
    }

    @Override
    public void saveStageRun(String taskId, Map<String, Object> stageRun) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskStageRunMapper mapper = session.getMapper(TaskStageRunMapper.class);
            TaskStageRunEntity entity = toStageRunEntity(taskId, stageRun);
            TaskStageRunEntity existing = mapper.selectOne(
                Wrappers.<TaskStageRunEntity>lambdaQuery()
                    .eq(TaskStageRunEntity::getTaskStageRunId, entity.getTaskStageRunId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<TaskStageRunEntity>lambdaUpdate().eq(TaskStageRunEntity::getTaskStageRunId, entity.getTaskStageRunId()));
            }
        }
    }

    @Override
    public void saveModelCall(String taskId, Map<String, Object> modelCall) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskModelCallMapper mapper = session.getMapper(TaskModelCallMapper.class);
            TaskModelCallEntity entity = toModelCallEntity(taskId, modelCall);
            TaskModelCallEntity existing = mapper.selectOne(
                Wrappers.<TaskModelCallEntity>lambdaQuery()
                    .eq(TaskModelCallEntity::getTaskModelCallId, entity.getTaskModelCallId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<TaskModelCallEntity>lambdaUpdate().eq(TaskModelCallEntity::getTaskModelCallId, entity.getTaskModelCallId()));
            }
        }
    }

    @Override
    public void saveMaterial(String taskId, Map<String, Object> material) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            MaterialAssetMapper mapper = session.getMapper(MaterialAssetMapper.class);
            MaterialAssetEntity entity = toMaterialAssetEntity(taskId, material);
            MaterialAssetEntity existing = mapper.selectOne(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(MaterialAssetEntity::getMaterialAssetId, entity.getMaterialAssetId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<MaterialAssetEntity>lambdaUpdate().eq(MaterialAssetEntity::getMaterialAssetId, entity.getMaterialAssetId()));
            }
        }
    }

    @Override
    public void saveResult(String taskId, Map<String, Object> result) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskResultMapper mapper = session.getMapper(TaskResultMapper.class);
            TaskResultEntity entity = toResultEntity(taskId, result);
            TaskResultEntity existing = mapper.selectOne(
                Wrappers.<TaskResultEntity>lambdaQuery()
                    .eq(TaskResultEntity::getTaskResultId, entity.getTaskResultId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                existing = mapper.selectOne(
                    Wrappers.<TaskResultEntity>lambdaQuery()
                        .eq(TaskResultEntity::getTaskId, taskId)
                        .eq(TaskResultEntity::getClipIndex, entity.getClipIndex())
                        .eq(TaskResultEntity::getIsDeleted, 0)
                        .last("LIMIT 1")
                );
            }
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<TaskResultEntity>lambdaUpdate()
                    .eq(TaskResultEntity::getTaskId, taskId)
                    .eq(TaskResultEntity::getClipIndex, entity.getClipIndex()));
            }
        }
    }

    @Override
    public void saveQueueEvent(String taskId, Map<String, Object> queueEvent) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskQueueEventMapper mapper = session.getMapper(TaskQueueEventMapper.class);
            TaskQueueEventEntity entity = toTaskQueueEventEntity(taskId, queueEvent);
            TaskQueueEventEntity existing = mapper.selectOne(
                Wrappers.<TaskQueueEventEntity>lambdaQuery()
                    .eq(TaskQueueEventEntity::getTaskQueueEventId, entity.getTaskQueueEventId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<TaskQueueEventEntity>lambdaUpdate().eq(TaskQueueEventEntity::getTaskQueueEventId, entity.getTaskQueueEventId()));
            }
        }
    }

    @Override
    public void saveWorkerInstance(Map<String, Object> workerInstance) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            WorkerInstanceMapper mapper = session.getMapper(WorkerInstanceMapper.class);
            WorkerInstanceEntity entity = toWorkerInstanceEntity(workerInstance);
            WorkerInstanceEntity existing = mapper.selectOne(
                Wrappers.<WorkerInstanceEntity>lambdaQuery()
                    .eq(WorkerInstanceEntity::getWorkerInstanceId, entity.getWorkerInstanceId())
                    .last("LIMIT 1")
            );
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.update(entity, Wrappers.<WorkerInstanceEntity>lambdaUpdate().eq(WorkerInstanceEntity::getWorkerInstanceId, entity.getWorkerInstanceId()));
            }
        }
    }

    @Override
    public Map<String, Object> findWorkerInstance(String workerInstanceId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            WorkerInstanceMapper mapper = session.getMapper(WorkerInstanceMapper.class);
            WorkerInstanceEntity entity = mapper.selectOne(
                Wrappers.<WorkerInstanceEntity>lambdaQuery()
                    .eq(WorkerInstanceEntity::getWorkerInstanceId, workerInstanceId)
                    .eq(WorkerInstanceEntity::getIsDeleted, 0)
                    .last("LIMIT 1")
            );
            return entity == null ? Map.of() : toWorkerInstanceMap(entity);
        }
    }

    @Override
    public List<Map<String, Object>> listWorkerInstances(int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            WorkerInstanceMapper mapper = session.getMapper(WorkerInstanceMapper.class);
            return mapper.selectList(
                Wrappers.<WorkerInstanceEntity>lambdaQuery()
                    .eq(WorkerInstanceEntity::getIsDeleted, 0)
                    .orderByDesc(WorkerInstanceEntity::getLastHeartbeatAt)
                    .last("LIMIT " + Math.max(1, limit))
            ).stream().map(this::toWorkerInstanceMap).toList();
        }
    }

    @Override
    public void removeQueuedTask(String taskId) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskAttemptMapper mapper = session.getMapper(TaskAttemptMapper.class);
            mapper.removeQueuedAttempts(taskId, OffsetDateTime.now());
        }
    }

    @Override
    public String claimNextQueuedTask(String workerInstanceId) {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            TaskAttemptMapper mapper = session.getMapper(TaskAttemptMapper.class);
            List<QueueCandidateRow> candidates = mapper.selectQueueCandidates(20);
            OffsetDateTime now = OffsetDateTime.now();
            for (QueueCandidateRow candidate : candidates) {
                int updated = mapper.claimAttempt(candidate.taskAttemptId(), workerInstanceId, now);
                if (updated == 1) {
                    session.commit();
                    return candidate.taskId();
                }
            }
            session.rollback();
            return "";
        }
    }

    @Override
    public List<String> listQueuedTaskIds(int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            TaskAttemptMapper mapper = session.getMapper(TaskAttemptMapper.class);
            return mapper.selectQueuedTaskIds(Math.max(1, limit));
        }
    }

    @Override
    public List<Map<String, Object>> listStaleRunningClaims(OffsetDateTime staleBefore, int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            TaskAttemptMapper mapper = session.getMapper(TaskAttemptMapper.class);
            return mapper.selectStaleRunningTasks(staleBefore, Math.max(1, limit)).stream()
                .map(item -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("taskId", item.taskId());
                    row.put("workerInstanceId", item.workerInstanceId());
                    return row;
                })
                .toList();
        }
    }

    @Override
    public List<String> listStaleWorkerInstanceIds(OffsetDateTime staleBefore, int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            WorkerInstanceMapper mapper = session.getMapper(WorkerInstanceMapper.class);
            return mapper.selectStaleWorkerInstanceIds(staleBefore, Math.max(1, limit));
        }
    }

    @Override
    public List<Map<String, Object>> listQueueEvents(String taskId, int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            TaskQueueEventMapper mapper = session.getMapper(TaskQueueEventMapper.class);
            var query = Wrappers.<TaskQueueEventEntity>lambdaQuery()
                .eq(TaskQueueEventEntity::getIsDeleted, 0)
                .orderByDesc(TaskQueueEventEntity::getEventTime)
                .last("LIMIT " + Math.max(1, limit));
            if (taskId != null && !taskId.isBlank()) {
                query.eq(TaskQueueEventEntity::getTaskId, taskId);
            }
            return mapper.selectList(query).stream().map(this::toQueueEventMap).toList();
        }
    }

    @Override
    public List<Map<String, Object>> listTraces(String taskId, String stage, String level, String queryText, int limit) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            SystemLogMapper mapper = session.getMapper(SystemLogMapper.class);
            var query = Wrappers.<SystemLogEntity>lambdaQuery()
                .eq(SystemLogEntity::getIsDeleted, 0)
                .orderByDesc(SystemLogEntity::getLoggedAt)
                .last("LIMIT " + Math.max(1, limit));
            if (taskId != null && !taskId.isBlank()) {
                query.eq(SystemLogEntity::getTaskId, taskId);
            }
            if (stage != null && !stage.isBlank()) {
                query.eq(SystemLogEntity::getStage, stage);
            }
            if (level != null && !level.isBlank()) {
                query.eq(SystemLogEntity::getLevel, level.toUpperCase());
            }
            if (queryText != null && !queryText.isBlank()) {
                query.and(wrapper -> wrapper
                    .like(SystemLogEntity::getTaskId, queryText)
                    .or()
                    .like(SystemLogEntity::getTraceId, queryText)
                    .or()
                    .like(SystemLogEntity::getEvent, queryText)
                    .or()
                    .like(SystemLogEntity::getMessage, queryText));
            }
            return mapper.selectList(query).stream().map(this::toTraceMap).toList();
        }
    }

    @Override
    public TaskRecord findById(String taskId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            TaskMapper taskMapper = session.getMapper(TaskMapper.class);
            TaskAttemptMapper taskAttemptMapper = session.getMapper(TaskAttemptMapper.class);
            TaskStageRunMapper taskStageRunMapper = session.getMapper(TaskStageRunMapper.class);
            TaskStatusHistoryMapper taskStatusHistoryMapper = session.getMapper(TaskStatusHistoryMapper.class);
            TaskModelCallMapper taskModelCallMapper = session.getMapper(TaskModelCallMapper.class);
            TaskResultMapper taskResultMapper = session.getMapper(TaskResultMapper.class);
            MaterialAssetMapper materialAssetMapper = session.getMapper(MaterialAssetMapper.class);
            SystemLogMapper systemLogMapper = session.getMapper(SystemLogMapper.class);

            TaskEntity entity = taskMapper.selectOne(
                Wrappers.<TaskEntity>lambdaQuery()
                    .eq(TaskEntity::getTaskId, taskId)
                    .eq(TaskEntity::getIsDeleted, 0)
                    .last("LIMIT 1")
            );
            if (entity == null) {
                return null;
            }
            TaskRecord task = taskRecordAssembler.fromTaskRow(toTaskRow(entity));
            applyAttempts(task, taskAttemptMapper.selectList(
                Wrappers.<TaskAttemptEntity>lambdaQuery()
                    .eq(TaskAttemptEntity::getTaskId, taskId)
                    .eq(TaskAttemptEntity::getIsDeleted, 0)
                    .orderByDesc(TaskAttemptEntity::getAttemptNo)
            ));
            taskRecordAssembler.applyStatusHistory(task, taskStatusHistoryMapper.selectList(
                Wrappers.<TaskStatusHistoryEntity>lambdaQuery()
                    .eq(TaskStatusHistoryEntity::getTaskId, taskId)
                    .eq(TaskStatusHistoryEntity::getIsDeleted, 0)
                    .orderByDesc(TaskStatusHistoryEntity::getChangeTime)
            ).stream().map(this::toStatusHistoryRow).toList());
            applyStageRuns(task, taskStageRunMapper.selectList(
                Wrappers.<TaskStageRunEntity>lambdaQuery()
                    .eq(TaskStageRunEntity::getTaskId, taskId)
                    .eq(TaskStageRunEntity::getIsDeleted, 0)
                    .orderByDesc(TaskStageRunEntity::getStartedAt)
            ));
            applyModelCalls(task, taskModelCallMapper.selectList(
                Wrappers.<TaskModelCallEntity>lambdaQuery()
                    .eq(TaskModelCallEntity::getTaskId, taskId)
                    .eq(TaskModelCallEntity::getIsDeleted, 0)
                    .orderByAsc(TaskModelCallEntity::getStartedAt)
            ));
            applyMaterials(task, materialAssetMapper.selectList(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(MaterialAssetEntity::getTaskId, taskId)
                    .eq(MaterialAssetEntity::getIsDeleted, 0)
                    .orderByAsc(MaterialAssetEntity::getCreateTime)
            ));
            applyResults(task, taskResultMapper.selectList(
                Wrappers.<TaskResultEntity>lambdaQuery()
                    .eq(TaskResultEntity::getTaskId, taskId)
                    .eq(TaskResultEntity::getIsDeleted, 0)
                    .orderByAsc(TaskResultEntity::getClipIndex)
            ));
            applyTrace(task, systemLogMapper.selectList(
                Wrappers.<SystemLogEntity>lambdaQuery()
                    .eq(SystemLogEntity::getTaskId, taskId)
                    .eq(SystemLogEntity::getIsDeleted, 0)
                    .orderByAsc(SystemLogEntity::getLoggedAt)
            ));
            return task;
        }
    }

    @Override
    public Collection<TaskRecord> findAll() {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            TaskMapper taskMapper = session.getMapper(TaskMapper.class);
            return taskMapper.selectList(
                Wrappers.<TaskEntity>lambdaQuery()
                    .eq(TaskEntity::getIsDeleted, 0)
                    .orderByDesc(TaskEntity::getCreateTime)
            ).stream().map(this::toTaskRow).map(taskRecordAssembler::fromTaskRow).toList();
        }
    }

    @Override
    public void delete(String taskId) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            TaskMapper taskMapper = session.getMapper(TaskMapper.class);
            TaskEntity entity = new TaskEntity();
            entity.setIsDeleted(1);
            taskMapper.update(entity, Wrappers.<TaskEntity>lambdaUpdate().eq(TaskEntity::getTaskId, taskId));
        }
    }

    private TaskEntity toTaskEntity(TaskRecordAssembler.TaskWriteModel model) {
        TaskEntity entity = new TaskEntity();
        entity.setTaskId(model.taskId());
        entity.setTaskType("generation");
        entity.setTitle(model.title());
        entity.setDescription("");
        entity.setPlatform(model.platform());
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
        entity.setExecutionMode("queue");
        entity.setEditingMode(model.editingMode());
        entity.setStatus(model.status());
        entity.setProgress(model.progress());
        entity.setErrorCode("");
        entity.setErrorMessage(model.errorMessage());
        entity.setPlanJson("");
        entity.setRetryCount(model.retryCount());
        entity.setTimezoneOffsetMinutes(480);
        entity.setStartedAt(model.startedAt());
        entity.setFinishedAt(model.finishedAt());
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskAttemptEntity toAttemptEntity(String taskId, Map<String, Object> attempt) {
        TaskAttemptEntity entity = new TaskAttemptEntity();
        entity.setTaskAttemptId(stringValue(attempt.get("attemptId")));
        entity.setTaskId(taskId);
        entity.setAttemptNo(intValue(attempt.get("attemptNo"), 1));
        entity.setTriggerType(stringValue(attempt.get("triggerType")));
        entity.setStatus(stringValue(attempt.get("status")));
        entity.setQueueName(stringValue(attempt.get("queueName")));
        entity.setWorkerInstanceId(stringValue(attempt.get("workerInstanceId")));
        entity.setQueueEnteredAt(offsetValue(attempt.get("queueEnteredAt")));
        entity.setQueueLeftAt(offsetValue(attempt.get("queueLeftAt")));
        entity.setClaimedAt(offsetValue(attempt.get("claimedAt")));
        entity.setStartedAt(offsetValue(attempt.get("startedAt")));
        entity.setFinishedAt(offsetValue(attempt.get("finishedAt")));
        entity.setResumeFromStage(stringValue(attempt.get("resumeFromStage")));
        entity.setResumeFromClipIndex(intValue(attempt.get("resumeFromClipIndex"), 0));
        entity.setFailureCode(stringValue(attempt.get("failureCode")));
        entity.setFailureMessage(stringValue(attempt.get("failureMessage")));
        entity.setPayloadJson(MybatisJsonSupport.write(attempt.get("payload")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskStatusHistoryEntity toStatusHistoryEntity(String taskId, Map<String, Object> statusHistory) {
        TaskStatusHistoryEntity entity = new TaskStatusHistoryEntity();
        entity.setTaskStatusHistoryId(stringValue(statusHistory.get("statusHistoryId")));
        entity.setTaskId(taskId);
        entity.setPreviousStatus(stringValue(statusHistory.get("previousStatus")));
        entity.setCurrentStatus(stringValue(statusHistory.get("nextStatus")));
        entity.setProgress(intValue(statusHistory.get("progress"), 0));
        entity.setStage(stringValue(statusHistory.get("stage")));
        entity.setEvent(stringValue(statusHistory.get("event")));
        entity.setMessage(stringValue(statusHistory.get("reason")));
        entity.setPayloadJson(MybatisJsonSupport.write(statusHistory.get("payload")));
        entity.setChangeTime(offsetValue(statusHistory.get("changedAt")));
        entity.setOperatorType(stringValue(statusHistory.get("operator")));
        entity.setOperatorId("");
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private SystemLogEntity toSystemLogEntity(String taskId, Map<String, Object> trace) {
        SystemLogEntity entity = new SystemLogEntity();
        entity.setSystemLogId(stringValue(trace.getOrDefault("traceId", trace.get("systemLogId"))));
        entity.setTaskId(taskId);
        entity.setTraceId(stringValue(trace.getOrDefault("traceId", entity.getSystemLogId())));
        entity.setModule("task");
        entity.setStage(stringValue(trace.get("stage")));
        entity.setEvent(stringValue(trace.get("event")));
        entity.setLevel(stringValue(trace.get("level")));
        entity.setMessage(stringValue(trace.get("message")));
        entity.setPayloadJson(MybatisJsonSupport.write(trace.get("payload")));
        entity.setSource("spring-api");
        entity.setServiceName("api-spring");
        entity.setHostName("");
        entity.setLoggedAt(offsetValue(trace.get("timestamp")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskStageRunEntity toStageRunEntity(String taskId, Map<String, Object> stageRun) {
        TaskStageRunEntity entity = new TaskStageRunEntity();
        entity.setTaskStageRunId(stringValue(stageRun.get("stageRunId")));
        entity.setTaskId(taskId);
        entity.setAttemptId(stringValue(stageRun.get("attemptId")));
        entity.setStageName(stringValue(stageRun.get("stageName")));
        entity.setStageSeq(intValue(stageRun.get("stageSeq"), 1));
        entity.setClipIndex(intValue(stageRun.get("clipIndex"), 0));
        entity.setStatus(stringValue(stageRun.get("status")));
        entity.setWorkerInstanceId(stringValue(stageRun.get("workerInstanceId")));
        entity.setStartedAt(offsetValue(stageRun.get("startedAt")));
        entity.setFinishedAt(offsetValue(stageRun.get("finishedAt")));
        entity.setDurationMs(intValue(stageRun.get("durationMs"), 0));
        entity.setInputSummaryJson(MybatisJsonSupport.write(stageRun.get("inputSummary")));
        entity.setOutputSummaryJson(MybatisJsonSupport.write(stageRun.get("outputSummary")));
        entity.setErrorCode(stringValue(stageRun.get("errorCode")));
        entity.setErrorMessage(stringValue(stageRun.get("errorMessage")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskQueueEventEntity toTaskQueueEventEntity(String taskId, Map<String, Object> queueEvent) {
        TaskQueueEventEntity entity = new TaskQueueEventEntity();
        entity.setTaskQueueEventId(stringValue(queueEvent.get("taskQueueEventId")));
        entity.setTaskId(taskId);
        entity.setAttemptId(stringValue(queueEvent.get("attemptId")));
        entity.setQueueName(stringValue(queueEvent.getOrDefault("queueName", "default")));
        entity.setEventType(stringValue(queueEvent.get("eventType")));
        entity.setWorkerInstanceId(stringValue(queueEvent.get("workerInstanceId")));
        entity.setQueuePositionHint(intValue(queueEvent.get("queuePositionHint"), 0));
        entity.setPayloadJson(MybatisJsonSupport.write(queueEvent.get("payload")));
        entity.setEventTime(offsetValue(queueEvent.get("eventTime")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private WorkerInstanceEntity toWorkerInstanceEntity(Map<String, Object> workerInstance) {
        WorkerInstanceEntity entity = new WorkerInstanceEntity();
        entity.setWorkerInstanceId(stringValue(workerInstance.get("workerInstanceId")));
        entity.setWorkerType(stringValue(workerInstance.getOrDefault("workerType", "spring_queue_worker")));
        entity.setQueueName(stringValue(workerInstance.getOrDefault("queueName", "default")));
        entity.setHostName(stringValue(workerInstance.get("hostName")));
        entity.setProcessId(intValue(workerInstance.get("processId"), 0));
        entity.setStatus(stringValue(workerInstance.getOrDefault("status", "RUNNING")));
        entity.setStartedAt(offsetValue(workerInstance.get("startedAt")));
        entity.setLastHeartbeatAt(offsetValue(workerInstance.get("lastHeartbeatAt")));
        entity.setStoppedAt(offsetValue(workerInstance.get("stoppedAt")));
        entity.setMetadataJson(MybatisJsonSupport.write(workerInstance.get("metadata")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskModelCallEntity toModelCallEntity(String taskId, Map<String, Object> modelCall) {
        TaskModelCallEntity entity = new TaskModelCallEntity();
        entity.setTaskModelCallId(stringValue(modelCall.get("modelCallId")));
        entity.setTaskId(taskId);
        entity.setCallKind(stringValue(modelCall.get("callKind")));
        entity.setStage(stringValue(modelCall.get("stage")));
        entity.setOperation(stringValue(modelCall.get("operation")));
        entity.setProvider(stringValue(modelCall.get("provider")));
        entity.setProviderModel(stringValue(modelCall.get("providerModel")));
        entity.setRequestedModel(stringValue(modelCall.get("requestedModel")));
        entity.setResolvedModel(stringValue(modelCall.get("resolvedModel")));
        entity.setModelName(stringValue(modelCall.get("modelName")));
        entity.setModelAlias(stringValue(modelCall.get("modelAlias")));
        entity.setEndpointHost(stringValue(modelCall.get("endpointHost")));
        entity.setRequestId(stringValue(modelCall.get("requestId")));
        entity.setRequestPayloadJson(MybatisJsonSupport.write(modelCall.get("requestPayload")));
        entity.setResponsePayloadJson(MybatisJsonSupport.write(modelCall.get("responsePayload")));
        entity.setHttpStatus(intValue(modelCall.get("httpStatus"), 0));
        entity.setResponseStatusCode(intValue(modelCall.get("responseCode"), intValue(modelCall.get("httpStatus"), 0)));
        entity.setSuccess(boolValue(modelCall.get("success")) ? 1 : 0);
        entity.setErrorCode(stringValue(modelCall.get("errorCode")));
        entity.setErrorMessage(stringValue(modelCall.get("errorMessage")));
        entity.setLatencyMs(intValue(modelCall.get("latencyMs"), 0));
        entity.setDurationMs(intValue(modelCall.get("latencyMs"), 0));
        entity.setInputTokens(intValue(modelCall.get("inputTokens"), 0));
        entity.setOutputTokens(intValue(modelCall.get("outputTokens"), 0));
        entity.setStartedAt(offsetValue(modelCall.get("startedAt")));
        entity.setFinishedAt(offsetValue(modelCall.get("finishedAt")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private MaterialAssetEntity toMaterialAssetEntity(String taskId, Map<String, Object> material) {
        MaterialAssetEntity entity = new MaterialAssetEntity();
        entity.setMaterialAssetId(stringValue(material.get("id")));
        entity.setTaskId(taskId);
        entity.setSourceTaskId(stringValue(material.getOrDefault("sourceTaskId", "")));
        entity.setSourceMaterialId(stringValue(material.getOrDefault("sourceMaterialId", "")));
        entity.setAssetRole(stringValue(material.get("kind")));
        entity.setMediaType(stringValue(material.get("mediaType")));
        entity.setTitle(stringValue(material.get("title")));
        entity.setOriginProvider(stringValue(material.get("originProvider")));
        entity.setOriginModel(stringValue(material.get("originModel")));
        entity.setRemoteTaskId(stringValue(material.get("remoteTaskId")));
        entity.setRemoteAssetId(stringValue(material.get("remoteAssetId")));
        entity.setOriginalFileName(stringValue(material.get("originalFileName")));
        entity.setStoredFileName(stringValue(material.get("storedFileName")));
        entity.setFileExt(stringValue(material.get("fileExt")));
        entity.setStorageProvider(stringValue(material.getOrDefault("storageProvider", "local")));
        entity.setMimeType(stringValue(material.get("mimeType")));
        entity.setSizeBytes(longValue(material.get("sizeBytes"), 0L));
        entity.setSha256(stringValue(material.get("sha256")));
        entity.setDurationSeconds(doubleValue(material.get("durationSeconds"), 0.0));
        entity.setWidth(intValue(material.get("width"), 0));
        entity.setHeight(intValue(material.get("height"), 0));
        entity.setHasAudio(boolValue(material.get("hasAudio")) ? 1 : 0);
        entity.setLocalStoragePath(stringValue(material.get("storagePath")));
        entity.setLocalFilePath(stringValue(material.get("localFilePath")));
        entity.setPublicUrl(stringValue(material.get("fileUrl")));
        entity.setThirdPartyUrl(stringValue(material.get("thirdPartyUrl")));
        entity.setRemoteUrl(stringValue(material.get("remoteUrl")));
        entity.setMetadataJson(MybatisJsonSupport.write(material.get("metadata")));
        entity.setCapturedAt(offsetValue(material.get("createdAt")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskResultEntity toResultEntity(String taskId, Map<String, Object> result) {
        TaskResultEntity entity = new TaskResultEntity();
        entity.setTaskResultId(stringValue(result.get("id")));
        entity.setTaskId(taskId);
        entity.setResultType(stringValue(result.getOrDefault("resultType", "video")));
        entity.setClipIndex(intValue(result.get("clipIndex"), 0));
        entity.setTitle(stringValue(result.get("title")));
        entity.setReason(stringValue(result.get("reason")));
        entity.setSourceModelCallId(stringValue(result.get("sourceModelCallId")));
        entity.setMaterialAssetId(stringValue(result.get("materialAssetId")));
        entity.setStartSeconds(doubleValue(result.get("startSeconds"), 0.0));
        entity.setEndSeconds(doubleValue(result.get("endSeconds"), 0.0));
        entity.setDurationSeconds(doubleValue(result.get("durationSeconds"), 0.0));
        entity.setPreviewPath(stringValue(result.get("previewUrl")));
        entity.setDownloadPath(stringValue(result.get("downloadUrl")));
        entity.setWidth(intValue(result.get("width"), 0));
        entity.setHeight(intValue(result.get("height"), 0));
        entity.setMimeType(stringValue(result.get("mimeType")));
        entity.setSizeBytes(longValue(result.get("sizeBytes"), 0L));
        entity.setRemoteUrl(stringValue(result.get("remoteUrl")));
        entity.setExtraJson(MybatisJsonSupport.write(result.get("extra")));
        entity.setProducedAt(offsetValue(result.get("createdAt")));
        entity.setTimezoneOffsetMinutes(480);
        entity.setIsDeleted(0);
        return entity;
    }

    private TaskRow toTaskRow(TaskEntity entity) {
        return new TaskRow(
            entity.getTaskId(),
            entity.getTaskType(),
            entity.getTitle(),
            entity.getDescription(),
            entity.getPlatform(),
            entity.getAspectRatio(),
            defaultInt(entity.getMinDurationSeconds()),
            defaultInt(entity.getMaxDurationSeconds()),
            defaultInt(entity.getOutputCount()),
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
            defaultInt(entity.getProgress()),
            entity.getErrorCode(),
            entity.getErrorMessage(),
            entity.getPlanJson(),
            defaultInt(entity.getRetryCount()),
            defaultInt(entity.getTimezoneOffsetMinutes()),
            entity.getStartedAt(),
            entity.getFinishedAt(),
            entity.getCreateTime(),
            entity.getUpdateTime()
        );
    }

    private Map<String, Object> toQueueEventMap(TaskQueueEventEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskQueueEventId", entity.getTaskQueueEventId());
        row.put("taskId", entity.getTaskId());
        row.put("attemptId", entity.getAttemptId());
        row.put("queueName", entity.getQueueName());
        row.put("eventType", entity.getEventType());
        row.put("workerInstanceId", entity.getWorkerInstanceId());
        row.put("queuePositionHint", defaultInt(entity.getQueuePositionHint()));
        row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
        row.put("eventTime", format(entity.getEventTime()));
        row.put("createdAt", format(entity.getCreateTime()));
        return row;
    }

    private Map<String, Object> toWorkerInstanceMap(WorkerInstanceEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("workerInstanceId", entity.getWorkerInstanceId());
        row.put("workerType", entity.getWorkerType());
        row.put("queueName", entity.getQueueName());
        row.put("hostName", entity.getHostName());
        row.put("processId", defaultInt(entity.getProcessId()));
        row.put("status", entity.getStatus());
        row.put("startedAt", format(entity.getStartedAt()));
        row.put("lastHeartbeatAt", format(entity.getLastHeartbeatAt()));
        row.put("stoppedAt", format(entity.getStoppedAt()));
        row.put("metadata", MybatisJsonSupport.readMap(entity.getMetadataJson()));
        row.put("createdAt", format(entity.getCreateTime()));
        row.put("updatedAt", format(entity.getUpdateTime()));
        return row;
    }

    private Map<String, Object> toTraceMap(SystemLogEntity entity) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("traceId", entity.getTraceId());
        row.put("taskId", entity.getTaskId());
        row.put("timestamp", format(entity.getLoggedAt()));
        row.put("level", entity.getLevel());
        row.put("stage", entity.getStage());
        row.put("event", entity.getEvent());
        row.put("message", entity.getMessage());
        row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
        row.put("source", entity.getSource());
        row.put("serviceName", entity.getServiceName());
        row.put("createdAt", format(entity.getCreateTime()));
        return row;
    }

    private TaskStatusHistoryRow toStatusHistoryRow(TaskStatusHistoryEntity entity) {
        return new TaskStatusHistoryRow(
            entity.getTaskStatusHistoryId(),
            entity.getTaskId(),
            entity.getPreviousStatus(),
            entity.getCurrentStatus(),
            defaultInt(entity.getProgress()),
            entity.getStage(),
            entity.getEvent(),
            entity.getMessage(),
            MybatisJsonSupport.readMap(entity.getPayloadJson()),
            entity.getChangeTime(),
            entity.getOperatorType(),
            entity.getOperatorId(),
            defaultInt(entity.getTimezoneOffsetMinutes()),
            entity.getCreateTime(),
            entity.getUpdateTime()
        );
    }

    private void applyAttempts(TaskRecord task, List<TaskAttemptEntity> entities) {
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
            row.put("queueEnteredAt", format(entity.getQueueEnteredAt()));
            row.put("queueLeftAt", format(entity.getQueueLeftAt()));
            row.put("claimedAt", format(entity.getClaimedAt()));
            row.put("startedAt", format(entity.getStartedAt()));
            row.put("finishedAt", format(entity.getFinishedAt()));
            row.put("resumeFromStage", entity.getResumeFromStage());
            row.put("resumeFromClipIndex", defaultInt(entity.getResumeFromClipIndex()));
            row.put("failureCode", entity.getFailureCode());
            row.put("failureMessage", entity.getFailureMessage());
            row.put("payload", MybatisJsonSupport.readMap(entity.getPayloadJson()));
            task.attemptsView().add(row);
        }
        if (!entities.isEmpty()) {
            TaskAttemptEntity active = entities.get(0);
            task.setActiveAttempt(active.getTaskAttemptId(), defaultInt(active.getAttemptNo()));
        }
    }

    private void applyStageRuns(TaskRecord task, List<TaskStageRunEntity> entities) {
        task.stageRunsView().clear();
        for (TaskStageRunEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("stageRunId", entity.getTaskStageRunId());
            row.put("taskId", entity.getTaskId());
            row.put("attemptId", entity.getAttemptId());
            row.put("stageName", entity.getStageName());
            row.put("stageSeq", defaultInt(entity.getStageSeq()));
            row.put("clipIndex", defaultInt(entity.getClipIndex()));
            row.put("status", entity.getStatus());
            row.put("workerInstanceId", entity.getWorkerInstanceId());
            row.put("startedAt", format(entity.getStartedAt()));
            row.put("finishedAt", format(entity.getFinishedAt()));
            row.put("durationMs", defaultInt(entity.getDurationMs()));
            row.put("inputSummary", MybatisJsonSupport.readMap(entity.getInputSummaryJson()));
            row.put("outputSummary", MybatisJsonSupport.readMap(entity.getOutputSummaryJson()));
            row.put("errorCode", entity.getErrorCode());
            row.put("errorMessage", entity.getErrorMessage());
            task.stageRunsView().add(row);
        }
    }

    private void applyModelCalls(TaskRecord task, List<TaskModelCallEntity> entities) {
        task.modelCallsView().clear();
        for (TaskModelCallEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("modelCallId", entity.getTaskModelCallId());
            row.put("taskId", entity.getTaskId());
            row.put("provider", entity.getProvider());
            row.put("modelName", stringValue(entity.getModelName().isBlank() ? entity.getModelAlias() : entity.getModelName()));
            row.put("operationKind", entity.getOperation());
            row.put("status", defaultInt(entity.getSuccess()) == 1 ? "success" : "failed");
            row.put("latencyMs", defaultInt(entity.getLatencyMs()));
            row.put("requestPayload", MybatisJsonSupport.readMap(entity.getRequestPayloadJson()));
            row.put("responsePayload", MybatisJsonSupport.readMap(entity.getResponsePayloadJson()));
            row.put("responseCode", defaultInt(entity.getResponseStatusCode()));
            row.put("errorCode", entity.getErrorCode());
            row.put("errorMessage", entity.getErrorMessage());
            row.put("startedAt", format(entity.getStartedAt()));
            row.put("finishedAt", format(entity.getFinishedAt()));
            row.put("createdAt", format(entity.getCreateTime()));
            task.modelCallsView().add(row);
        }
    }

    private void applyMaterials(TaskRecord task, List<MaterialAssetEntity> entities) {
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
            row.put("durationSeconds", defaultDouble(entity.getDurationSeconds()));
            row.put("width", defaultInt(entity.getWidth()));
            row.put("height", defaultInt(entity.getHeight()));
            row.put("hasAudio", defaultInt(entity.getHasAudio()) == 1);
            row.put("sizeBytes", defaultLong(entity.getSizeBytes()));
            row.put("createdAt", format(entity.getCreateTime()));
            row.put("storagePath", entity.getLocalStoragePath());
            row.put("localFilePath", entity.getLocalFilePath());
            row.put("remoteUrl", entity.getRemoteUrl());
            row.put("thirdPartyUrl", entity.getThirdPartyUrl());
            row.put("metadata", MybatisJsonSupport.readMap(entity.getMetadataJson()));
            task.materialsView().add(row);
        }
    }

    private void applyResults(TaskRecord task, List<TaskResultEntity> entities) {
        task.outputsView().clear();
        for (TaskResultEntity entity : entities) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", entity.getTaskResultId());
            row.put("resultType", entity.getResultType());
            row.put("clipIndex", defaultInt(entity.getClipIndex()));
            row.put("title", entity.getTitle());
            row.put("reason", entity.getReason());
            row.put("sourceModelCallId", entity.getSourceModelCallId());
            row.put("startSeconds", defaultDouble(entity.getStartSeconds()));
            row.put("endSeconds", defaultDouble(entity.getEndSeconds()));
            row.put("durationSeconds", defaultDouble(entity.getDurationSeconds()));
            row.put("previewUrl", entity.getPreviewPath());
            row.put("downloadUrl", entity.getDownloadPath());
            row.put("mimeType", entity.getMimeType());
            row.put("width", defaultInt(entity.getWidth()));
            row.put("height", defaultInt(entity.getHeight()));
            row.put("sizeBytes", defaultLong(entity.getSizeBytes()));
            row.put("materialAssetId", entity.getMaterialAssetId());
            row.put("remoteUrl", entity.getRemoteUrl());
            row.put("extra", MybatisJsonSupport.readMap(entity.getExtraJson()));
            row.put("createdAt", format(entity.getCreateTime()));
            task.outputsView().add(row);
        }
    }

    private void applyTrace(TaskRecord task, List<SystemLogEntity> entities) {
        task.traceView().clear();
        for (SystemLogEntity entity : entities) {
            task.traceView().add(toTraceMap(entity));
        }
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private int intValue(Object value, int fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Integer.parseInt(text);
    }

    private int defaultInt(Integer value) {
        return value == null ? 0 : value;
    }

    private String format(OffsetDateTime value) {
        return value == null ? null : value.toString();
    }

    private long defaultLong(Long value) {
        return value == null ? 0L : value;
    }

    private double defaultDouble(Double value) {
        return value == null ? 0.0 : value;
    }

    private OffsetDateTime offsetValue(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return null;
        }
        return OffsetDateTime.parse(text);
    }

    private boolean boolValue(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        String text = String.valueOf(value).trim();
        return "true".equalsIgnoreCase(text) || "1".equals(text) || "yes".equalsIgnoreCase(text);
    }

    private long longValue(Object value, long fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.longValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Long.parseLong(text);
    }

    private double doubleValue(Object value, double fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Double.parseDouble(text);
    }
}
