package com.jiandou.api.task.application;

import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import com.jiandou.api.task.web.dto.TaskListItemResponse;
import java.util.List;
import java.util.Map;

/**
 * 任务模块应用服务接口。
 * 该接口对外暴露任务创建、查询、控制和管理相关用例。
 */
public interface TaskApplicationService {

    /**
     * 创建生成任务。
     * @param request 请求体
     * @return 处理结果
     */
    Map<String, Object> createGenerationTask(CreateGenerationTaskRequest request);

    /**
     * 生成创意提示词。
     * @param request 请求体
     * @return 处理结果
     */
    Map<String, Object> generateCreativePrompt(GenerateCreativePromptRequest request);

    /**
     * 列出任务。
     * @param q 查询文本
     * @param status 状态值
     * @param sort 排序方式
     * @return 处理结果
     */
    List<TaskListItemResponse> listTasks(String q, String status, String sort);

    /**
     * 管理端列出全部任务。
     * @param q 查询文本
     * @param status 状态值
     * @param sort 排序方式
     * @return 处理结果
     */
    List<TaskListItemResponse> adminListTasks(String q, String status, String sort);

    /**
     * 返回公开案例展示。
     * @return 处理结果
     */
    Map<String, Object> showcaseCases();

    /**
     * 返回任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> getTask(String taskId);

    /**
     * 管理端返回任务详情。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> adminGetTask(String taskId);

    /**
     * 返回追踪。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> getTrace(String taskId, int limit);

    /**
     * 返回Logs。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> getLogs(String taskId, int limit);

    /**
     * 返回状态History。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> getStatusHistory(String taskId, int limit);

    /**
     * 返回模型Calls。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> getModelCalls(String taskId, int limit);

    /**
     * 返回Results。
     * @param taskId 任务标识
     * @return 处理结果
     */
    List<Map<String, Object>> getResults(String taskId);

    /**
     * 返回素材。
     * @param taskId 任务标识
     * @return 处理结果
     */
    List<Map<String, Object>> getMaterials(String taskId);

    /**
     * 返回Seedance任务结果。
     * @param remoteTaskId 远程任务标识值
     * @return 处理结果
     */
    Map<String, Object> getSeedanceTaskResult(String remoteTaskId);

    /**
     * 重试任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> retryTask(String taskId);

    /**
     * 暂停任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> pauseTask(String taskId);

    /**
     * 处理继续任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> continueTask(String taskId);

    /**
     * 终止任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> terminateTask(String taskId);

    /**
     * 管理端终止任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> adminTerminateTask(String taskId);

    /**
     * 处理评分任务效果。
     * @param taskId 任务标识
     * @param request 请求体
     * @return 处理结果
     */
    Map<String, Object> rateTaskEffect(String taskId, RateTaskEffectRequest request);

    /**
     * 删除任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> deleteTask(String taskId);

    /**
     * 处理管理概览。
     * @return 处理结果
     */
    Map<String, Object> adminOverview();

    /**
     * 处理管理Traces。
     * @param taskId 任务标识
     * @param stage 阶段名称
     * @param level level值
     * @param q 查询文本
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit);

    /**
     * 处理管理Workers。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> adminWorkers(int limit);

    /**
     * 处理管理工作节点。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    Map<String, Object> adminWorker(String workerInstanceId);

    /**
     * 处理管理队列Events。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> adminQueueEvents(String taskId, int limit);

    /**
     * 处理管理队列概览。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    Map<String, Object> adminQueueOverview(int limit);

    /**
     * 处理管理任务诊断。
     * @param taskId 任务标识
     * @return 处理结果
     */
    Map<String, Object> adminTaskDiagnosis(String taskId);
}
