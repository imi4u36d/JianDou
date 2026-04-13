package com.jiandou.api.task.application;

import com.jiandou.api.task.TaskController;
import java.util.List;
import java.util.Map;

public interface TaskApplicationService {

    Map<String, Object> createGenerationTask(TaskController.CreateGenerationTaskRequest request);

    Map<String, Object> generateCreativePrompt(TaskController.GenerateCreativePromptRequest request);

    List<Map<String, Object>> listTasks(String q, String status, String platform, String sort);

    Map<String, Object> getTask(String taskId);

    List<Map<String, Object>> getTrace(String taskId, int limit);

    List<Map<String, Object>> getLogs(String taskId, int limit);

    List<Map<String, Object>> getStatusHistory(String taskId, int limit);

    List<Map<String, Object>> getModelCalls(String taskId, int limit);

    List<Map<String, Object>> getResults(String taskId);

    List<Map<String, Object>> getMaterials(String taskId);

    Map<String, Object> getSeedanceTaskResult(String remoteTaskId);

    Map<String, Object> retryTask(String taskId);

    Map<String, Object> pauseTask(String taskId);

    Map<String, Object> continueTask(String taskId);

    Map<String, Object> terminateTask(String taskId);

    Map<String, Object> rateTaskEffect(String taskId, TaskController.RateTaskEffectRequest request);

    Map<String, Object> deleteTask(String taskId);

    Map<String, Object> adminOverview();

    List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit);

    List<Map<String, Object>> adminWorkers(int limit);

    Map<String, Object> adminWorker(String workerInstanceId);

    List<Map<String, Object>> adminQueueEvents(String taskId, int limit);

    Map<String, Object> adminQueueOverview(int limit);

    Map<String, Object> adminTaskDiagnosis(String taskId);
}
