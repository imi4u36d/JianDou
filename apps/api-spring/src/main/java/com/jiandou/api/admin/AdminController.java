package com.jiandou.api.admin;

import com.jiandou.api.task.TaskNotFoundException;
import com.jiandou.api.task.application.TaskApplicationService;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v2/admin")
public class AdminController {

    private final TaskApplicationService taskService;

    public AdminController(TaskApplicationService taskService) {
        this.taskService = taskService;
    }

    @GetMapping("/overview")
    public Map<String, Object> overview() {
        return taskService.adminOverview();
    }

    @GetMapping("/tasks")
    public List<Map<String, Object>> listTasks(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "platform", required = false) String platform,
        @RequestParam(value = "sort", required = false) String sort
    ) {
        return taskService.listTasks(q, status, platform, sort);
    }

    @GetMapping("/tasks/{taskId}")
    public Map<String, Object> getTask(@PathVariable String taskId) {
        return invoke(() -> taskService.getTask(taskId));
    }

    @GetMapping("/tasks/{taskId}/trace")
    public List<Map<String, Object>> getTaskTrace(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return invoke(() -> taskService.getTrace(taskId, limit == null ? 500 : limit));
    }

    @GetMapping("/traces")
    public List<Map<String, Object>> listTraces(
        @RequestParam(value = "task_id", required = false) String taskId,
        @RequestParam(value = "stage", required = false) String stage,
        @RequestParam(value = "level", required = false) String level,
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return taskService.adminTraces(taskId, stage, level, q, limit == null ? 200 : limit);
    }

    @GetMapping("/workers")
    public List<Map<String, Object>> listWorkers(@RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.adminWorkers(limit == null ? 100 : limit);
    }

    @GetMapping("/workers/{workerInstanceId}")
    public Map<String, Object> getWorker(@PathVariable String workerInstanceId) {
        return invoke(() -> taskService.adminWorker(workerInstanceId));
    }

    @GetMapping("/queue")
    public Map<String, Object> queueOverview(@RequestParam(value = "limit", required = false) Integer limit) {
        return taskService.adminQueueOverview(limit == null ? 200 : limit);
    }

    @GetMapping("/queue/events")
    public List<Map<String, Object>> listQueueEvents(
        @RequestParam(value = "task_id", required = false) String taskId,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return taskService.adminQueueEvents(taskId, limit == null ? 200 : limit);
    }

    @GetMapping("/tasks/{taskId}/queue-events")
    public List<Map<String, Object>> getTaskQueueEvents(
        @PathVariable String taskId,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        return invoke(() -> taskService.adminQueueEvents(taskId, limit == null ? 200 : limit));
    }

    @GetMapping("/tasks/{taskId}/diagnosis")
    public Map<String, Object> getTaskDiagnosis(@PathVariable String taskId) {
        return invoke(() -> taskService.adminTaskDiagnosis(taskId));
    }

    @PostMapping("/tasks/{taskId}/retry")
    public Map<String, Object> retry(@PathVariable String taskId) {
        return invoke(() -> taskService.retryTask(taskId));
    }

    @PostMapping("/tasks/{taskId}/terminate")
    public Map<String, Object> terminate(@PathVariable String taskId) {
        return invoke(() -> taskService.terminateTask(taskId));
    }

    @PostMapping("/tasks/{taskId}/effect-rating")
    public Map<String, Object> rateEffect(
        @PathVariable String taskId,
        @org.springframework.web.bind.annotation.RequestBody com.jiandou.api.task.TaskController.RateTaskEffectRequest request
    ) {
        return invoke(() -> taskService.rateTaskEffect(taskId, request));
    }

    @DeleteMapping("/tasks/{taskId}")
    public Map<String, Object> delete(@PathVariable String taskId) {
        return invoke(() -> taskService.deleteTask(taskId));
    }

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

    private <T> T invoke(Callback<T> callback) {
        try {
            return callback.call();
        } catch (IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, ex.getMessage(), ex);
        } catch (TaskNotFoundException ex) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "task not found", ex);
        }
    }

    @FunctionalInterface
    private interface Callback<T> {
        T call();
    }

    public record TaskIdsRequest(List<String> taskIds) {}
}
