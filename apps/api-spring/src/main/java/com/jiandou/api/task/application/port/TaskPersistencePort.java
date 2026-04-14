package com.jiandou.api.task.application.port;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.TaskPersistenceMutation;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Map;

public interface TaskPersistencePort {

    void save(TaskRecord task);

    void saveMutation(TaskPersistenceMutation mutation);

    void saveAttempt(String taskId, Map<String, Object> attempt);

    void saveStatusHistory(String taskId, Map<String, Object> statusHistory);

    void saveTrace(String taskId, Map<String, Object> trace);

    void saveStageRun(String taskId, Map<String, Object> stageRun);

    void saveModelCall(String taskId, Map<String, Object> modelCall);

    void saveMaterial(String taskId, Map<String, Object> material);

    void saveResult(String taskId, Map<String, Object> result);

    void saveQueueEvent(String taskId, Map<String, Object> queueEvent);

    void saveWorkerInstance(Map<String, Object> workerInstance);

    Map<String, Object> findWorkerInstance(String workerInstanceId);

    List<Map<String, Object>> listWorkerInstances(int limit);

    void removeQueuedTask(String taskId);

    String claimNextQueuedTask(String workerInstanceId);

    List<String> listQueuedTaskIds(int limit);

    List<Map<String, Object>> listStaleRunningClaims(OffsetDateTime staleBefore, int limit);

    List<String> listStaleWorkerInstanceIds(OffsetDateTime staleBefore, int limit);

    List<Map<String, Object>> listQueueEvents(String taskId, int limit);

    List<Map<String, Object>> listTraces(String taskId, String stage, String level, String query, int limit);

    TaskRecord findById(String taskId);

    Collection<TaskRecord> findAll();

    void delete(String taskId);
}
