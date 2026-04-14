package com.jiandou.api.task.web;

import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
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

/**
 * 任务模块的 Web 入口。
 * 控制器只负责参数接收与路由分发，业务逻辑下沉到应用服务。
 */
@RestController
@RequestMapping("/api/v2/tasks")
public class TaskController {

    private final TaskApplicationService taskService;

    public TaskController(TaskApplicationService taskService) {
        this.taskService = taskService;
    }

    @PostMapping("/generation")
    public Map<String, Object> createGenerationTask(@RequestBody CreateGenerationTaskRequest request) {
        return taskService.createGenerationTask(request);
    }

    @PostMapping("/generate-prompt")
    public Map<String, Object> generateCreativePrompt(@RequestBody GenerateCreativePromptRequest request) {
        return taskService.generateCreativePrompt(request);
    }

    @GetMapping
    public List<Map<String, Object>> listTasks(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "sort", required = false) String sort
    ) {
        return taskService.listTasks(q, status, sort);
    }

    @GetMapping("/{taskId}")
    public Map<String, Object> getTask(@PathVariable String taskId) {
        return taskService.getTask(taskId);
    }

    @GetMapping("/{taskId}/trace")
    public List<Map<String, Object>> getTrace(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getTrace(taskId, limit == null ? 500 : limit);
    }

    @GetMapping("/{taskId}/logs")
    public List<Map<String, Object>> getLogs(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getLogs(taskId, limit == null ? 500 : limit);
    }

    @GetMapping("/{taskId}/status-history")
    public List<Map<String, Object>> getStatusHistory(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getStatusHistory(taskId, limit == null ? 500 : limit);
    }

    @GetMapping("/{taskId}/model-calls")
    public List<Map<String, Object>> getModelCalls(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.getModelCalls(taskId, limit == null ? 500 : limit);
    }

    @GetMapping("/{taskId}/results")
    public List<Map<String, Object>> getResults(@PathVariable String taskId) {
        return taskService.getResults(taskId);
    }

    @GetMapping("/{taskId}/materials")
    public List<Map<String, Object>> getMaterials(@PathVariable String taskId) {
        return taskService.getMaterials(taskId);
    }

    @GetMapping("/seedance/{remoteTaskId}")
    public Map<String, Object> getSeedanceTaskResult(@PathVariable String remoteTaskId) {
        return taskService.getSeedanceTaskResult(remoteTaskId);
    }

    @PostMapping("/{taskId}/retry")
    public Map<String, Object> retry(@PathVariable String taskId) {
        return taskService.retryTask(taskId);
    }

    @PostMapping("/{taskId}/pause")
    public Map<String, Object> pause(@PathVariable String taskId) {
        return taskService.pauseTask(taskId);
    }

    @PostMapping("/{taskId}/continue")
    public Map<String, Object> resume(@PathVariable String taskId) {
        return taskService.continueTask(taskId);
    }

    @PostMapping("/{taskId}/terminate")
    public Map<String, Object> terminate(@PathVariable String taskId) {
        return taskService.terminateTask(taskId);
    }

    @PostMapping("/{taskId}/effect-rating")
    public Map<String, Object> rateEffect(@PathVariable String taskId, @RequestBody RateTaskEffectRequest request) {
        return taskService.rateTaskEffect(taskId, request);
    }

    @DeleteMapping("/{taskId}")
    public Map<String, Object> delete(@PathVariable String taskId) {
        return taskService.deleteTask(taskId);
    }
}
