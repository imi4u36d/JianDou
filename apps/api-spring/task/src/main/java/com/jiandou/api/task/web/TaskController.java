package com.jiandou.api.task.web;

import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import com.jiandou.api.task.web.dto.TaskListItemResponse;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * 任务模块的 Web 入口。
 * 控制器只负责参数接收与路由分发，业务逻辑下沉到应用服务。
 */
@RestController
@RequestMapping(ApiPathConstants.TASKS)
@Tag(name = "Tasks", description = "任务管理")
public class TaskController {

    private final TaskApplicationService taskService;
    private final JiandouTaskOpsProperties taskOpsProperties;

    /**
     * 创建新的任务控制器。
     * @param taskService 任务服务值
     */
    public TaskController(TaskApplicationService taskService, JiandouTaskOpsProperties taskOpsProperties) {
        this.taskService = taskService;
        this.taskOpsProperties = taskOpsProperties;
    }

    /**
     * 创建生成任务。
     * @param request 请求体
     * @return 处理结果
     */
    @Operation(summary = "创建生成任务")
    @PostMapping("/generation")
    public Map<String, Object> createGenerationTask(@RequestBody CreateGenerationTaskRequest request) {
        return taskService.createGenerationTask(request);
    }

    /**
     * 生成创意提示词。
     * @param request 请求体
     * @return 处理结果
     */
    @Operation(summary = "生成创意提示词")
    @PostMapping("/generate-prompt")
    public Map<String, Object> generateCreativePrompt(@RequestBody GenerateCreativePromptRequest request) {
        return taskService.generateCreativePrompt(request);
    }

    @Operation(summary = "查询任务列表")
    @GetMapping
    public List<TaskListItemResponse> listTasks(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "sort", required = false) String sort
    ) {
        return taskService.listTasks(q, status, sort);
    }

    /**
     * 返回官网与工作台共用的案例展示。
     * @return 处理结果
     */
    @Operation(summary = "获取案例展示")
    @GetMapping("/showcase")
    public Map<String, Object> showcaseCases() {
        return taskService.showcaseCases();
    }

    /**
     * 返回任务。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "获取任务详情")
    @GetMapping("/{taskId}")
    public Map<String, Object> getTask(@PathVariable String taskId) {
        return taskService.getTask(taskId);
    }

    @Operation(summary = "获取任务追踪")
    @GetMapping("/{taskId}/trace")
    public List<Map<String, Object>> getTrace(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getTrace(taskId, limit == null ? taskOpsProperties.getTraceLimit() : limit);
    }

    @Operation(summary = "获取任务日志")
    @GetMapping("/{taskId}/logs")
    public List<Map<String, Object>> getLogs(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getLogs(taskId, limit == null ? taskOpsProperties.getLogLimit() : limit);
    }

    @Operation(summary = "获取状态变更历史")
    @GetMapping("/{taskId}/status-history")
    public List<Map<String, Object>> getStatusHistory(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getStatusHistory(taskId, limit == null ? taskOpsProperties.getStatusHistoryLimit() : limit);
    }

    @Operation(summary = "获取模型调用记录")
    @GetMapping("/{taskId}/model-calls")
    public List<Map<String, Object>> getModelCalls(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getModelCalls(taskId, limit == null ? taskOpsProperties.getModelCallLimit() : limit);
    }

    /**
     * 返回Results。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "获取任务结果")
    @GetMapping("/{taskId}/results")
    public List<Map<String, Object>> getResults(@PathVariable String taskId) {
        return taskService.getResults(taskId);
    }

    /**
     * 返回素材。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "获取任务素材")
    @GetMapping("/{taskId}/materials")
    public List<Map<String, Object>> getMaterials(@PathVariable String taskId) {
        return taskService.getMaterials(taskId);
    }

    /**
     * 返回Seedance任务结果。
     * @param remoteTaskId 远程任务标识值
     * @return 处理结果
     */
    @Operation(summary = "查询 Seedance 任务结果")
    @GetMapping("/seedance/{remoteTaskId}")
    public Map<String, Object> getSeedanceTaskResult(@PathVariable String remoteTaskId) {
        return taskService.getSeedanceTaskResult(remoteTaskId);
    }

    /**
     * 重试重试。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "重试任务")
    @PostMapping("/{taskId}/retry")
    public Map<String, Object> retry(@PathVariable String taskId) {
        return taskService.retryTask(taskId);
    }

    /**
     * 暂停pause。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "暂停任务")
    @PostMapping("/{taskId}/pause")
    public Map<String, Object> pause(@PathVariable String taskId) {
        return taskService.pauseTask(taskId);
    }

    /**
     * 恢复resume。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "恢复任务")
    @PostMapping("/{taskId}/continue")
    public Map<String, Object> resume(@PathVariable String taskId) {
        return taskService.continueTask(taskId);
    }

    /**
     * 终止terminate。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "终止任务")
    @PostMapping("/{taskId}/terminate")
    public Map<String, Object> terminate(@PathVariable String taskId) {
        return taskService.terminateTask(taskId);
    }

    /**
     * 处理评分效果。
     * @param taskId 任务标识
     * @param request 请求体
     * @return 处理结果
     */
    @Operation(summary = "评价任务效果")
    @PostMapping("/{taskId}/effect-rating")
    public Map<String, Object> rateEffect(@PathVariable String taskId, @RequestBody RateTaskEffectRequest request) {
        return taskService.rateTaskEffect(taskId, request);
    }

    /**
     * 删除删除。
     * @param taskId 任务标识
     * @return 处理结果
     */
    @Operation(summary = "删除任务")
    @DeleteMapping("/{taskId}")
    public Map<String, Object> delete(@PathVariable String taskId) {
        return taskService.deleteTask(taskId);
    }
}
