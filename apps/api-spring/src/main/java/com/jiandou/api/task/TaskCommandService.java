package com.jiandou.api.task;

import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 负责任务生命周期中的命令型操作，例如创建、重试、暂停和终止。
 * 这样应用服务可以专注于接口级用例编排，而不是直接操作任务状态细节。
 */
@Service
public class TaskCommandService {

    private final TaskRepository taskRepository;
    private final TaskExecutionCoordinator executionCoordinator;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final TaskRequestSnapshotFactory requestSnapshotFactory;
    private final Path storageRoot;

    public TaskCommandService(
        TaskRepository taskRepository,
        TaskExecutionCoordinator executionCoordinator,
        ModelRuntimePropertiesResolver modelResolver,
        TaskRequestSnapshotFactory requestSnapshotFactory,
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot
    ) {
        this.taskRepository = taskRepository;
        this.executionCoordinator = executionCoordinator;
        this.modelResolver = modelResolver;
        this.requestSnapshotFactory = requestSnapshotFactory;
        this.storageRoot = Paths.get(storageRoot).toAbsolutePath().normalize();
    }

    public TaskRecord createGenerationTask(CreateGenerationTaskRequest request) {
        validateGenerationTaskRequest(request);
        int defaultDurationSeconds = modelResolver.intValue(
            "catalog.defaults",
            "video_duration_seconds",
            8
        );

        TaskRecord task = new TaskRecord();
        task.id = "task_" + UUID.randomUUID().toString().replace("-", "");
        task.title = trimmed(request.title(), "未命名任务");
        task.status = "PENDING";
        task.progress = 0;
        task.createdAt = task.nowIso();
        task.updatedAt = task.createdAt;
        task.sourceFileName = "text_prompt";
        task.aspectRatio = trimmed(
            request.aspectRatio(),
            modelResolver.value("pipeline", "default_aspect_ratio", "9:16")
        );
        task.minDurationSeconds = request.minDurationSeconds() != null ? request.minDurationSeconds() : defaultDurationSeconds;
        task.maxDurationSeconds = request.maxDurationSeconds() != null ? request.maxDurationSeconds() : defaultDurationSeconds;
        task.retryCount = 0;
        task.completedOutputCount = 0;
        task.hasTranscript = request.transcriptText() != null && !request.transcriptText().isBlank();
        task.hasTimedTranscript = false;
        task.sourceAssetCount = 0;
        task.editingMode = "drama";
        task.introTemplate = "none";
        task.outroTemplate = "none";
        task.creativePrompt = trimmed(request.creativePrompt(), "");
        task.taskSeed = normalizeOptionalSeed(request.seed());
        task.effectRating = null;
        task.effectRatingNote = "";
        task.ratedAt = null;
        task.transcriptText = trimmed(request.transcriptText(), "");
        if (task.taskSeed != null) {
            task.executionContext.put("taskSeed", task.taskSeed);
        }
        task.executionContext.put("artifactBaseRelativeDir", TaskArtifactNaming.taskBaseRelativeDir(task));
        task.executionContext.put("artifactRunningRelativeDir", TaskArtifactNaming.taskRunningRelativeDir(task));
        task.executionContext.put("artifactJoinedRelativeDir", TaskArtifactNaming.taskJoinedRelativeDir(task));
        task.executionContext.put("storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md"));
        createArtifactDirectories(task);
        task.requestSnapshot = requestSnapshotFactory.create(request, task);
        taskRepository.save(task);

        executionCoordinator.createAttempt(task, "create", Map.of(
            "videoModel", trimmed(request.videoModel(), ""),
            "imageModel", trimmed(request.imageModel(), ""),
            "textAnalysisModel", trimmed(request.textAnalysisModel(), ""),
            "visionModel", trimmed(request.visionModel(), "")
        ));
        executionCoordinator.recordTrace(task, "api", "task.created", "生成任务已创建。", "INFO", Map.of(
            "task_type", "generation",
            "taskSeed", task.taskSeed == null ? "" : task.taskSeed,
            "outputCount", task.requestSnapshot.outputCount().toValue(),
            "artifactBaseRelativeDir", TaskArtifactNaming.taskBaseRelativeDir(task),
            "artifactRunningRelativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
            "artifactJoinedRelativeDir", TaskArtifactNaming.taskJoinedRelativeDir(task),
            "storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md")
        ));
        executionCoordinator.enqueue(task, "dispatch", "task.enqueued", "任务已进入队列，等待 Spring 后端任务执行器接管。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    public TaskRecord retry(TaskRecord task) {
        task.retryCount += 1;
        task.errorMessage = "";
        executionCoordinator.createAttempt(task, "retry", buildRetryPayload(task, "retry"));
        executionCoordinator.enqueue(task, "dispatch", "task.retry_requested", "任务已重新加入队列。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    public TaskRecord pause(TaskRecord task) {
        executionCoordinator.dequeue(task);
        task.isQueued = false;
        task.queuePosition = null;
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.info(
                "PAUSED",
                task.progress,
                "api",
                "task.paused",
                "任务已暂停。",
                Map.of("reason", "manual")
            ).withAttempt("PAUSED", "")
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    public TaskRecord resume(TaskRecord task) {
        executionCoordinator.createAttempt(task, "continue", buildRetryPayload(task, "continue"));
        executionCoordinator.enqueue(task, "dispatch", "task.continue_requested", "任务已继续执行。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    public TaskRecord terminate(TaskRecord task) {
        executionCoordinator.dequeue(task);
        task.isQueued = false;
        task.queuePosition = null;
        String errorMessage = "任务已手动终止。";
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.warn(
                "FAILED",
                task.progress,
                "api",
                "task.terminated",
                "任务已终止。",
                Map.of("reason", "manual")
            ).withAttempt("TERMINATED", errorMessage),
            currentTask -> {
                currentTask.errorMessage = errorMessage;
                currentTask.finishedAt = currentTask.nowIso();
            }
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    public TaskRecord rateEffect(TaskRecord task, RateTaskEffectRequest request) {
        int effectRating = normalizeEffectRating(request.effectRating());
        String effectRatingNote = normalizeEffectRatingNote(request.effectRatingNote());
        task.effectRating = effectRating;
        task.effectRatingNote = effectRatingNote;
        task.ratedAt = task.nowIso();
        if (task.executionContext == null) {
            task.executionContext = new LinkedHashMap<>();
        }
        task.executionContext.put("effectRating", effectRating);
        task.executionContext.put("effectRatingNote", effectRatingNote);
        task.executionContext.put("ratedAt", task.ratedAt);
        taskRepository.save(task);
        executionCoordinator.recordTrace(task, "feedback", "task.effect_rated", "任务效果评分已更新。", "INFO", Map.of(
            "effectRating", effectRating,
            "effectRatingNote", effectRatingNote,
            "taskSeed", task.taskSeed == null ? "" : task.taskSeed
        ));
        return task;
    }

    public Map<String, Object> delete(TaskRecord task) {
        executionCoordinator.dequeue(task);
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        taskRepository.delete(task.id);
        return Map.of("taskId", task.id, "deleted", true);
    }

    /**
     * 任务创建时预先准备运行目录，避免后续流水线首次写盘失败。
     */
    private void createArtifactDirectories(TaskRecord task) {
        try {
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskBaseRelativeDir(task)));
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskRunningRelativeDir(task)));
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskJoinedRelativeDir(task)));
        } catch (IOException ex) {
            throw new IllegalStateException("任务产物目录创建失败: " + ex.getMessage(), ex);
        }
    }

    /**
     * 继续执行和重试都复用同一套恢复上下文推导逻辑，保证恢复起点一致。
     */
    private Map<String, Object> buildRetryPayload(TaskRecord task, String triggerType) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("triggerType", triggerType);
        payload.put("retryCount", task.retryCount);
        List<Integer> clipIndices = existingVideoClipIndices(task);
        int completedClipCount = lastContiguousCompletedClipIndex(clipIndices);
        if (task.storyboardScript != null && !task.storyboardScript.isBlank()) {
            payload.put("resumeFromStage", completedClipCount > 0 ? "render" : "planning");
            payload.put("resumeFromClipIndex", Math.max(1, completedClipCount + 1));
            payload.put("completedClipCount", completedClipCount);
            payload.put("existingClipIndices", clipIndices);
            payload.put("reuseStoryboard", true);
        }
        return payload;
    }

    private List<Integer> existingVideoClipIndices(TaskRecord task) {
        LinkedHashSet<Integer> indices = new LinkedHashSet<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(String.valueOf(output.getOrDefault("resultType", "")))) {
                continue;
            }
            Integer clipIndex = integerValue(output.get("clipIndex"));
            if (clipIndex != null && clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        return indices.stream().sorted().toList();
    }

    private int lastContiguousCompletedClipIndex(List<Integer> clipIndices) {
        int expected = 1;
        for (Integer clipIndex : clipIndices) {
            if (clipIndex == null || clipIndex != expected) {
                break;
            }
            expected += 1;
        }
        return expected - 1;
    }

    private Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private void validateGenerationTaskRequest(CreateGenerationTaskRequest request) {
        requireSelectedModel(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireSelectedModel(request.visionModel(), "visionModel", "视觉模型");
        requireSelectedModel(request.imageModel(), "imageModel", "关键帧模型");
        requireSelectedModel(request.videoModel(), "videoModel", "视频模型");
        normalizeOptionalSeed(request.seed());
        normalizeOutputCount(request.outputCount());
    }

    private Integer normalizeOptionalSeed(Integer seed) {
        if (seed == null) {
            return null;
        }
        if (seed < 0) {
            throw new IllegalArgumentException("seed 不能小于 0");
        }
        return seed;
    }

    private Object normalizeOutputCount(Object outputCount) {
        if (outputCount == null) {
            return "auto";
        }
        String raw = String.valueOf(outputCount).trim();
        if (raw.isBlank() || "auto".equalsIgnoreCase(raw)) {
            return "auto";
        }
        try {
            int value = Integer.parseInt(raw);
            if (value < 1) {
                throw new IllegalArgumentException("outputCount 必须大于 0");
            }
            return value;
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException("outputCount 必须为正整数或 auto");
        }
    }

    private int normalizeEffectRating(Integer effectRating) {
        if (effectRating == null) {
            throw new IllegalArgumentException("effectRating 不能为空");
        }
        if (effectRating < 1 || effectRating > 5) {
            throw new IllegalArgumentException("effectRating 必须在 1 到 5 之间");
        }
        return effectRating;
    }

    private String normalizeEffectRatingNote(String note) {
        String normalized = trimmed(note, "");
        if (normalized.length() > 1000) {
            throw new IllegalArgumentException("effectRatingNote 不能超过 1000 个字符");
        }
        return normalized;
    }

    private String requireSelectedModel(String value, String fieldName, String label) {
        String normalized = trimmed(value, "");
        if (!normalized.isBlank()) {
            return normalized;
        }
        throw new IllegalArgumentException("请先选择" + label + "（" + fieldName + "）");
    }

    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }
}
