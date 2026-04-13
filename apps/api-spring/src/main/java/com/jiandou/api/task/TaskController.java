package com.jiandou.api.task;

import com.jiandou.api.task.application.TaskApplicationService;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v2/tasks")
public class TaskController {

    private final TaskApplicationService taskService;

    public TaskController(TaskApplicationService taskService) {
        this.taskService = taskService;
    }

    @PostMapping("/generation")
    public Map<String, Object> createGenerationTask(@RequestBody CreateGenerationTaskRequest request) {
        return invoke(() -> taskService.createGenerationTask(request));
    }

    @PostMapping("/generate-prompt")
    public Map<String, Object> generateCreativePrompt(@RequestBody GenerateCreativePromptRequest request) {
        return taskService.generateCreativePrompt(request);
    }

    @GetMapping
    public List<Map<String, Object>> listTasks(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "platform", required = false) String platform,
        @RequestParam(value = "sort", required = false) String sort
    ) {
        return taskService.listTasks(q, status, platform, sort);
    }

    @GetMapping("/{taskId}")
    public Map<String, Object> getTask(@PathVariable String taskId) {
        return invoke(() -> taskService.getTask(taskId));
    }

    @GetMapping("/{taskId}/trace")
    public List<Map<String, Object>> getTrace(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return invoke(() -> taskService.getTrace(taskId, limit == null ? 500 : limit));
    }

    @GetMapping("/{taskId}/logs")
    public List<Map<String, Object>> getLogs(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return invoke(() -> taskService.getLogs(taskId, limit == null ? 500 : limit));
    }

    @GetMapping("/{taskId}/status-history")
    public List<Map<String, Object>> getStatusHistory(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return invoke(() -> taskService.getStatusHistory(taskId, limit == null ? 500 : limit));
    }

    @GetMapping("/{taskId}/model-calls")
    public List<Map<String, Object>> getModelCalls(@PathVariable String taskId, @RequestParam(value = "limit", required = false) Integer limit) {
        return invoke(() -> taskService.getModelCalls(taskId, limit == null ? 500 : limit));
    }

    @GetMapping("/{taskId}/results")
    public List<Map<String, Object>> getResults(@PathVariable String taskId) {
        return invoke(() -> taskService.getResults(taskId));
    }

    @GetMapping("/{taskId}/materials")
    public List<Map<String, Object>> getMaterials(@PathVariable String taskId) {
        return invoke(() -> taskService.getMaterials(taskId));
    }

    @GetMapping("/seedance/{remoteTaskId}")
    public Map<String, Object> getSeedanceTaskResult(@PathVariable String remoteTaskId) {
        return taskService.getSeedanceTaskResult(remoteTaskId);
    }

    @PostMapping("/{taskId}/retry")
    public Map<String, Object> retry(@PathVariable String taskId) {
        return invoke(() -> taskService.retryTask(taskId));
    }

    @PostMapping("/{taskId}/pause")
    public Map<String, Object> pause(@PathVariable String taskId) {
        return invoke(() -> taskService.pauseTask(taskId));
    }

    @PostMapping("/{taskId}/continue")
    public Map<String, Object> resume(@PathVariable String taskId) {
        return invoke(() -> taskService.continueTask(taskId));
    }

    @PostMapping("/{taskId}/terminate")
    public Map<String, Object> terminate(@PathVariable String taskId) {
        return invoke(() -> taskService.terminateTask(taskId));
    }

    @PostMapping("/{taskId}/effect-rating")
    public Map<String, Object> rateEffect(@PathVariable String taskId, @RequestBody RateTaskEffectRequest request) {
        return invoke(() -> taskService.rateTaskEffect(taskId, request));
    }

    @DeleteMapping("/{taskId}")
    public Map<String, Object> delete(@PathVariable String taskId) {
        return invoke(() -> taskService.deleteTask(taskId));
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

    public record CreateGenerationTaskRequest(
        @NotBlank String title,
        String creativePrompt,
        String platform,
        String aspectRatio,
        String textAnalysisModel,
        String visionModel,
        String imageModel,
        String videoModel,
        String videoSize,
        Integer seed,
        Object videoDurationSeconds,
        Object outputCount,
        Integer minDurationSeconds,
        Integer maxDurationSeconds,
        String transcriptText,
        Boolean stopBeforeVideoGeneration
    ) {}

    public record GenerateCreativePromptRequest(
        @NotBlank String title,
        String platform,
        String aspectRatio,
        Integer minDurationSeconds,
        Integer maxDurationSeconds,
        String introTemplate,
        String outroTemplate,
        String transcriptText
    ) {}

    public record RateTaskEffectRequest(
        Integer effectRating,
        String effectRatingNote
    ) {}
}
