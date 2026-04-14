package com.jiandou.api.task;

import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.RemoteMediaGenerationClient;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/**
 * 任务模块的应用服务实现。
 * 当前类只保留用例级编排，把状态变更和诊断等重逻辑下沉到专门协作者。
 */
@Service
public class TaskApplicationServiceImpl implements TaskApplicationService {

    private final TaskQueryService taskQueryService;
    private final TaskCommandService taskCommandService;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final RemoteMediaGenerationClient remoteMediaGenerationClient;

    public TaskApplicationServiceImpl(
        TaskQueryService taskQueryService,
        TaskCommandService taskCommandService,
        ModelRuntimePropertiesResolver modelResolver,
        RemoteMediaGenerationClient remoteMediaGenerationClient
    ) {
        this.taskQueryService = taskQueryService;
        this.taskCommandService = taskCommandService;
        this.modelResolver = modelResolver;
        this.remoteMediaGenerationClient = remoteMediaGenerationClient;
    }

    @Override
    public Map<String, Object> createGenerationTask(CreateGenerationTaskRequest request) {
        return taskQueryService.getTask(taskCommandService.createGenerationTask(request).id);
    }

    @Override
    public Map<String, Object> generateCreativePrompt(GenerateCreativePromptRequest request) {
        String title = trimmed(request.title(), "未命名任务");
        String prompt = "短剧风格，情绪递进，人物表情贴合语境，镜头写实，台词和配音语气符合剧情：" + title;
        return Map.of(
            "prompt", prompt,
            "source", "spring-default"
        );
    }

    @Override
    public List<Map<String, Object>> listTasks(String q, String status, String sort) {
        return taskQueryService.listTasks(q, status, sort);
    }

    @Override
    public Map<String, Object> getTask(String taskId) {
        return taskQueryService.getTask(taskId);
    }

    @Override
    public List<Map<String, Object>> getTrace(String taskId, int limit) {
        return taskQueryService.getTrace(taskId, limit);
    }

    @Override
    public List<Map<String, Object>> getLogs(String taskId, int limit) {
        return taskQueryService.getLogs(taskId, limit);
    }

    @Override
    public List<Map<String, Object>> getStatusHistory(String taskId, int limit) {
        return taskQueryService.getStatusHistory(taskId, limit);
    }

    @Override
    public List<Map<String, Object>> getModelCalls(String taskId, int limit) {
        return taskQueryService.getModelCalls(taskId, limit);
    }

    @Override
    public List<Map<String, Object>> getResults(String taskId) {
        return taskQueryService.getResults(taskId);
    }

    @Override
    public List<Map<String, Object>> getMaterials(String taskId) {
        return taskQueryService.getMaterials(taskId);
    }

    @Override
    public Map<String, Object> getSeedanceTaskResult(String remoteTaskId) {
        RemoteTaskQueryResult queryResult = remoteMediaGenerationClient.querySeedanceTask(
            modelResolver.resolveVideoProfile("seedance-1.5-pro"),
            remoteTaskId
        );
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskId", queryResult.taskId());
        row.put("status", queryResult.status());
        row.put("videoUrl", queryResult.videoUrl() == null || queryResult.videoUrl().isBlank() ? null : queryResult.videoUrl());
        row.put("message", queryResult.message() == null || queryResult.message().isBlank() ? null : queryResult.message());
        row.put("payload", queryResult.payload());
        return row;
    }

    @Override
    public Map<String, Object> retryTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.retry(taskQueryService.requireTask(taskId)).id);
    }

    @Override
    public Map<String, Object> pauseTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.pause(taskQueryService.requireTask(taskId)).id);
    }

    @Override
    public Map<String, Object> continueTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.resume(taskQueryService.requireTask(taskId)).id);
    }

    @Override
    public Map<String, Object> terminateTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.terminate(taskQueryService.requireTask(taskId)).id);
    }

    @Override
    public Map<String, Object> rateTaskEffect(String taskId, RateTaskEffectRequest request) {
        return taskQueryService.getTask(taskCommandService.rateEffect(taskQueryService.requireTask(taskId), request).id);
    }

    @Override
    public Map<String, Object> deleteTask(String taskId) {
        return taskCommandService.delete(taskQueryService.requireTask(taskId));
    }

    @Override
    public Map<String, Object> adminOverview() {
        Map<String, Object> payload = new LinkedHashMap<>(taskQueryService.adminOverview());
        payload.put("modelReady",
            !modelResolver.listModelsByKind("text").isEmpty()
                && !modelResolver.listModelsByKind("vision").isEmpty()
                && !modelResolver.listModelsByKind("image").isEmpty()
                && !modelResolver.listModelsByKind("video").isEmpty()
        );
        payload.put("primaryModel", null);
        payload.put("textModel", null);
        payload.put("visionModel", null);
        return payload;
    }

    @Override
    public List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit) {
        return taskQueryService.adminTraces(taskId, stage, level, q, limit);
    }

    @Override
    public List<Map<String, Object>> adminWorkers(int limit) {
        return taskQueryService.adminWorkers(limit);
    }

    @Override
    public Map<String, Object> adminWorker(String workerInstanceId) {
        return taskQueryService.adminWorker(workerInstanceId);
    }

    @Override
    public List<Map<String, Object>> adminQueueEvents(String taskId, int limit) {
        return taskQueryService.adminQueueEvents(taskId, limit);
    }

    @Override
    public Map<String, Object> adminQueueOverview(int limit) {
        return taskQueryService.adminQueueOverview(limit);
    }

    @Override
    public Map<String, Object> adminTaskDiagnosis(String taskId) {
        return taskQueryService.adminTaskDiagnosis(taskId);
    }

    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }
}
