package com.jiandou.api.admin.web;

import com.jiandou.api.admin.application.AdminModelConfigService;
import com.jiandou.api.admin.dto.AdminModelConfigKeyUpdateRequest;
import com.jiandou.api.admin.dto.AdminModelConfigResponse;
import com.jiandou.api.admin.dto.AdminModelConfigValidationResponse;
import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端接口聚合任务运营视图、诊断和批量控制能力。
 */
@RestController
@RequestMapping(ApiPathConstants.ADMIN)
public class AdminController {

    private final TaskApplicationService taskService;
    private final JiandouTaskOpsProperties taskOpsProperties;
    private final AdminModelConfigService modelConfigService;

    /**
     * 创建新的管理控制器。
     * @param taskService 任务服务值
     */
    public AdminController(
        TaskApplicationService taskService,
        JiandouTaskOpsProperties taskOpsProperties,
        AdminModelConfigService modelConfigService
    ) {
        this.taskService = taskService;
        this.taskOpsProperties = taskOpsProperties;
        this.modelConfigService = modelConfigService;
    }

    /**
     * 获取概览。
     * @return 处理结果
     */
    @GetMapping("/overview")
    public Map<String, Object> overview() {
        return taskService.adminOverview();
    }

    /**
     * 返回当前模型配置快照。
     * @return 处理结果
     */
    @GetMapping("/model-config")
    public AdminModelConfigResponse modelConfig() {
        return modelConfigService.read();
    }

    /**
     * 校验模型配置草稿。
     * @param request 草稿请求体
     * @return 处理结果
     */
    @PostMapping("/model-config/validate")
    public AdminModelConfigValidationResponse validateModelConfig(@org.springframework.web.bind.annotation.RequestBody AdminModelConfigKeyUpdateRequest request) {
        return modelConfigService.validateKeys(request);
    }

    /**
     * 保存模型接入 API Key 配置并刷新运行时。
     * @param request 密钥请求体
     * @return 处理结果
     */
    @PostMapping("/model-config/keys")
    public AdminModelConfigResponse saveModelConfigKeys(@org.springframework.web.bind.annotation.RequestBody AdminModelConfigKeyUpdateRequest request) {
        return modelConfigService.saveKeys(request);
    }

    @GetMapping("/tasks")
    public List<Map<String, Object>> listTasks(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "sort", required = false) String sort
    ) {
        return taskService.listTasks(q, status, sort);
    }

    /**
     * 返回任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @GetMapping("/tasks/{taskId}")
    public Map<String, Object> getTask(@PathVariable String taskId) {
        return taskService.getTask(taskId);
    }

    @GetMapping("/tasks/{taskId}/trace")
    public List<Map<String, Object>> getTaskTrace(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getTrace(taskId, limit == null ? taskOpsProperties.getTraceLimit() : limit);
    }

    @GetMapping("/traces")
    public List<Map<String, Object>> listTraces(
        @RequestParam(value = "task_id", required = false) String taskId,
        @RequestParam(value = "stage", required = false) String stage,
        @RequestParam(value = "level", required = false) String level,
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return taskService.adminTraces(taskId, stage, level, q, limit == null ? taskOpsProperties.getAdminTraceLimit() : limit);
    }

    @GetMapping("/workers")
    public List<Map<String, Object>> listWorkers(@RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.adminWorkers(limit == null ? taskOpsProperties.getAdminWorkerLimit() : limit);
    }

    /**
     * 返回工作节点。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    @GetMapping("/workers/{workerInstanceId}")
    public Map<String, Object> getWorker(@PathVariable String workerInstanceId) {
        return taskService.adminWorker(workerInstanceId);
    }

    @GetMapping("/queue")
    public Map<String, Object> queueOverview(@RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.adminQueueOverview(limit == null ? taskOpsProperties.getAdminQueueLimit() : limit);
    }

    @GetMapping("/queue/events")
    public List<Map<String, Object>> listQueueEvents(
        @RequestParam(value = "task_id", required = false) String taskId,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return taskService.adminQueueEvents(taskId, limit == null ? taskOpsProperties.getAdminQueueLimit() : limit);
    }

    @GetMapping("/tasks/{taskId}/queue-events")
    public List<Map<String, Object>> getTaskQueueEvents(
        @PathVariable String taskId,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return taskService.adminQueueEvents(taskId, limit == null ? taskOpsProperties.getAdminQueueLimit() : limit);
    }

    /**
     * 返回任务诊断。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @GetMapping("/tasks/{taskId}/diagnosis")
    public Map<String, Object> getTaskDiagnosis(@PathVariable String taskId) {
        return taskService.adminTaskDiagnosis(taskId);
    }

    /**
     * 重试重试。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @PostMapping("/tasks/{taskId}/retry")
    public Map<String, Object> retry(@PathVariable String taskId) {
        return taskService.retryTask(taskId);
    }

    /**
     * 终止terminate。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @PostMapping("/tasks/{taskId}/terminate")
    public Map<String, Object> terminate(@PathVariable String taskId) {
        return taskService.terminateTask(taskId);
    }

    /**
     * 处理评分效果。
     * @param taskId 任务标识
     * @param request 请求体
     * @return 处理结果
     */
    @PostMapping("/tasks/{taskId}/effect-rating")
    public Map<String, Object> rateEffect(
        @PathVariable String taskId,
        @org.springframework.web.bind.annotation.RequestBody RateTaskEffectRequest request
    ) {
        return taskService.rateTaskEffect(taskId, request);
    }

    /**
     * 删除删除。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @DeleteMapping("/tasks/{taskId}")
    public Map<String, Object> delete(@PathVariable String taskId) {
        return taskService.deleteTask(taskId);
    }

    /**
     * 处理批量删除。
     * @param request 请求体
     * @return 处理结果
     */
    @PostMapping("/tasks/bulk-delete")
    public Map<String, Object> bulkDelete(@org.springframework.web.bind.annotation.RequestBody TaskIdsRequest request) {
        List<String> taskIds = request.taskIds() == null ? List.of() : request.taskIds();
        taskIds.forEach(taskService::deleteTask);
        return Map.of(
            "action", "delete",
            "requestedCount", taskIds.size(),
            "succeededTaskIds", taskIds,
            "failed", List.of()
        );
    }

    /**
     * 处理批量重试。
     * @param request 请求体
     * @return 处理结果
     */
    @PostMapping("/tasks/bulk-retry")
    public Map<String, Object> bulkRetry(@org.springframework.web.bind.annotation.RequestBody TaskIdsRequest request) {
        List<String> taskIds = request.taskIds() == null ? List.of() : request.taskIds();
        taskIds.forEach(taskService::retryTask);
        return Map.of(
            "action", "retry",
            "requestedCount", taskIds.size(),
            "succeededTaskIds", taskIds,
            "failed", List.of()
        );
    }

    /**
     * 任务标识批量请求体。
     * @param taskIds 任务标识列表值
     * @return 处理结果
     */
    public record TaskIdsRequest(List<String> taskIds) {}
}
