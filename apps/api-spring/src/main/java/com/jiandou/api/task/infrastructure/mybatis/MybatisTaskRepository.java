package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.task.TaskPersistenceMutation;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.TaskRecordAssembler;
import com.jiandou.api.task.TaskRepository;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.springframework.stereotype.Repository;

@Repository
public class MybatisTaskRepository implements TaskRepository {

    private final SqlSessionFactory sqlSessionFactory;
    private final TaskRecordAssembler taskRecordAssembler;
    private final TaskMybatisWriteMapper writeMapper;
    private final TaskMybatisReadMapper readMapper;

    public MybatisTaskRepository(
        SqlSessionFactory sqlSessionFactory,
        TaskRecordAssembler taskRecordAssembler
    ) {
        this.sqlSessionFactory = sqlSessionFactory;
        this.taskRecordAssembler = taskRecordAssembler;
        this.writeMapper = new TaskMybatisWriteMapper();
        this.readMapper = new TaskMybatisReadMapper();
    }

    @Override
    public void save(TaskRecord task) {
        TaskRecordAssembler.TaskWriteModel model = taskRecordAssembler.toWriteModel(task);
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            saveTask(session, task);
        }
    }

    @Override
    public void saveMutation(TaskPersistenceMutation mutation) {
        if (mutation == null) {
            return;
        }
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            try {
                TaskRecord task = mutation.task();
                String taskId = mutation.taskId();
                if ((taskId == null || taskId.isBlank()) && task != null) {
                    taskId = taskRecordAssembler.toWriteModel(task).taskId();
                }
                if ((taskId == null || taskId.isBlank()) && requiresTaskId(mutation)) {
                    throw new IllegalArgumentException("Task persistence mutation requires taskId for task-scoped rows.");
                }
                if (task != null) {
                    saveTask(session, task);
                }
                for (Map<String, Object> attempt : mutation.attempts()) {
                    saveAttempt(session, taskId, attempt);
                }
                for (Map<String, Object> statusHistory : mutation.statusHistoryRows()) {
                    saveStatusHistory(session, taskId, statusHistory);
                }
                for (Map<String, Object> trace : mutation.traceRows()) {
                    saveTrace(session, taskId, trace);
                }
                for (Map<String, Object> stageRun : mutation.stageRunRows()) {
                    saveStageRun(session, taskId, stageRun);
                }
                for (Map<String, Object> modelCall : mutation.modelCallRows()) {
                    saveModelCall(session, taskId, modelCall);
                }
                for (Map<String, Object> material : mutation.materialRows()) {
                    saveMaterial(session, taskId, material);
                }
                for (Map<String, Object> result : mutation.resultRows()) {
                    saveResult(session, taskId, result);
                }
                for (Map<String, Object> queueEvent : mutation.queueEventRows()) {
                    saveQueueEvent(session, taskId, queueEvent);
                }
                for (Map<String, Object> workerInstance : mutation.workerInstanceRows()) {
                    saveWorkerInstance(session, workerInstance);
                }
                session.commit();
            } catch (RuntimeException ex) {
                session.rollback();
                throw ex;
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
            return entity == null ? Map.of() : readMapper.toWorkerInstanceMap(entity);
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
            ).stream().map(readMapper::toWorkerInstanceMap).toList();
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
                .map(readMapper::toStaleRunningClaimMap)
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
            return mapper.selectList(query).stream().map(readMapper::toQueueEventMap).toList();
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
            return mapper.selectList(query).stream().map(readMapper::toTraceMap).toList();
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
            TaskRecord task = taskRecordAssembler.fromTaskRow(readMapper.toTaskRow(entity));
            readMapper.applyAttempts(task, taskAttemptMapper.selectList(
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
            ).stream().map(readMapper::toStatusHistoryRow).toList());
            readMapper.applyStageRuns(task, taskStageRunMapper.selectList(
                Wrappers.<TaskStageRunEntity>lambdaQuery()
                    .eq(TaskStageRunEntity::getTaskId, taskId)
                    .eq(TaskStageRunEntity::getIsDeleted, 0)
                    .orderByDesc(TaskStageRunEntity::getStartedAt)
            ));
            readMapper.applyModelCalls(task, taskModelCallMapper.selectList(
                Wrappers.<TaskModelCallEntity>lambdaQuery()
                    .eq(TaskModelCallEntity::getTaskId, taskId)
                    .eq(TaskModelCallEntity::getIsDeleted, 0)
                    .orderByAsc(TaskModelCallEntity::getStartedAt)
            ));
            readMapper.applyMaterials(task, materialAssetMapper.selectList(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(MaterialAssetEntity::getTaskId, taskId)
                    .eq(MaterialAssetEntity::getIsDeleted, 0)
                    .orderByAsc(MaterialAssetEntity::getCreateTime)
            ));
            readMapper.applyResults(task, taskResultMapper.selectList(
                Wrappers.<TaskResultEntity>lambdaQuery()
                    .eq(TaskResultEntity::getTaskId, taskId)
                    .eq(TaskResultEntity::getIsDeleted, 0)
                    .orderByAsc(TaskResultEntity::getClipIndex)
            ));
            readMapper.applyTrace(task, systemLogMapper.selectList(
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
            ).stream().map(readMapper::toTaskRow).map(taskRecordAssembler::fromTaskRow).toList();
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

    private void saveTask(SqlSession session, TaskRecord task) {
        TaskMapper mapper = session.getMapper(TaskMapper.class);
        TaskRecordAssembler.TaskWriteModel model = taskRecordAssembler.toWriteModel(task);
        TaskEntity entity = writeMapper.toTaskEntity(model);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskEntity>lambdaQuery()
                    .eq(TaskEntity::getTaskId, model.taskId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(entity, Wrappers.<TaskEntity>lambdaUpdate().eq(TaskEntity::getTaskId, model.taskId()))
        );
    }

    private void saveAttempt(SqlSession session, String taskId, Map<String, Object> attempt) {
        TaskAttemptMapper mapper = session.getMapper(TaskAttemptMapper.class);
        TaskAttemptEntity entity = writeMapper.toAttemptEntity(taskId, attempt);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskAttemptEntity>lambdaQuery()
                    .eq(TaskAttemptEntity::getTaskAttemptId, entity.getTaskAttemptId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<TaskAttemptEntity>lambdaUpdate()
                    .eq(TaskAttemptEntity::getTaskAttemptId, entity.getTaskAttemptId())
            )
        );
    }

    private void saveStatusHistory(SqlSession session, String taskId, Map<String, Object> statusHistory) {
        TaskStatusHistoryMapper mapper = session.getMapper(TaskStatusHistoryMapper.class);
        TaskStatusHistoryEntity entity = writeMapper.toStatusHistoryEntity(taskId, statusHistory);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskStatusHistoryEntity>lambdaQuery()
                    .eq(TaskStatusHistoryEntity::getTaskStatusHistoryId, entity.getTaskStatusHistoryId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<TaskStatusHistoryEntity>lambdaUpdate()
                    .eq(TaskStatusHistoryEntity::getTaskStatusHistoryId, entity.getTaskStatusHistoryId())
            )
        );
    }

    private void saveTrace(SqlSession session, String taskId, Map<String, Object> trace) {
        SystemLogMapper mapper = session.getMapper(SystemLogMapper.class);
        SystemLogEntity entity = writeMapper.toSystemLogEntity(taskId, trace);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<SystemLogEntity>lambdaQuery()
                    .eq(SystemLogEntity::getSystemLogId, entity.getSystemLogId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<SystemLogEntity>lambdaUpdate()
                    .eq(SystemLogEntity::getSystemLogId, entity.getSystemLogId())
            )
        );
    }

    private void saveStageRun(SqlSession session, String taskId, Map<String, Object> stageRun) {
        TaskStageRunMapper mapper = session.getMapper(TaskStageRunMapper.class);
        TaskStageRunEntity entity = writeMapper.toStageRunEntity(taskId, stageRun);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskStageRunEntity>lambdaQuery()
                    .eq(TaskStageRunEntity::getTaskStageRunId, entity.getTaskStageRunId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<TaskStageRunEntity>lambdaUpdate()
                    .eq(TaskStageRunEntity::getTaskStageRunId, entity.getTaskStageRunId())
            )
        );
    }

    private void saveModelCall(SqlSession session, String taskId, Map<String, Object> modelCall) {
        TaskModelCallMapper mapper = session.getMapper(TaskModelCallMapper.class);
        TaskModelCallEntity entity = writeMapper.toModelCallEntity(taskId, modelCall);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskModelCallEntity>lambdaQuery()
                    .eq(TaskModelCallEntity::getTaskModelCallId, entity.getTaskModelCallId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<TaskModelCallEntity>lambdaUpdate()
                    .eq(TaskModelCallEntity::getTaskModelCallId, entity.getTaskModelCallId())
            )
        );
    }

    private void saveMaterial(SqlSession session, String taskId, Map<String, Object> material) {
        MaterialAssetMapper mapper = session.getMapper(MaterialAssetMapper.class);
        MaterialAssetEntity entity = writeMapper.toMaterialAssetEntity(taskId, material);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(MaterialAssetEntity::getMaterialAssetId, entity.getMaterialAssetId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<MaterialAssetEntity>lambdaUpdate()
                    .eq(MaterialAssetEntity::getMaterialAssetId, entity.getMaterialAssetId())
            )
        );
    }

    private void saveResult(SqlSession session, String taskId, Map<String, Object> result) {
        TaskResultMapper mapper = session.getMapper(TaskResultMapper.class);
        TaskResultEntity entity = writeMapper.toResultEntity(taskId, result);
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
            return;
        }
        mapper.update(
            entity,
            Wrappers.<TaskResultEntity>lambdaUpdate()
                .eq(TaskResultEntity::getTaskId, taskId)
                .eq(TaskResultEntity::getClipIndex, entity.getClipIndex())
        );
    }

    private void saveQueueEvent(SqlSession session, String taskId, Map<String, Object> queueEvent) {
        TaskQueueEventMapper mapper = session.getMapper(TaskQueueEventMapper.class);
        TaskQueueEventEntity entity = writeMapper.toTaskQueueEventEntity(taskId, queueEvent);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<TaskQueueEventEntity>lambdaQuery()
                    .eq(TaskQueueEventEntity::getTaskQueueEventId, entity.getTaskQueueEventId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<TaskQueueEventEntity>lambdaUpdate()
                    .eq(TaskQueueEventEntity::getTaskQueueEventId, entity.getTaskQueueEventId())
            )
        );
    }

    private void saveWorkerInstance(SqlSession session, Map<String, Object> workerInstance) {
        WorkerInstanceMapper mapper = session.getMapper(WorkerInstanceMapper.class);
        WorkerInstanceEntity entity = writeMapper.toWorkerInstanceEntity(workerInstance);
        upsert(
            () -> mapper.selectOne(
                Wrappers.<WorkerInstanceEntity>lambdaQuery()
                    .eq(WorkerInstanceEntity::getWorkerInstanceId, entity.getWorkerInstanceId())
                    .last("LIMIT 1")
            ),
            () -> mapper.insert(entity),
            () -> mapper.update(
                entity,
                Wrappers.<WorkerInstanceEntity>lambdaUpdate()
                    .eq(WorkerInstanceEntity::getWorkerInstanceId, entity.getWorkerInstanceId())
            )
        );
    }

    private <T> void upsert(
        Supplier<T> existingSupplier,
        Runnable insertAction,
        Runnable updateAction
    ) {
        if (existingSupplier.get() == null) {
            insertAction.run();
        } else {
            updateAction.run();
        }
    }

    private boolean requiresTaskId(TaskPersistenceMutation mutation) {
        return !mutation.attempts().isEmpty()
            || !mutation.statusHistoryRows().isEmpty()
            || !mutation.traceRows().isEmpty()
            || !mutation.stageRunRows().isEmpty()
            || !mutation.modelCallRows().isEmpty()
            || !mutation.materialRows().isEmpty()
            || !mutation.resultRows().isEmpty()
            || !mutation.queueEventRows().isEmpty();
    }
}
