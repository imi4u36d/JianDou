package com.jiandou.api.task.application;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.config.JiandouTaskDefaultsProperties;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.AttemptStatus;
import com.jiandou.api.task.domain.AttemptTriggerType;
import com.jiandou.api.task.domain.TaskArtifactNaming;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStateTransition;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.domain.TraceLevel;
import com.jiandou.api.task.persistence.TaskRepository;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
    private final JiandouTaskDefaultsProperties taskDefaultsProperties;
    private final Path storageRoot;

    /**
     * 创建新的任务Command服务。
     */
    public TaskCommandService(
        TaskRepository taskRepository,
        TaskExecutionCoordinator executionCoordinator,
        ModelRuntimePropertiesResolver modelResolver,
        TaskRequestSnapshotFactory requestSnapshotFactory,
        JiandouTaskDefaultsProperties taskDefaultsProperties,
        JiandouStorageProperties storageProperties
    ) {
        this.taskRepository = taskRepository;
        this.executionCoordinator = executionCoordinator;
        this.modelResolver = modelResolver;
        this.requestSnapshotFactory = requestSnapshotFactory;
        this.taskDefaultsProperties = taskDefaultsProperties;
        this.storageRoot = storageProperties.resolveRootDir();
    }

    /**
     * 创建生成任务。
     * @param request 请求体
     * @return 处理结果
     */
    public TaskRecord createGenerationTask(CreateGenerationTaskRequest request) {
        validateGenerationTaskRequest(request);
        int defaultDurationSeconds = modelResolver.intValue(
            "catalog.defaults",
            "video_duration_seconds",
            taskDefaultsProperties.getDefaultDurationSeconds()
        );

        TaskRecord task = new TaskRecord();
        task.setId("task_" + UUID.randomUUID().toString().replace("-", ""));
        task.setTitle(trimmed(request.title(), "未命名任务"));
        task.setStatus(TaskStatus.PENDING);
        task.setProgress(0);
        task.setCreatedAt(task.nowIso());
        task.setUpdatedAt(task.createdAt());
        task.setSourceFileName(taskDefaultsProperties.getSourceFileName());
        task.setAspectRatio(trimmed(
            request.aspectRatio(),
            modelResolver.value("pipeline", "default_aspect_ratio", taskDefaultsProperties.getDefaultAspectRatio())
        ));
        task.setMinDurationSeconds(request.minDurationSeconds() != null ? request.minDurationSeconds() : defaultDurationSeconds);
        task.setMaxDurationSeconds(request.maxDurationSeconds() != null ? request.maxDurationSeconds() : defaultDurationSeconds);
        task.setRetryCount(0);
        task.setCompletedOutputCount(0);
        task.setHasTranscript(request.transcriptText() != null && !request.transcriptText().isBlank());
        task.setHasTimedTranscript(false);
        task.setSourceAssetCount(0);
        task.setEditingMode(taskDefaultsProperties.getEditingMode());
        task.setIntroTemplate(taskDefaultsProperties.getIntroTemplate());
        task.setOutroTemplate(taskDefaultsProperties.getOutroTemplate());
        task.setCreativePrompt(trimmed(request.creativePrompt(), ""));
        task.setTaskSeed(normalizeOptionalSeed(request.seed()));
        task.setEffectRating(null);
        task.setEffectRatingNote("");
        task.setRatedAt(null);
        task.setTranscriptText(trimmed(request.transcriptText(), ""));
        if (task.taskSeed() != null) {
            task.mutableExecutionContext().put("taskSeed", task.taskSeed());
        }
        task.mutableExecutionContext().put("artifactBaseRelativeDir", TaskArtifactNaming.taskBaseRelativeDir(task));
        task.mutableExecutionContext().put("artifactRunningRelativeDir", TaskArtifactNaming.taskRunningRelativeDir(task));
        task.mutableExecutionContext().put("artifactJoinedRelativeDir", TaskArtifactNaming.taskJoinedRelativeDir(task));
        task.mutableExecutionContext().put("storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md"));
        createArtifactDirectories(task);
        task.setRequestSnapshot(requestSnapshotFactory.create(request, task));
        taskRepository.save(task);

        executionCoordinator.createAttempt(task, AttemptTriggerType.CREATE, Map.of(
            /**
             * 处理trimmed。
             * @param request.videoModel( request.videoModel(值
             * @param "" ""值
             * @return 处理结果
             */
            "videoModel", trimmed(request.videoModel(), ""),
            /**
             * 处理trimmed。
             * @param request.imageModel( request.imageModel(值
             * @param "" ""值
             * @return 处理结果
             */
            "imageModel", trimmed(request.imageModel(), ""),
            /**
             * 处理trimmed。
             * @param request.textAnalysisModel( request.text分析Model(值
             * @param "" ""值
             * @return 处理结果
             */
            "textAnalysisModel", trimmed(request.textAnalysisModel(), ""),
            /**
             * 处理trimmed。
             * @param request.visionModel( request.visionModel(值
             * @param "" ""值
             * @return 处理结果
             */
            "visionModel", trimmed(request.visionModel(), "")
        ));
        executionCoordinator.recordTrace(task, TaskStage.API.code(), "task.created", "生成任务已创建。", TraceLevel.INFO.value(), Map.of(
            "task_type", "generation",
            "taskSeed", task.taskSeed() == null ? "" : task.taskSeed(),
            "outputCount", task.requestSnapshot().outputCount().toValue(),
            "artifactBaseRelativeDir", TaskArtifactNaming.taskBaseRelativeDir(task),
            "artifactRunningRelativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
            "artifactJoinedRelativeDir", TaskArtifactNaming.taskJoinedRelativeDir(task),
            "storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md")
        ));
        executionCoordinator.enqueue(task, TaskStage.DISPATCH.code(), "task.enqueued", "任务已进入队列，等待 Spring 后端任务执行器接管。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    /**
     * 重试重试。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public TaskRecord retry(TaskRecord task) {
        task.setRetryCount(task.retryCount() + 1);
        task.setErrorMessage("");
        executionCoordinator.createAttempt(task, AttemptTriggerType.RETRY, buildRetryPayload(task, AttemptTriggerType.RETRY));
        executionCoordinator.enqueue(task, TaskStage.DISPATCH.code(), "task.retry_requested", "任务已重新加入队列。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    /**
     * 暂停pause。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public TaskRecord pause(TaskRecord task) {
        executionCoordinator.dequeue(task);
        task.setQueued(false);
        task.setQueuePosition(null);
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.info(
                TaskStatus.PAUSED,
                task.progress(),
                TaskStage.API.code(),
                "task.paused",
                "任务已暂停。",
                Map.of("reason", "manual")
            ).withAttempt(AttemptStatus.PAUSED, "")
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    /**
     * 恢复resume。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public TaskRecord resume(TaskRecord task) {
        executionCoordinator.createAttempt(task, AttemptTriggerType.CONTINUE, buildRetryPayload(task, AttemptTriggerType.CONTINUE));
        executionCoordinator.enqueue(task, TaskStage.DISPATCH.code(), "task.continue_requested", "任务已继续执行。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    /**
     * 终止terminate。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public TaskRecord terminate(TaskRecord task) {
        executionCoordinator.dequeue(task);
        task.setQueued(false);
        task.setQueuePosition(null);
        String errorMessage = "任务已手动终止。";
        executionCoordinator.transitionTask(
            task,
            TaskStateTransition.warn(
                TaskStatus.FAILED,
                task.progress(),
                TaskStage.API.code(),
                "task.terminated",
                "任务已终止。",
                Map.of("reason", "manual")
            ).withAttempt(AttemptStatus.TERMINATED, errorMessage),
            currentTask -> {
                currentTask.setErrorMessage(errorMessage);
                currentTask.setFinishedAt(currentTask.nowIso());
            }
        );
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return task;
    }

    /**
     * 处理评分效果。
     * @param task 要处理的任务对象
     * @param request 请求体
     * @return 处理结果
     */
    public TaskRecord rateEffect(TaskRecord task, RateTaskEffectRequest request) {
        int effectRating = normalizeEffectRating(request.effectRating());
        String effectRatingNote = normalizeEffectRatingNote(request.effectRatingNote());
        task.setEffectRating(effectRating);
        task.setEffectRatingNote(effectRatingNote);
        task.setRatedAt(task.nowIso());
        task.mutableExecutionContext().put("effectRating", effectRating);
        task.mutableExecutionContext().put("effectRatingNote", effectRatingNote);
        task.mutableExecutionContext().put("ratedAt", task.ratedAt());
        taskRepository.save(task);
        executionCoordinator.recordTrace(task, TaskStage.FEEDBACK.code(), "task.effect_rated", "任务效果评分已更新。", "INFO", Map.of(
            "effectRating", effectRating,
            "effectRatingNote", effectRatingNote,
            "taskSeed", task.taskSeed() == null ? "" : task.taskSeed()
        ));
        return task;
    }

    /**
     * 删除删除。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Map<String, Object> delete(TaskRecord task) {
        executionCoordinator.dequeue(task);
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        taskRepository.delete(task.id());
        return Map.of("taskId", task.id(), "deleted", true);
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
    private Map<String, Object> buildRetryPayload(TaskRecord task, AttemptTriggerType triggerType) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("triggerType", triggerType == null ? "" : triggerType.value());
        payload.put("retryCount", task.retryCount());
        List<Integer> clipIndices = existingVideoClipIndices(task);
        // 只允许从连续成功的最后一个镜头后继续，避免跳过缺失片段直接向后恢复。
        int completedClipCount = lastContiguousCompletedClipIndex(clipIndices);
        if (task.storyboardScript() != null && !task.storyboardScript().isBlank()) {
            // 已经有分镜脚本时优先复用规划结果；只有至少完成一镜时才直接从 render 阶段继续。
            payload.put("resumeFromStage", completedClipCount > 0 ? TaskStage.RENDER.code() : TaskStage.PLANNING.code());
            payload.put("resumeFromClipIndex", Math.max(1, completedClipCount + 1));
            payload.put("completedClipCount", completedClipCount);
            payload.put("existingClipIndices", clipIndices);
            payload.put("reuseStoryboard", true);
        }
        return payload;
    }

    /**
     * 处理existing视频片段Indices。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Integer> existingVideoClipIndices(TaskRecord task) {
        LinkedHashSet<Integer> indices = new LinkedHashSet<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.getOrDefault("resultType", ""))) {
                continue;
            }
            Integer clipIndex = integerValue(output.get("clipIndex"));
            if (clipIndex != null && clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        return indices.stream().sorted().toList();
    }

    /**
     * 处理lastContiguousCompleted片段索引。
     * @param clipIndices 片段Indices值
     * @return 处理结果
     */
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

    /**
     * 处理integer值。
     * @param value 待处理的值
     * @return 处理结果
     */
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

    /**
     * 处理validate生成任务请求。
     * @param request 请求体
     */
    private void validateGenerationTaskRequest(CreateGenerationTaskRequest request) {
        requireSelectedModel(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireSelectedModel(request.visionModel(), "visionModel", "视觉模型");
        requireSelectedModel(request.imageModel(), "imageModel", "关键帧模型");
        requireSelectedModel(request.videoModel(), "videoModel", "视频模型");
        normalizeOptionalSeed(request.seed());
        normalizeOutputCount(request.outputCount());
    }

    /**
     * 规范化Optional种子。
     * @param seed 种子值
     * @return 处理结果
     */
    private Integer normalizeOptionalSeed(Integer seed) {
        if (seed == null) {
            return null;
        }
        if (seed < 0) {
            throw new IllegalArgumentException("seed 不能小于 0");
        }
        return seed;
    }

    /**
     * 规范化输出数量。
     * @param outputCount 输出数量值
     * @return 处理结果
     */
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

    /**
     * 规范化效果评分。
     * @param effectRating 效果评分值
     * @return 处理结果
     */
    private int normalizeEffectRating(Integer effectRating) {
        if (effectRating == null) {
            throw new IllegalArgumentException("effectRating 不能为空");
        }
        if (effectRating < 1 || effectRating > 5) {
            throw new IllegalArgumentException("effectRating 必须在 1 到 5 之间");
        }
        return effectRating;
    }

    /**
     * 规范化效果评分Note。
     * @param note note值
     * @return 处理结果
     */
    private String normalizeEffectRatingNote(String note) {
        String normalized = trimmed(note, "");
        if (normalized.length() > 1000) {
            throw new IllegalArgumentException("effectRatingNote 不能超过 1000 个字符");
        }
        return normalized;
    }

    /**
     * 处理requireSelected模型。
     * @param value 待处理的值
     * @param fieldName fieldName值
     * @param label 标签值
     * @return 处理结果
     */
    private String requireSelectedModel(String value, String fieldName, String label) {
        String normalized = trimmed(value, "");
        if (!normalized.isBlank()) {
            return normalized;
        }
        throw new IllegalArgumentException("请先选择" + label + "（" + fieldName + "）");
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
