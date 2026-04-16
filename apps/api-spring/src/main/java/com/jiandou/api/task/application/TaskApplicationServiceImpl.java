package com.jiandou.api.task.application;

import com.jiandou.api.config.JiandouTaskDefaultsProperties;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
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
    private final VideoModelProviderRegistry videoModelProviderRegistry;
    private final JiandouTaskDefaultsProperties taskDefaultsProperties;

    /**
     * 创建新的任务应用服务Impl。
     * @param taskQueryService 任务查询服务值
     * @param taskCommandService 任务Command服务值
     * @param modelResolver 模型解析器值
     * @param videoModelProviderRegistry 视频模型 provider 注册表值
     */
    public TaskApplicationServiceImpl(
        TaskQueryService taskQueryService,
        TaskCommandService taskCommandService,
        ModelRuntimePropertiesResolver modelResolver,
        VideoModelProviderRegistry videoModelProviderRegistry,
        JiandouTaskDefaultsProperties taskDefaultsProperties
    ) {
        this.taskQueryService = taskQueryService;
        this.taskCommandService = taskCommandService;
        this.modelResolver = modelResolver;
        this.videoModelProviderRegistry = videoModelProviderRegistry;
        this.taskDefaultsProperties = taskDefaultsProperties;
    }

    /**
     * 创建生成任务。
     * @param request 请求体
     * @return 处理结果
     */
    @Override
    public Map<String, Object> createGenerationTask(CreateGenerationTaskRequest request) {
        return taskQueryService.getTask(taskCommandService.createGenerationTask(request).id());
    }

    /**
     * 生成创意提示词。
     * @param request 请求体
     * @return 处理结果
     */
    @Override
    public Map<String, Object> generateCreativePrompt(GenerateCreativePromptRequest request) {
        String title = trimmed(request.title(), "未命名任务");
        String prompt = "短剧风格，情绪递进，人物表情贴合语境，镜头写实，台词和配音语气符合剧情：" + title;
        return Map.of(
            "prompt", prompt,
            "source", taskDefaultsProperties.getPromptSource()
        );
    }

    /**
     * 列出任务。
     * @param q 查询文本
     * @param status 状态值
     * @param sort 排序方式
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> listTasks(String q, String status, String sort) {
        return taskQueryService.listTasks(q, status, sort);
    }

    /**
     * 返回任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> getTask(String taskId) {
        return taskQueryService.getTask(taskId);
    }

    /**
     * 返回追踪。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getTrace(String taskId, int limit) {
        return taskQueryService.getTrace(taskId, limit);
    }

    /**
     * 返回Logs。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getLogs(String taskId, int limit) {
        return taskQueryService.getLogs(taskId, limit);
    }

    /**
     * 返回状态History。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getStatusHistory(String taskId, int limit) {
        return taskQueryService.getStatusHistory(taskId, limit);
    }

    /**
     * 返回模型Calls。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getModelCalls(String taskId, int limit) {
        return taskQueryService.getModelCalls(taskId, limit);
    }

    /**
     * 返回Results。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getResults(String taskId) {
        return taskQueryService.getResults(taskId);
    }

    /**
     * 返回素材。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> getMaterials(String taskId) {
        return taskQueryService.getMaterials(taskId);
    }

    /**
     * 返回Seedance任务结果。
     * @param remoteTaskId 远程任务标识值
     * @return 处理结果
     */
    @Override
    public Map<String, Object> getSeedanceTaskResult(String remoteTaskId) {
        var profile = modelResolver.resolveVideoProfile(taskDefaultsProperties.getSeedanceQueryModel());
        RemoteTaskQueryResult queryResult = videoModelProviderRegistry.resolve(profile).query(profile, remoteTaskId);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskId", queryResult.taskId());
        row.put("status", queryResult.status());
        row.put("videoUrl", queryResult.videoUrl() == null || queryResult.videoUrl().isBlank() ? null : queryResult.videoUrl());
        row.put("message", queryResult.message() == null || queryResult.message().isBlank() ? null : queryResult.message());
        row.put("payload", queryResult.payload());
        return row;
    }

    /**
     * 重试任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> retryTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.retry(taskQueryService.requireTask(taskId)).id());
    }

    /**
     * 暂停任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> pauseTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.pause(taskQueryService.requireTask(taskId)).id());
    }

    /**
     * 处理继续任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> continueTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.resume(taskQueryService.requireTask(taskId)).id());
    }

    /**
     * 终止任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> terminateTask(String taskId) {
        return taskQueryService.getTask(taskCommandService.terminate(taskQueryService.requireTask(taskId)).id());
    }

    /**
     * 处理评分任务效果。
     * @param taskId 任务标识
     * @param request 请求体
     * @return 处理结果
     */
    @Override
    public Map<String, Object> rateTaskEffect(String taskId, RateTaskEffectRequest request) {
        return taskQueryService.getTask(taskCommandService.rateEffect(taskQueryService.requireTask(taskId), request).id());
    }

    /**
     * 删除任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> deleteTask(String taskId) {
        return taskCommandService.delete(taskQueryService.requireTask(taskId));
    }

    /**
     * 处理管理概览。
     * @return 处理结果
     */
    @Override
    public Map<String, Object> adminOverview() {
        Map<String, Object> payload = new LinkedHashMap<>(taskQueryService.adminOverview());
        payload.put("modelReady",
            !modelResolver.listModelsByKind(com.jiandou.api.generation.GenerationModelKinds.TEXT).isEmpty()
                && !modelResolver.listModelsByKind(com.jiandou.api.generation.GenerationModelKinds.VISION).isEmpty()
                && !modelResolver.listModelsByKind(com.jiandou.api.generation.GenerationModelKinds.IMAGE).isEmpty()
                && !modelResolver.listModelsByKind(com.jiandou.api.generation.GenerationModelKinds.VIDEO).isEmpty()
        );
        payload.put("primaryModel", null);
        payload.put("textModel", null);
        payload.put("visionModel", null);
        return payload;
    }

    /**
     * 处理管理Traces。
     * @param taskId 任务标识
     * @param stage 阶段名称
     * @param level level值
     * @param q 查询文本
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit) {
        return taskQueryService.adminTraces(taskId, stage, level, q, limit);
    }

    /**
     * 处理管理Workers。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> adminWorkers(int limit) {
        return taskQueryService.adminWorkers(limit);
    }

    /**
     * 处理管理工作节点。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> adminWorker(String workerInstanceId) {
        return taskQueryService.adminWorker(workerInstanceId);
    }

    /**
     * 处理管理队列Events。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> adminQueueEvents(String taskId, int limit) {
        return taskQueryService.adminQueueEvents(taskId, limit);
    }

    /**
     * 处理管理队列概览。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public Map<String, Object> adminQueueOverview(int limit) {
        return taskQueryService.adminQueueOverview(limit);
    }

    /**
     * 处理管理任务诊断。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Override
    public Map<String, Object> adminTaskDiagnosis(String taskId) {
        return taskQueryService.adminTaskDiagnosis(taskId);
    }

    /**
     * 处理trimmed。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }
}
