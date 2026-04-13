package com.jiandou.api.task;

import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.RemoteMediaGenerationClient;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.task.application.TaskApplicationService;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;

@Service
public class TaskApplicationServiceImpl implements TaskApplicationService {

    private final TaskRepository taskRepository;
    private final TaskViewMapper taskViewMapper;
    private final TaskExecutionCoordinator executionCoordinator;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final RemoteMediaGenerationClient remoteMediaGenerationClient;
    private final Path storageRoot;

    public TaskApplicationServiceImpl(
        TaskRepository taskRepository,
        TaskViewMapper taskViewMapper,
        TaskExecutionCoordinator executionCoordinator,
        ModelRuntimePropertiesResolver modelResolver,
        RemoteMediaGenerationClient remoteMediaGenerationClient,
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot
    ) {
        this.taskRepository = taskRepository;
        this.taskViewMapper = taskViewMapper;
        this.executionCoordinator = executionCoordinator;
        this.modelResolver = modelResolver;
        this.remoteMediaGenerationClient = remoteMediaGenerationClient;
        this.storageRoot = Paths.get(storageRoot).toAbsolutePath().normalize();
    }

    public Map<String, Object> createGenerationTask(TaskController.CreateGenerationTaskRequest request) {
        validateGenerationTaskRequest(request);
        String defaultPlatform = modelResolver.value("platform.defaults", "default_platform", "douyin");
        String platform = trimmed(request.platform(), defaultPlatform);
        String platformSection = "platform.platforms." + platform;
        int defaultDurationSeconds = modelResolver.intValue(
            platformSection,
            "default_video_duration_seconds",
            modelResolver.intValue("catalog.defaults", "video_duration_seconds", 8)
        );
        String taskId = "task_" + UUID.randomUUID().toString().replace("-", "");
        TaskRecord task = new TaskRecord();
        task.id = taskId;
        task.title = trimmed(request.title(), "未命名任务");
        task.status = "PENDING";
        task.platform = platform;
        task.progress = 0;
        task.createdAt = nowIso();
        task.updatedAt = task.createdAt;
        task.sourceFileName = "text_prompt";
        task.aspectRatio = trimmed(
            request.aspectRatio(),
            modelResolver.value(platformSection, "default_aspect_ratio", modelResolver.value("platform.defaults", "default_aspect_ratio", "9:16"))
        );
        task.minDurationSeconds = request.minDurationSeconds() != null ? request.minDurationSeconds() : defaultDurationSeconds;
        task.maxDurationSeconds = request.maxDurationSeconds() != null ? request.maxDurationSeconds() : defaultDurationSeconds;
        task.retryCount = 0;
        task.completedOutputCount = 0;
        task.hasTranscript = request.transcriptText() != null && !request.transcriptText().isBlank();
        task.hasTimedTranscript = false;
        task.sourceAssetCount = 0;
        task.editingMode = modelResolver.value("platform.defaults", "default_editing_mode", "drama");
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
        task.requestSnapshot = buildRequestSnapshot(request, task);
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
            "outputCount", task.requestSnapshot.getOrDefault("outputCount", "auto"),
            "artifactBaseRelativeDir", TaskArtifactNaming.taskBaseRelativeDir(task),
            "artifactRunningRelativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
            "artifactJoinedRelativeDir", TaskArtifactNaming.taskJoinedRelativeDir(task),
            "storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md")
        ));
        executionCoordinator.enqueue(task, "dispatch", "task.enqueued", "任务已进入队列，等待 Spring 后端任务执行器接管。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> generateCreativePrompt(TaskController.GenerateCreativePromptRequest request) {
        String title = trimmed(request.title(), "未命名任务");
        String prompt = "短剧风格，情绪递进，人物表情贴合语境，镜头写实，台词和配音语气符合剧情：" + title;
        return Map.of(
            "prompt", prompt,
            "source", "spring-default"
        );
    }

    public List<Map<String, Object>> listTasks(String q, String status, String platform, String sort) {
        List<TaskRecord> tasks = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(tasks);
        return tasks.stream()
            .sorted(taskComparator(sort))
            .filter(item -> q == null || q.isBlank() || containsIgnoreCase(item.title, q) || containsIgnoreCase(item.creativePrompt, q))
            .filter(item -> status == null || status.isBlank() || Objects.equals(item.status, status))
            .filter(item -> platform == null || platform.isBlank() || Objects.equals(item.platform, platform))
            .map(taskViewMapper::toListItem)
            .collect(Collectors.toList());
    }

    public Map<String, Object> getTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        executionCoordinator.recomputeQueuePositions(List.of(task));
        return taskViewMapper.toDetail(task);
    }

    public List<Map<String, Object>> getTrace(String taskId, int limit) {
        return tail(requireTask(taskId).trace, limit);
    }

    public List<Map<String, Object>> getLogs(String taskId, int limit) {
        return getTrace(taskId, limit);
    }

    public List<Map<String, Object>> getStatusHistory(String taskId, int limit) {
        return tail(requireTask(taskId).statusHistory, limit);
    }

    public List<Map<String, Object>> getModelCalls(String taskId, int limit) {
        return tail(requireTask(taskId).modelCalls, limit);
    }

    public List<Map<String, Object>> getResults(String taskId) {
        return new ArrayList<>(requireTask(taskId).outputs);
    }

    public List<Map<String, Object>> getMaterials(String taskId) {
        return new ArrayList<>(requireTask(taskId).materials);
    }

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

    public Map<String, Object> retryTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        task.retryCount += 1;
        task.errorMessage = "";
        executionCoordinator.createAttempt(task, "retry", buildRetryPayload(task, "retry"));
        executionCoordinator.enqueue(task, "dispatch", "task.retry_requested", "任务已重新加入队列。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> pauseTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        String previousStatus = task.status;
        executionCoordinator.dequeue(task);
        task.status = "PAUSED";
        task.isQueued = false;
        task.queuePosition = null;
        executionCoordinator.markActiveAttemptFinished(task, "PAUSED", "");
        executionCoordinator.recordTrace(task, "api", "task.paused", "任务已暂停。", "INFO", Map.of("reason", "manual"));
        executionCoordinator.recordStatusHistory(task, previousStatus, "PAUSED", "api", "task.paused", "任务已暂停。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> continueTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        executionCoordinator.createAttempt(task, "continue", buildRetryPayload(task, "continue"));
        executionCoordinator.enqueue(task, "dispatch", "task.continue_requested", "任务已继续执行。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> terminateTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        String previousStatus = task.status;
        executionCoordinator.dequeue(task);
        task.status = "FAILED";
        task.isQueued = false;
        task.queuePosition = null;
        task.errorMessage = "任务已手动终止。";
        task.finishedAt = nowIso();
        executionCoordinator.markActiveAttemptFinished(task, "TERMINATED", task.errorMessage);
        executionCoordinator.recordTrace(task, "api", "task.terminated", "任务已终止。", "WARN", Map.of("reason", "manual"));
        executionCoordinator.recordStatusHistory(task, previousStatus, "FAILED", "api", "task.terminated", "任务已终止。");
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> rateTaskEffect(String taskId, TaskController.RateTaskEffectRequest request) {
        TaskRecord task = requireTask(taskId);
        int effectRating = normalizeEffectRating(request.effectRating());
        String effectRatingNote = normalizeEffectRatingNote(request.effectRatingNote());
        task.effectRating = effectRating;
        task.effectRatingNote = effectRatingNote;
        task.ratedAt = nowIso();
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
        return taskViewMapper.toDetail(task);
    }

    public Map<String, Object> deleteTask(String taskId) {
        TaskRecord task = requireTask(taskId);
        executionCoordinator.dequeue(task);
        executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        taskRepository.delete(task.id);
        return Map.of("taskId", taskId, "deleted", true);
    }

    public Map<String, Object> adminOverview() {
        List<String> queueSnapshot = executionCoordinator.queueSnapshot();
        List<TaskRecord> values = new ArrayList<>(taskRepository.findAll());
        executionCoordinator.recomputeQueuePositions(values);
        values = values.stream()
            .sorted(Comparator.comparing((TaskRecord item) -> item.createdAt).reversed())
            .toList();
        int total = values.size();
        List<Map<String, Object>> recentTasks = values.stream().limit(8).map(taskViewMapper::toListItem).toList();
        List<Map<String, Object>> recentFailures = values.stream()
            .filter(item -> "FAILED".equals(item.status))
            .limit(6)
            .map(taskViewMapper::toListItem)
            .toList();
        List<Map<String, Object>> recentRunning = values.stream()
            .filter(item -> List.of("ANALYZING", "PLANNING", "RENDERING").contains(item.status))
            .limit(6)
            .map(taskViewMapper::toListItem)
            .toList();
        Map<String, Object> payload = new LinkedHashMap<>();
        List<Map<String, Object>> listItems = values.stream().map(taskViewMapper::toListItem).toList();
        payload.put("generatedAt", nowIso());
        payload.put("counts", Map.of(
            "totalTasks", total,
            "queuedTasks", queueSnapshot.size(),
            "runningTasks", values.stream().mapToInt(item -> List.of("ANALYZING", "PLANNING", "RENDERING").contains(item.status) ? 1 : 0).sum(),
            "completedTasks", values.stream().mapToInt(item -> "COMPLETED".equals(item.status) ? 1 : 0).sum(),
            "failedTasks", values.stream().mapToInt(item -> "FAILED".equals(item.status) ? 1 : 0).sum(),
            "highRiskTasks", listItems.stream().mapToInt(item -> "high".equals(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "riskyTasks", listItems.stream().mapToInt(item -> List.of("high", "medium").contains(String.valueOf(item.getOrDefault("diagnosisSeverity", ""))) ? 1 : 0).sum(),
            "semanticTasks", values.stream().mapToInt(item -> item.hasTranscript ? 1 : 0).sum(),
            "timedSemanticTasks", values.stream().mapToInt(item -> item.hasTimedTranscript ? 1 : 0).sum(),
            "averageProgress", total == 0 ? 0 : values.stream().mapToInt(item -> item.progress).sum() / total
        ));
        payload.put("queue", adminQueueOverview(50));
        payload.put("workers", Map.of(
            "items", adminWorkers(20),
            "onlineCount", taskRepository.listWorkerInstances(200).stream()
                .map(item -> String.valueOf(item.getOrDefault("status", "")))
                .filter(statusValue -> "RUNNING".equalsIgnoreCase(statusValue))
                .count()
        ));
        payload.put("modelReady",
            !modelResolver.listModelsByKind("text").isEmpty()
                && !modelResolver.listModelsByKind("vision").isEmpty()
                && !modelResolver.listModelsByKind("image").isEmpty()
                && !modelResolver.listModelsByKind("video").isEmpty()
        );
        payload.put("primaryModel", null);
        payload.put("textModel", null);
        payload.put("visionModel", null);
        payload.put("recentTasks", recentTasks);
        payload.put("recentFailures", recentFailures);
        payload.put("recentRunningTasks", recentRunning);
        payload.put("recentTraceCount", taskRepository.listTraces(null, null, null, null, 1000).size());
        return payload;
    }

    public List<Map<String, Object>> adminTraces(String taskId, String stage, String level, String q, int limit) {
        int resolvedLimit = Math.max(1, limit);
        Map<String, TaskRecord> tasks = taskRepository.findAll().stream()
            .collect(Collectors.toMap(item -> item.id, item -> item, (left, right) -> left, LinkedHashMap::new));
        return taskRepository.listTraces(taskId, stage, level, q, resolvedLimit).stream()
            .map(trace -> {
                Map<String, Object> row = new LinkedHashMap<>(trace);
                TaskRecord task = tasks.get(String.valueOf(trace.getOrDefault("taskId", "")));
                row.put("taskTitle", task == null ? "" : task.title);
                row.put("taskStatus", task == null ? "" : task.status);
                return row;
            })
            .toList();
    }

    public List<Map<String, Object>> adminWorkers(int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listWorkerInstances(resolvedLimit);
    }

    public Map<String, Object> adminWorker(String workerInstanceId) {
        Map<String, Object> item = taskRepository.findWorkerInstance(workerInstanceId);
        if (item == null || item.isEmpty()) {
            throw new TaskNotFoundException(workerInstanceId);
        }
        return item;
    }

    public List<Map<String, Object>> adminQueueEvents(String taskId, int limit) {
        int resolvedLimit = Math.max(1, limit);
        return taskRepository.listQueueEvents(taskId, resolvedLimit);
    }

    public Map<String, Object> adminQueueOverview(int limit) {
        int resolvedLimit = Math.max(1, limit);
        List<String> snapshot = executionCoordinator.queueSnapshot();
        List<Map<String, Object>> events = taskRepository.listQueueEvents(null, resolvedLimit);
        List<Map<String, Object>> workers = taskRepository.listWorkerInstances(200);
        long runningWorkers = workers.stream()
            .map(item -> String.valueOf(item.getOrDefault("status", "")))
            .filter(statusValue -> "RUNNING".equalsIgnoreCase(statusValue))
            .count();
        String oldestQueuedTaskId = snapshot.isEmpty() ? "" : snapshot.get(0);
        TaskRecord oldestQueuedTask = oldestQueuedTaskId.isBlank() ? null : taskRepository.findById(oldestQueuedTaskId);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", nowIso());
        payload.put("queueLength", snapshot.size());
        payload.put("queueSnapshot", snapshot);
        payload.put("runningWorkers", runningWorkers);
        payload.put("latestEvents", events);
        payload.put("oldestQueuedTaskId", oldestQueuedTaskId);
        payload.put("oldestQueuedTaskTitle", oldestQueuedTask == null ? "" : oldestQueuedTask.title);
        payload.put("oldestQueuedTaskCreatedAt", oldestQueuedTask == null ? null : oldestQueuedTask.createdAt);
        return payload;
    }

    public Map<String, Object> adminTaskDiagnosis(String taskId) {
        TaskRecord task = requireTask(taskId);
        Map<String, Object> detail = taskViewMapper.toDetail(task);
        Map<String, Object> monitoring = mapValue(detail.get("monitoring"));
        List<Integer> renderedClipIndices = existingVideoClipIndices(task);
        int plannedClipCount = intValue(monitoring.get("plannedClipCount"), 0);
        int contiguousRenderedClipCount = intValue(monitoring.get("contiguousRenderedClipCount"), 0);
        int latestRenderedClipIndex = intValue(monitoring.get("latestRenderedClipIndex"), 0);
        List<Integer> missingClipIndices = missingClipIndices(plannedClipCount, renderedClipIndices);
        Map<String, Object> latestJoinOutput = latestOutputOfKind(task, "video_join");
        Map<String, Object> latestVideoOutput = latestOutputOfKind(task, "video");
        Map<String, Object> latestVideoExtra = mapValue(latestVideoOutput.get("extra"));
        int joinCount = (int) task.outputsView().stream()
            .filter(item -> "video_join".equalsIgnoreCase(stringValue(item.get("resultType"))))
            .count();
        int videoClipCount = renderedClipIndices.size();
        boolean hasAudioClip = task.outputsView().stream()
            .filter(item -> "video".equalsIgnoreCase(stringValue(item.get("resultType"))))
            .anyMatch(item -> boolValue(mapValue(item.get("extra")).get("hasAudio")));

        List<Map<String, Object>> findings = new ArrayList<>();
        if ("FAILED".equals(task.status)) {
            findings.add(finding("task_failed", "high", "任务处于失败状态", firstNonBlank(task.errorMessage, "请检查最近一条 trace 和模型调用记录。")));
        }
        if ("PENDING".equals(task.status) && !task.isQueued) {
            findings.add(finding("pending_not_queued", "high", "任务状态为 PENDING 但未在队列中", "这通常说明 attempt/queue 状态不同步，需要重新入队或重试。"));
        }
        if (plannedClipCount > 0 && contiguousRenderedClipCount < plannedClipCount) {
            findings.add(finding("missing_clips", contiguousSeverity(task.status), "分镜输出未完整覆盖计划镜头", "已连续完成 " + contiguousRenderedClipCount + " / " + plannedClipCount + "，缺失镜头: " + missingClipIndices));
        }
        if (videoClipCount > 1 && joinCount == 0) {
            findings.add(finding("join_missing", "medium", "多镜头任务尚未产出拼接结果", "已有 " + videoClipCount + " 段片段，但没有 join 输出。"));
        }
        if (videoClipCount > 0 && !hasAudioClip) {
            findings.add(finding("audio_missing", "medium", "视频片段未检测到音轨", "请检查远端视频模型返回以及 generateAudio 参数。"));
        }
        if ("COMPLETED".equals(task.status) && plannedClipCount > 0 && videoClipCount < plannedClipCount) {
            findings.add(finding("completed_but_incomplete", "high", "任务标记完成但镜头未完整生成", "COMPLETED 状态与片段产物数量不一致。"));
        }
        if (findings.isEmpty()) {
            findings.add(finding("healthy", "info", "当前未发现明显阻塞", "任务状态、队列与分镜产物看起来基本一致。"));
        }

        String recommendedAction = recommendedAction(task, findings, contiguousRenderedClipCount, plannedClipCount);
        Map<String, Object> recovery = new LinkedHashMap<>();
        recovery.put("canRetry", !"RENDERING".equals(task.status) && !"ANALYZING".equals(task.status) && !"PLANNING".equals(task.status));
        recovery.put("recommendedAction", recommendedAction);
        recovery.put("resumeFromStage", monitoring.get("resumeFromStage"));
        recovery.put("resumeFromClipIndex", intValue(monitoring.get("resumeFromClipIndex"), Math.max(1, contiguousRenderedClipCount + 1)));

        Map<String, Object> continuity = new LinkedHashMap<>();
        continuity.put("plannedClipCount", plannedClipCount);
        continuity.put("renderedClipIndices", renderedClipIndices);
        continuity.put("contiguousRenderedClipCount", contiguousRenderedClipCount);
        continuity.put("missingClipIndices", missingClipIndices);
        continuity.put("latestRenderedClipIndex", latestRenderedClipIndex);
        continuity.put("latestJoinName", stringValue(monitoring.get("latestJoinName")));
        continuity.put("latestJoinClipIndex", intValue(monitoring.get("latestJoinClipIndex"), intValue(latestJoinOutput.get("clipIndex"), 0)));
        continuity.put("latestJoinClipIndices", listValue(monitoring.get("latestJoinClipIndices")));

        Map<String, Object> outputs = new LinkedHashMap<>();
        outputs.put("videoClipCount", videoClipCount);
        outputs.put("joinCount", joinCount);
        outputs.put("latestVideoOutputUrl", firstNonBlank(stringValue(monitoring.get("latestVideoOutputUrl")), stringValue(latestVideoOutput.get("downloadUrl"))));
        outputs.put("latestJoinOutputUrl", firstNonBlank(stringValue(monitoring.get("latestJoinOutputUrl")), stringValue(latestJoinOutput.get("downloadUrl"))));
        outputs.put("latestLastFrameUrl", stringValue(latestVideoExtra.get("lastFrameUrl")));
        outputs.put("hasAudioClip", hasAudioClip);

        Map<String, Object> queue = new LinkedHashMap<>();
        queue.put("isQueued", task.isQueued);
        queue.put("queuePosition", task.queuePosition);
        queue.put("activeAttemptStatus", monitoring.get("activeAttemptStatus"));
        queue.put("activeWorkerInstanceId", monitoring.get("activeWorkerInstanceId"));

        Map<String, Object> diagnosis = new LinkedHashMap<>();
        diagnosis.put("taskId", task.id);
        diagnosis.put("title", task.title);
        diagnosis.put("status", task.status);
        diagnosis.put("severity", highestSeverity(findings));
        diagnosis.put("summary", diagnosisSummary(task, findings, plannedClipCount, videoClipCount, joinCount));
        diagnosis.put("findings", findings);
        diagnosis.put("recovery", recovery);
        diagnosis.put("continuity", continuity);
        diagnosis.put("outputs", outputs);
        diagnosis.put("queue", queue);
        return diagnosis;
    }

    private Map<String, Object> buildRequestSnapshot(TaskController.CreateGenerationTaskRequest request, TaskRecord task) {
        String platformSection = "platform.platforms." + task.platform;
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("taskType", "generation");
        snapshot.put("title", task.title);
        snapshot.put("creativePrompt", task.creativePrompt);
        snapshot.put("platform", task.platform);
        snapshot.put("aspectRatio", task.aspectRatio);
        snapshot.put("stylePreset", firstNonBlank(
            modelResolver.value(platformSection, "default_style_preset", ""),
            modelResolver.value("platform.defaults", "default_style_preset", ""),
            modelResolver.value("catalog.defaults", "style_preset", "cinematic"),
            "cinematic"
        ));
        snapshot.put("textAnalysisModel", trimmed(request.textAnalysisModel(), ""));
        snapshot.put("visionModel", trimmed(request.visionModel(), ""));
        snapshot.put("imageModel", trimmed(request.imageModel(), ""));
        snapshot.put("videoModel", trimmed(request.videoModel(), ""));
        snapshot.put("videoSize", trimmed(
            request.videoSize(),
            modelResolver.value(platformSection, "default_video_size", modelResolver.value("catalog.defaults", "video_size", "720*1280"))
        ));
        snapshot.put("seed", task.taskSeed);
        snapshot.put("videoDurationSeconds", request.videoDurationSeconds());
        snapshot.put("outputCount", normalizeOutputCount(request.outputCount()));
        snapshot.put("minDurationSeconds", task.minDurationSeconds);
        snapshot.put("maxDurationSeconds", task.maxDurationSeconds);
        snapshot.put("transcriptText", task.transcriptText);
        snapshot.put("stopBeforeVideoGeneration", Boolean.TRUE.equals(request.stopBeforeVideoGeneration()));
        return snapshot;
    }

    private Map<String, Object> latestOutputOfKind(TaskRecord task, String resultType) {
        List<Map<String, Object>> outputs = task.outputsView().stream()
            .filter(item -> resultType.equalsIgnoreCase(stringValue(item.get("resultType"))))
            .sorted(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .toList();
        return outputs.isEmpty() ? Map.of() : outputs.get(outputs.size() - 1);
    }

    private List<Integer> missingClipIndices(int plannedClipCount, List<Integer> renderedClipIndices) {
        if (plannedClipCount <= 0) {
            return List.of();
        }
        LinkedHashSet<Integer> rendered = new LinkedHashSet<>(renderedClipIndices);
        List<Integer> missing = new ArrayList<>();
        for (int index = 1; index <= plannedClipCount; index++) {
            if (!rendered.contains(index)) {
                missing.add(index);
            }
        }
        return missing;
    }

    private Map<String, Object> finding(String code, String severity, String title, String detail) {
        Map<String, Object> finding = new LinkedHashMap<>();
        finding.put("code", code);
        finding.put("severity", severity);
        finding.put("title", title);
        finding.put("detail", detail);
        return finding;
    }

    private String highestSeverity(List<Map<String, Object>> findings) {
        int level = 0;
        String label = "info";
        for (Map<String, Object> finding : findings) {
            String severity = stringValue(finding.get("severity"));
            int current = switch (severity) {
                case "high" -> 3;
                case "medium" -> 2;
                case "low" -> 1;
                default -> 0;
            };
            if (current > level) {
                level = current;
                label = severity.isBlank() ? "info" : severity;
            }
        }
        return label;
    }

    private String diagnosisSummary(TaskRecord task, List<Map<String, Object>> findings, int plannedClipCount, int videoClipCount, int joinCount) {
        String highest = highestSeverity(findings);
        if ("high".equals(highest)) {
            return "任务存在高优先级异常，建议优先查看失败原因与恢复起点。";
        }
        if ("medium".equals(highest)) {
            return "任务主链已跑通，但存在产物完整性或拼接一致性风险。";
        }
        return "任务当前整体健康。计划镜头 " + plannedClipCount + "，视频片段 " + videoClipCount + "，拼接结果 " + joinCount + "。";
    }

    private String recommendedAction(TaskRecord task, List<Map<String, Object>> findings, int contiguousRenderedClipCount, int plannedClipCount) {
        if ("FAILED".equals(task.status)) {
            return contiguousRenderedClipCount > 0 ? "执行 retry，按已有分镜从失败镜头继续恢复。" : "执行 retry，重新从分析阶段开始。";
        }
        if ("PAUSED".equals(task.status)) {
            return "执行 continue，保持当前分镜进度继续生成。";
        }
        if (plannedClipCount > 1 && findings.stream().anyMatch(item -> "join_missing".equals(stringValue(item.get("code"))))) {
            return "检查 join worker trace，确认片段已连续落盘后重新触发 join。";
        }
        if ("PENDING".equals(task.status) && !task.isQueued) {
            return "重新 enqueue 当前任务，必要时直接 retry 创建新的 attempt。";
        }
        return "继续观察最新 trace 与 stage run，如长时间无进展再执行 retry。";
    }

    private void createArtifactDirectories(TaskRecord task) {
        try {
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskBaseRelativeDir(task)));
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskRunningRelativeDir(task)));
            Files.createDirectories(storageRoot.resolve(TaskArtifactNaming.taskJoinedRelativeDir(task)));
        } catch (IOException ex) {
            throw new IllegalStateException("任务产物目录创建失败: " + ex.getMessage(), ex);
        }
    }

    private String contiguousSeverity(String taskStatus) {
        return "COMPLETED".equals(taskStatus) || "FAILED".equals(taskStatus) ? "high" : "medium";
    }

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

    private void validateGenerationTaskRequest(TaskController.CreateGenerationTaskRequest request) {
        requireSelectedModel(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireSelectedModel(request.visionModel(), "visionModel", "视觉模型");
        requireSelectedModel(request.imageModel(), "imageModel", "关键帧模型");
        requireSelectedModel(request.videoModel(), "videoModel", "视频模型");
        normalizeOptionalSeed(request.seed());
        normalizeOutputCount(request.outputCount());
    }

    private Comparator<TaskRecord> taskComparator(String sort) {
        String normalizedSort = trimmed(sort, "updated_desc").toLowerCase();
        Comparator<TaskRecord> updatedDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.updatedAt),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        Comparator<TaskRecord> createdDesc = Comparator.comparing(
            (TaskRecord item) -> stringValue(item.createdAt),
            Comparator.nullsLast(String::compareTo)
        ).reversed();
        return switch (normalizedSort) {
            case "created_desc" -> createdDesc;
            case "progress_desc" -> Comparator.comparingInt((TaskRecord item) -> item.progress).reversed().thenComparing(updatedDesc);
            case "semantic_desc" -> Comparator.comparingInt(
                (TaskRecord item) -> item.hasTimedTranscript || item.hasTranscript ? 1 : 0
            ).reversed().thenComparing(updatedDesc);
            case "status_desc" -> Comparator.comparing((TaskRecord item) -> stringValue(item.status)).thenComparing(updatedDesc);
            case "effect_rating_desc", "rating_desc" -> Comparator
                .comparingInt((TaskRecord item) -> item.effectRating == null ? Integer.MIN_VALUE : item.effectRating)
                .reversed()
                .thenComparing(updatedDesc);
            default -> updatedDesc;
        };
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

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    @SuppressWarnings("unchecked")
    private List<Object> listValue(Object value) {
        if (value instanceof List<?> list) {
            return (List<Object>) list;
        }
        return List.of();
    }

    private int intValue(Object value, int fallback) {
        Integer resolved = integerValue(value);
        return resolved == null ? fallback : resolved;
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return "true".equalsIgnoreCase(stringValue(value));
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private List<Map<String, Object>> tail(List<Map<String, Object>> items, int limit) {
        if (limit <= 0 || items.isEmpty()) {
            return List.of();
        }
        int fromIndex = Math.max(0, items.size() - limit);
        return new ArrayList<>(items.subList(fromIndex, items.size()));
    }

    private TaskRecord requireTask(String taskId) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null) {
            throw new TaskNotFoundException(taskId);
        }
        return task;
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    private boolean containsIgnoreCase(String source, String query) {
        return source != null && source.toLowerCase().contains(query.toLowerCase());
    }

    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }

}
