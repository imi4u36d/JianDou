package com.jiandou.api.task.view;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.web.dto.TaskListItemResponse;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import com.jiandou.api.task.domain.TaskArtifactNaming;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStatus;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 负责把任务聚合对象转换为接口返回结构。
 * 当前阶段优先保持前端字段兼容，但内部已经开始收敛为更明确的视图对象。
 */
@Component
public class TaskViewMapper {

    private final Path storageRoot;
    private final LocalMediaArtifactService localMediaArtifactService;

    public TaskViewMapper(JiandouStorageProperties storageProperties) {
        this(storageProperties, null);
    }

    @Autowired
    public TaskViewMapper(JiandouStorageProperties storageProperties, LocalMediaArtifactService localMediaArtifactService) {
        this.storageRoot = storageProperties.resolveRootDir();
        this.localMediaArtifactService = localMediaArtifactService;
    }

    /**
     * 处理转为列表Item。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Map<String, Object> toListItem(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        TaskDiagnosisSummary diagnosis = diagnosisSummary(task, monitoring);
        FailureSummary failure = failureSummary(task);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", task.id());
        row.put("taskType", task.taskType());
        row.put("title", task.title());
        row.put("status", task.status());
        row.put("progress", task.progress());
        row.put("createdAt", task.createdAt());
        row.put("updatedAt", task.updatedAt());
        row.put("sourceFileName", task.sourceFileName());
        row.put("aspectRatio", task.aspectRatio());
        row.put("minDurationSeconds", task.minDurationSeconds());
        row.put("maxDurationSeconds", task.maxDurationSeconds());
        row.put("retryCount", task.retryCount());
        row.put("startedAt", task.startedAt());
        row.put("finishedAt", task.finishedAt());
        row.put("completedOutputCount", task.completedOutputCount());
        row.put("taskSeed", task.taskSeed());
        row.put("effectRating", task.effectRating());
        row.put("effectRatingNote", task.effectRatingNote());
        row.put("ratedAt", task.ratedAt());
        row.put("hasTranscript", task.hasTranscript());
        row.put("hasTimedTranscript", task.hasTimedTranscript());
        row.put("sourceAssetCount", task.sourceAssetCount());
        row.put("editingMode", task.editingMode());
        row.put("isQueued", task.isQueued());
        row.put("queuePosition", task.queuePosition());
        row.put("currentStage", monitoring.currentStage());
        row.put("activeWorkerInstanceId", monitoring.activeWorkerInstanceId());
        row.put("plannedClipCount", monitoring.plannedClipCount());
        row.put("renderedClipCount", monitoring.renderedClipCount());
        row.put("diagnosisSeverity", diagnosis.severity());
        row.put("diagnosisCode", diagnosis.code());
        row.put("diagnosisHint", diagnosis.hint());
        row.put("recommendedAction", diagnosis.recommendedAction());
        row.put("failureReason", failure.reason());
        row.put("failureStage", failure.stage());
        row.put("failureClipIndex", failure.clipIndex());
        row.put("thumbnailUrl", taskThumbnailUrl(task, monitoring));
        return row;
    }

    public TaskListItemResponse toListItemResponse(TaskRecord task, String ownerUserId, String ownerUsername, String ownerDisplayName, String ownerRole) {
        Map<String, Object> row = toListItem(task);
        return new TaskListItemResponse(
            (String) row.get("id"),
            (String) row.get("taskType"),
            (String) row.get("title"),
            (String) row.get("status"),
            (int) row.get("progress"),
            (String) row.get("createdAt"),
            (String) row.get("updatedAt"),
            (String) row.get("sourceFileName"),
            (String) row.get("aspectRatio"),
            (int) row.get("minDurationSeconds"),
            (int) row.get("maxDurationSeconds"),
            (int) row.get("retryCount"),
            (String) row.get("startedAt"),
            (String) row.get("finishedAt"),
            (int) row.get("completedOutputCount"),
            (Integer) row.get("taskSeed"),
            (Integer) row.get("effectRating"),
            (String) row.get("effectRatingNote"),
            (String) row.get("ratedAt"),
            (boolean) row.get("hasTranscript"),
            (boolean) row.get("hasTimedTranscript"),
            (int) row.get("sourceAssetCount"),
            (String) row.get("editingMode"),
            (boolean) row.get("isQueued"),
            (Integer) row.get("queuePosition"),
            (String) row.get("currentStage"),
            (String) row.get("activeWorkerInstanceId"),
            (int) row.get("plannedClipCount"),
            (int) row.get("renderedClipCount"),
            (String) row.get("diagnosisSeverity"),
            (String) row.get("diagnosisCode"),
            (String) row.get("diagnosisHint"),
            (String) row.get("recommendedAction"),
            (String) row.get("failureReason"),
            (String) row.get("failureStage"),
            (Integer) row.get("failureClipIndex"),
            (String) row.get("thumbnailUrl"),
            ownerUserId != null ? Long.parseLong(ownerUserId) : null,
            ownerUsername,
            ownerDisplayName,
            ownerRole
        );
    }

    /**
     * 返回适合官网与工作台案例区使用的任务摘要。
     * 该视图只保留公开展示必需字段，避免暴露完整任务上下文。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Map<String, Object> toShowcaseItem(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        Map<String, Object> latestJoinOutput = latestJoinOutput(task);
        Map<String, Object> latestVideoOutput = latestVideoOutput(task);
        Map<String, Object> preferredOutput = latestJoinOutput.isEmpty() ? latestVideoOutput : latestJoinOutput;
        Map<String, Object> outputExtra = mapValue(preferredOutput.get("extra"));
        String previewUrl = firstNonBlank(
            stringValue(preferredOutput.get("previewUrl")),
            stringValue(preferredOutput.get("downloadUrl")),
            monitoring.latestJoinOutputUrl(),
            monitoring.latestVideoOutputUrl()
        );
        String downloadUrl = firstNonBlank(
            stringValue(preferredOutput.get("downloadUrl")),
            stringValue(preferredOutput.get("previewUrl")),
            monitoring.latestJoinOutputUrl(),
            monitoring.latestVideoOutputUrl()
        );

        Map<String, Object> media = new LinkedHashMap<>();
        media.put("title", firstNonBlank(stringValue(preferredOutput.get("title")), monitoring.latestJoinName()));
        media.put("clipIndex", nullableInt(preferredOutput.get("clipIndex")));
        media.put("durationSeconds", nullableDouble(preferredOutput.get("durationSeconds")));
        media.put("width", nullableInt(preferredOutput.get("width")));
        media.put("height", nullableInt(preferredOutput.get("height")));
        media.put("hasAudio", outputExtra.containsKey("hasAudio") ? boolValue(outputExtra.get("hasAudio")) : null);

        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", task.id());
        row.put("title", task.title());
        row.put("status", task.status());
        row.put("createdAt", task.createdAt());
        row.put("updatedAt", task.updatedAt());
        row.put("sourceFileName", task.sourceFileName());
        row.put("aspectRatio", task.aspectRatio());
        row.put("minDurationSeconds", task.minDurationSeconds());
        row.put("maxDurationSeconds", task.maxDurationSeconds());
        row.put("completedOutputCount", task.completedOutputCount());
        row.put("taskSeed", task.taskSeed());
        row.put("effectRating", task.effectRating());
        row.put("description", showcaseDescription(task));
        row.put("previewUrl", previewUrl);
        row.put("downloadUrl", downloadUrl);
        row.put("joinName", monitoring.latestJoinName());
        row.put("models", showcaseModels(task));
        row.put("media", media);
        return row;
    }

    /**
     * 详情视图在列表字段基础上补充上下文、素材和运行信息。
     */
    public Map<String, Object> toDetail(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        FailureSummary failure = failureSummary(task);
        Map<String, Object> row = new LinkedHashMap<>(toListItem(task));
        row.put("artifactDirectories", monitoring.artifactDirectories().toMap());
        row.put("introTemplate", task.introTemplate());
        row.put("outroTemplate", task.outroTemplate());
        row.put("creativePrompt", task.creativePrompt());
        row.put("taskSeed", task.taskSeed());
        row.put("effectRating", task.effectRating());
        row.put("effectRatingNote", task.effectRatingNote());
        row.put("ratedAt", task.ratedAt());
        row.put("errorMessage", task.errorMessage());
        row.put("failureReason", failure.reason());
        row.put("failureStage", failure.stage());
        row.put("failureClipIndex", failure.clipIndex());
        row.put("transcriptPreview", transcriptPreview(task.transcriptText()));
        row.put("transcriptCueCount", 0);
        row.put("source", null);
        row.put("sourceAssets", task.sourceAssetsView().stream().map(this::withSourceAssetThumbnail).toList());
        row.put("storyboardScript", task.storyboardScript());
        row.put("materials", task.materialsView().stream().map(this::withMaterialThumbnail).toList());
        row.put("executionContext", task.executionContext());
        row.put("requestSnapshot", task.requestSnapshot() == null ? Map.of() : task.requestSnapshot().toMap());
        row.put("durationDiagnostics", durationDiagnostics(task));
        row.put("sourceAssetIds", List.of());
        row.put("sourceFileNames", List.of());
        row.put("plan", List.of());
        row.put("activeAttemptId", task.activeAttemptId());
        row.put("attempts", task.attempts());
        row.put("stageRuns", task.stageRuns());
        row.put("outputs", task.outputsView().stream().map(this::withOutputThumbnail).toList());
        row.put("monitoring", monitoring.toMap(true));
        return row;
    }

    /**
     * 处理诊断摘要。
     * @param task 要处理的任务对象
     * @param monitoring 监控值
     * @return 处理结果
     */
    private TaskDiagnosisSummary diagnosisSummary(TaskRecord task, TaskMonitoringSnapshot monitoring) {
        int plannedClipCount = monitoring.plannedClipCount();
        int renderedClipCount = monitoring.renderedClipCount();
        int contiguousRenderedClipCount = monitoring.contiguousRenderedClipCount();
        int joinClipIndex = monitoring.latestJoinClipIndex();
        boolean hasAudioClip = task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .anyMatch(item -> boolValue(mapValue(item.get("extra")).get("hasAudio")));
        if (TaskStatus.FAILED.matches(task.status())) {
            return diagnosis("high", "task_failed", "任务已失败，建议查看诊断并执行恢复重试。", contiguousRenderedClipCount > 0
                ? "从失败镜头继续 retry"
                : "从分析阶段重新 retry");
        }
        if (TaskStatus.PENDING.matches(task.status()) && !task.isQueued()) {
            return diagnosis("high", "pending_not_queued", "任务处于 PENDING，但当前未在队列中。", "重新 enqueue 或 retry");
        }
        if (TaskStatus.COMPLETED.matches(task.status()) && plannedClipCount > 0 && renderedClipCount < plannedClipCount) {
            return diagnosis("high", "completed_but_incomplete", "任务标记完成，但镜头产物数量不完整。", "核对丢失镜头并执行恢复");
        }
        if (plannedClipCount > 0 && contiguousRenderedClipCount < plannedClipCount) {
            return diagnosis("medium", "missing_clips", "镜头输出未完整覆盖计划分镜。", "从缺失镜头继续恢复");
        }
        if (renderedClipCount > 1 && joinClipIndex == 0) {
            return diagnosis("medium", "join_missing", "多镜头已生成，但还没有拼接结果。", "检查 join worker 或重新触发 join");
        }
        if (renderedClipCount > 0 && !hasAudioClip) {
            return diagnosis("medium", "audio_missing", "视频片段未检测到音轨。", "检查 generateAudio 参数与上游返回");
        }
        return diagnosis("info", "healthy", "当前未发现明显阻塞。", "继续观察");
    }

    /**
     * 处理诊断。
     * @param severity severity值
     * @param code code值
     * @param hint 提示值
     * @param recommendedAction recommendedAction值
     * @return 处理结果
     */
    private TaskDiagnosisSummary diagnosis(String severity, String code, String hint, String recommendedAction) {
        return new TaskDiagnosisSummary(severity, code, hint, recommendedAction);
    }

    /**
     * 监控快照内部先转成强类型对象，再在出参边界回写为 Map，减少字符串键名散落。
     */
    private TaskMonitoringSnapshot monitoringSummary(TaskRecord task) {
        Map<String, Object> activeAttempt = activeAttempt(task);
        Map<String, Object> latestTrace = latestByTimestamp(task.traceView(), "timestamp");
        Map<String, Object> latestStageRun = latestStageRun(task);
        Map<String, Object> latestVideoOutput = latestVideoOutput(task);
        Map<String, Object> latestJoinOutput = latestJoinOutput(task);
        int plannedClipCount = resolvePlannedClipCount(task);
        List<Integer> renderedClipIndices = renderedClipIndices(task);
        Map<String, Object> attemptPayload = mapValue(activeAttempt.get("payload"));
        return new TaskMonitoringSnapshot(
            currentStage(task, activeAttempt, latestStageRun, latestTrace),
            stringValue(activeAttempt.get("status")),
            firstNonBlank(
                stringValue(activeAttempt.get("workerInstanceId")),
                stringValue(task.executionContext().get("workerInstanceId")),
                stringValue(latestStageRun.get("workerInstanceId")),
                stringValue(latestTrace.get("workerInstanceId"))
            ),
            firstNonBlank(
                stringValue(activeAttempt.get("resumeFromStage")),
                stringValue(attemptPayload.get("resumeFromStage")),
                stringValue(task.executionContext().get("attemptResumeFromStage"))
            ),
            intValue(
                firstPresent(
                    activeAttempt.get("resumeFromClipIndex"),
                    attemptPayload.get("resumeFromClipIndex"),
                    task.executionContext().get("attemptResumeFromClipIndex")
                ),
                0
            ),
            plannedClipCount,
            renderedClipIndices.size(),
            contiguousClipCount(renderedClipIndices),
            renderedClipIndices.isEmpty() ? 0 : renderedClipIndices.get(renderedClipIndices.size() - 1),
            firstNonBlank(stringValue(latestVideoOutput.get("downloadUrl")), stringValue(latestVideoOutput.get("previewUrl"))),
            firstNonBlank(stringValue(task.executionContext().get("latestJoinName")), stringValue(mapValue(latestJoinOutput.get("extra")).get("joinName"))),
            firstNonBlank(stringValue(task.executionContext().get("latestJoinOutputUrl")), stringValue(latestJoinOutput.get("downloadUrl"))),
            intValue(task.executionContext().get("latestJoinClipIndex"), intValue(latestJoinOutput.get("clipIndex"), 0)),
            listValue(task.executionContext().get("latestJoinClipIndices")),
            stringValue(task.executionContext().get("storyboardFileUrl")),
            artifactDirectories(task),
            latestTrace,
            latestStageRun,
            latestVideoOutput,
            latestJoinOutput,
            renderedClipIndices
        );
    }

    /**
     * 处理产物Directories。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private TaskArtifactDirectories artifactDirectories(TaskRecord task) {
        return new TaskArtifactDirectories(
            storageRoot.resolve(TaskArtifactNaming.taskBaseRelativeDir(task)).toString(),
            storageRoot.resolve(TaskArtifactNaming.taskRunningRelativeDir(task)).toString(),
            storageRoot.resolve(TaskArtifactNaming.taskJoinedRelativeDir(task)).toString()
        );
    }

    /**
     * 处理active尝试。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId() == null || task.activeAttemptId().isBlank()) {
            return latestAttempt(task);
        }
        for (Map<String, Object> item : task.attemptsView()) {
            if (task.activeAttemptId().equals(stringValue(item.get("attemptId")))) {
                return item;
            }
        }
        return latestAttempt(task);
    }

    /**
     * 处理latestBy时间戳。
     * @param rows 行值
     * @param fieldName fieldName值
     * @return 处理结果
     */
    private Map<String, Object> latestByTimestamp(List<Map<String, Object>> rows, String fieldName) {
        return rows.stream()
            .max(Comparator.comparing(item -> stringValue(item.get(fieldName))))
            .orElse(Map.of());
    }

    /**
     * 处理latest尝试。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestAttempt(TaskRecord task) {
        return task.attemptsView().stream()
            .max(Comparator.comparing(this::attemptSortKey))
            .orElse(Map.of());
    }

    /**
     * 处理尝试SortKey。
     * @param item item值
     * @return 处理结果
     */
    private String attemptSortKey(Map<String, Object> item) {
        return firstNonBlank(
            stringValue(item.get("finishedAt")),
            stringValue(item.get("startedAt")),
            stringValue(item.get("claimedAt")),
            stringValue(item.get("queueEnteredAt"))
        );
    }

    /**
     * 处理latest阶段运行。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestStageRun(TaskRecord task) {
        return task.stageRunsView().stream()
            .max(Comparator.comparing(this::stageRunSortKey))
            .orElse(Map.of());
    }

    /**
     * 处理latest失败阶段运行。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestFailedStageRun(TaskRecord task) {
        return task.stageRunsView().stream()
            .filter(item -> !stringValue(item.get("errorMessage")).isBlank() || "FAILED".equalsIgnoreCase(stringValue(item.get("status"))))
            .max(Comparator.comparing(this::stageRunSortKey))
            .orElse(Map.of());
    }

    /**
     * 处理latest错误追踪。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestErrorTrace(TaskRecord task) {
        return task.traceView().stream()
            .filter(item -> {
                String level = stringValue(item.get("level"));
                return "ERROR".equalsIgnoreCase(level) || "WARN".equalsIgnoreCase(level);
            })
            .max(Comparator.comparing(item -> stringValue(item.get("timestamp"))))
            .orElse(Map.of());
    }

    /**
     * 处理阶段运行SortKey。
     * @param stageRun 阶段运行值
     * @return 处理结果
     */
    private String stageRunSortKey(Map<String, Object> stageRun) {
        return firstNonBlank(
            stringValue(stageRun.get("finishedAt")),
            stringValue(stageRun.get("updatedAt")),
            stringValue(stageRun.get("startedAt")),
            stringValue(stageRun.get("createdAt"))
        );
    }

    /**
     * 处理latest视频输出。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestVideoOutput(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .max(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .orElse(Map.of());
    }

    /**
     * 处理latest拼接输出。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> latestJoinOutput(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isJoinResultType(item.get("resultType")))
            .max(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .orElse(Map.of());
    }

    private String taskThumbnailUrl(TaskRecord task, TaskMonitoringSnapshot monitoring) {
        String imageUrl = firstNonBlank(
            stringValue(task.executionContext().get("latestImageOutputUrl")),
            imageMaterialUrl(task),
            imageOutputUrl(task)
        );
        if (!imageUrl.isBlank()) {
            return mediaThumbnailOrOriginal("image", imageUrl, List.of());
        }
        Map<String, Object> latestVideoOutput = latestVideoOutput(task);
        String videoUrl = firstNonBlank(
            stringValue(task.executionContext().get("videoOutputUrl")),
            stringValue(latestVideoOutput.get("previewUrl")),
            stringValue(latestVideoOutput.get("downloadUrl")),
            monitoring.latestVideoOutputUrl()
        );
        String videoCoverUrl = videoCoverUrl(task, monitoring);
        if (!videoUrl.isBlank()) {
            return mediaThumbnailOrOriginal("video", videoUrl, List.of(videoCoverUrl));
        }
        return mediaThumbnailOrOriginal("image", videoCoverUrl, List.of());
    }

    private String imageMaterialUrl(TaskRecord task) {
        return task.materialsView().stream()
            .filter(item -> "image".equalsIgnoreCase(stringValue(item.get("mediaType"))))
            .map(item -> firstNonBlank(stringValue(item.get("thumbnailUrl")), stringValue(item.get("previewUrl")), stringValue(item.get("fileUrl"))))
            .filter(item -> !item.isBlank())
            .findFirst()
            .orElse("");
    }

    private String imageOutputUrl(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isImageResultType(item.get("resultType")))
            .map(item -> firstNonBlank(
                stringValue(item.get("thumbnailUrl")),
                stringValue(mapValue(item.get("extra")).get("thumbnailUrl")),
                stringValue(item.get("previewUrl")),
                stringValue(item.get("downloadUrl"))
            ))
            .filter(item -> !item.isBlank())
            .findFirst()
            .orElse("");
    }

    private String videoCoverUrl(TaskRecord task, TaskMonitoringSnapshot monitoring) {
        Map<String, Object> latestVideoExtra = mapValue(monitoring.latestVideoOutput().get("extra"));
        return firstNonBlank(
            stringValue(task.executionContext().get("videoThumbnailUrl")),
            stringValue(latestVideoExtra.get("thumbnailUrl")),
            stringValue(latestVideoExtra.get("posterUrl")),
            stringValue(latestVideoExtra.get("firstFrameUrl")),
            stringValue(task.executionContext().get("firstFrameUrl"))
        );
    }

    private String thumbnailOrOriginal(String publicUrl) {
        return mediaThumbnailOrOriginal("image", publicUrl, List.of());
    }

    private String mediaThumbnailOrOriginal(String mediaType, String publicUrl, List<String> candidateImageUrls) {
        if (publicUrl == null || publicUrl.isBlank()) {
            return "";
        }
        if (localMediaArtifactService == null) {
            return publicUrl;
        }
        String thumbnailUrl = stringValue(localMediaArtifactService.ensureMediaThumbnail(mediaType, publicUrl, candidateImageUrls, 480));
        return thumbnailUrl.isBlank() ? publicUrl : thumbnailUrl;
    }

    private Map<String, Object> withMaterialThumbnail(Map<String, Object> material) {
        Map<String, Object> row = new LinkedHashMap<>(material);
        String mediaType = stringValue(row.get("mediaType"));
        String thumbnailUrl = mediaThumbnailOrOriginal(
            mediaType,
            firstNonBlank(stringValue(row.get("previewUrl")), stringValue(row.get("fileUrl"))),
            materialThumbnailCandidates(row)
        );
        if (!thumbnailUrl.isBlank()) {
            row.put("thumbnailUrl", thumbnailUrl);
        } else {
            row.putIfAbsent("thumbnailUrl", "");
        }
        return row;
    }

    private Map<String, Object> withSourceAssetThumbnail(Map<String, Object> sourceAsset) {
        Map<String, Object> row = new LinkedHashMap<>(sourceAsset);
        row.put("thumbnailUrl", thumbnailOrOriginal(stringValue(row.get("fileUrl"))));
        return row;
    }

    private Map<String, Object> withOutputThumbnail(Map<String, Object> output) {
        Map<String, Object> row = new LinkedHashMap<>(output);
        if (isImageResultType(row.get("resultType"))) {
            row.put("thumbnailUrl", thumbnailOrOriginal(firstNonBlank(stringValue(row.get("previewUrl")), stringValue(row.get("downloadUrl")))));
        } else if (isVideoResultType(row.get("resultType"))) {
            Map<String, Object> extra = mapValue(row.get("extra"));
            String thumbnailUrl = mediaThumbnailOrOriginal(
                "video",
                firstNonBlank(stringValue(row.get("previewUrl")), stringValue(row.get("downloadUrl"))),
                List.of(firstNonBlank(
                    stringValue(extra.get("thumbnailUrl")),
                    stringValue(extra.get("posterUrl")),
                    stringValue(extra.get("firstFrameUrl"))
                ))
            );
            if (!thumbnailUrl.isBlank()) {
                row.put("thumbnailUrl", thumbnailUrl);
            } else {
                row.putIfAbsent("thumbnailUrl", "");
            }
        } else {
            row.putIfAbsent("thumbnailUrl", "");
        }
        return row;
    }

    private List<String> materialThumbnailCandidates(Map<String, Object> material) {
        Map<String, Object> metadata = mapValue(material.get("metadata"));
        return List.of(firstNonBlank(
            stringValue(material.get("thumbnailUrl")),
            stringValue(metadata.get("thumbnailUrl")),
            stringValue(metadata.get("posterUrl")),
            stringValue(metadata.get("firstFrameUrl")),
            stringValue(metadata.get("startFrameUrl"))
        ));
    }

    /**
     * 汇总任务失败原因，优先返回执行期最具体的错误文本。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private FailureSummary failureSummary(TaskRecord task) {
        Map<String, Object> latestAttempt = latestAttempt(task);
        Map<String, Object> latestFailedStageRun = latestFailedStageRun(task);
        Map<String, Object> latestErrorTrace = latestErrorTrace(task);
        Map<String, Object> tracePayload = mapValue(latestErrorTrace.get("payload"));

        String reason = firstNonBlank(
            specificFailureMessage(latestAttempt.get("failureMessage")),
            specificFailureMessage(latestFailedStageRun.get("errorMessage")),
            specificFailureMessage(tracePayload.get("error")),
            specificFailureMessage(tracePayload.get("errorMessage")),
            specificFailureMessage(tracePayload.get("reason")),
            specificFailureMessage(latestErrorTrace.get("message")),
            blankToNull(task.errorMessage())
        );

        String stage = blankToNull(firstNonBlank(
            stringValue(latestFailedStageRun.get("stageName")),
            stringValue(latestErrorTrace.get("stage")),
            stringValue(task.executionContext().get("currentStage")),
            stringValue(latestAttempt.get("resumeFromStage"))
        ));
        Integer clipIndex = nullableInt(firstPresent(
            latestFailedStageRun.get("clipIndex"),
            tracePayload.get("clipIndex"),
            task.executionContext().get("currentClipIndex")
        ));
        if (clipIndex != null && clipIndex <= 0) {
            clipIndex = null;
        }
        if (reason.isBlank()) {
            return new FailureSummary(null, stage, clipIndex);
        }
        return new FailureSummary(reason, stage, clipIndex);
    }

    /**
     * 处理current阶段。
     * @param task 要处理的任务对象
     * @param activeAttempt active尝试值
     * @param latestStageRun latest阶段运行值
     * @param latestTrace latest追踪值
     * @return 处理结果
     */
    private String currentStage(TaskRecord task, Map<String, Object> activeAttempt, Map<String, Object> latestStageRun, Map<String, Object> latestTrace) {
        String stage = firstNonBlank(
            stringValue(task.executionContext().get("currentStage")),
            stringValue(latestStageRun.get("stageName")),
            stringValue(latestStageRun.get("stage")),
            stringValue(activeAttempt.get("stageName")),
            stringValue(activeAttempt.get("resumeFromStage")),
            stringValue(latestTrace.get("stage"))
        );
        if (!stage.isBlank()) {
            return stage;
        }
        return switch (TaskStatus.normalize(task.status())) {
            case "ANALYZING" -> TaskStage.ANALYSIS.code();
            case "PLANNING" -> TaskStage.PLANNING.code();
            case "RENDERING" -> TaskStage.RENDER.code();
            case "RUNNING" -> TaskStage.DISPATCH.code();
            case "PAUSED" -> TaskStage.PAUSED.code();
            case "PENDING" -> task.isQueued() ? TaskStage.DISPATCH.code() : "";
            default -> "";
        };
    }

    /**
     * 处理已渲染片段Indices。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Integer> renderedClipIndices(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .map(item -> intValue(item.get("clipIndex"), 0))
            .filter(item -> item > 0)
            .sorted()
            .toList();
    }

    /**
     * 处理contiguous片段数量。
     * @param clipIndices 片段Indices值
     * @return 处理结果
     */
    private int contiguousClipCount(List<Integer> clipIndices) {
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
     * 处理时长Diagnostics。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Map<String, Object>> durationDiagnostics(TaskRecord task) {
        List<Map<String, Object>> planRows = durationPlanRows(task);
        List<Map<String, Object>> diagnostics = new ArrayList<>();
        Map<Integer, Map<String, Object>> outputsByClip = new LinkedHashMap<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!isVideoResultType(output.get("resultType"))) {
                continue;
            }
            int clipIndex = intValue(output.get("clipIndex"), 0);
            if (clipIndex > 0) {
                outputsByClip.put(clipIndex, output);
            }
        }
        for (Map<String, Object> planRow : planRows) {
            int clipIndex = intValue(planRow.get("clipIndex"), diagnostics.size() + 1);
            Map<String, Object> output = outputsByClip.remove(clipIndex);
            if (output == null) {
                output = Map.of();
            }
            Map<String, Object> outputExtra = mapValue(output.get("extra"));
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("clipIndex", clipIndex);
            row.put("durationSource", stringValue(planRow.get("durationSource")));
            row.put("scriptMinDurationSeconds", nullableInt(planRow.get("scriptMinDurationSeconds")));
            row.put("scriptMaxDurationSeconds", nullableInt(planRow.get("scriptMaxDurationSeconds")));
            row.put("plannedTargetDurationSeconds", intValue(
                firstPresent(
                    planRow.get("plannedTargetDurationSeconds"),
                    planRow.get("targetDurationSeconds"),
                    outputExtra.get("plannedTargetDurationSeconds"),
                    outputExtra.get("targetDurationSeconds")
                ),
                0
            ));
            row.put("plannedMinDurationSeconds", intValue(
                firstPresent(
                    planRow.get("plannedMinDurationSeconds"),
                    planRow.get("minDurationSeconds"),
                    outputExtra.get("plannedMinDurationSeconds"),
                    outputExtra.get("minDurationSeconds")
                ),
                0
            ));
            row.put("plannedMaxDurationSeconds", intValue(
                firstPresent(
                    planRow.get("plannedMaxDurationSeconds"),
                    planRow.get("maxDurationSeconds"),
                    outputExtra.get("plannedMaxDurationSeconds"),
                    outputExtra.get("maxDurationSeconds")
                ),
                0
            ));
            row.put("requestedDurationSeconds", nullableDouble(firstPresent(
                outputExtra.get("requestedDurationSeconds"),
                outputExtra.get("requestedDuration"),
                planRow.get("requestedDurationSeconds")
            )));
            row.put("appliedDurationSeconds", nullableDouble(firstPresent(
                outputExtra.get("appliedDurationSeconds"),
                outputExtra.get("resolvedDurationSeconds"),
                planRow.get("appliedDurationSeconds")
            )));
            row.put("actualDurationSeconds", output.isEmpty() ? null : nullableDouble(output.get("durationSeconds")));
            row.put("status", output.isEmpty() ? "pending" : "rendered");
            diagnostics.add(row);
        }
        for (Map.Entry<Integer, Map<String, Object>> entry : outputsByClip.entrySet()) {
            Map<String, Object> output = entry.getValue();
            Map<String, Object> outputExtra = mapValue(output.get("extra"));
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("clipIndex", entry.getKey());
            row.put("durationSource", "");
            row.put("scriptMinDurationSeconds", null);
            row.put("scriptMaxDurationSeconds", null);
            row.put("plannedTargetDurationSeconds", nullableInt(firstPresent(
                outputExtra.get("plannedTargetDurationSeconds"),
                outputExtra.get("targetDurationSeconds")
            )));
            row.put("plannedMinDurationSeconds", nullableInt(firstPresent(
                outputExtra.get("plannedMinDurationSeconds"),
                outputExtra.get("minDurationSeconds")
            )));
            row.put("plannedMaxDurationSeconds", nullableInt(firstPresent(
                outputExtra.get("plannedMaxDurationSeconds"),
                outputExtra.get("maxDurationSeconds")
            )));
            row.put("requestedDurationSeconds", nullableDouble(firstPresent(
                outputExtra.get("requestedDurationSeconds"),
                outputExtra.get("requestedDuration")
            )));
            row.put("appliedDurationSeconds", nullableDouble(firstPresent(
                outputExtra.get("appliedDurationSeconds"),
                outputExtra.get("resolvedDurationSeconds")
            )));
            row.put("actualDurationSeconds", nullableDouble(output.get("durationSeconds")));
            row.put("status", "rendered");
            diagnostics.add(row);
        }
        diagnostics.sort(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), Integer.MAX_VALUE)));
        return diagnostics;
    }

    /**
     * 处理公开案例描述。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private String showcaseDescription(TaskRecord task) {
        String sourceFileName = stringValue(task.sourceFileName());
        if (!sourceFileName.isBlank()) {
            return "来源素材：" + sourceFileName;
        }
        String aspectRatio = stringValue(task.aspectRatio());
        String duration = durationLabel(task.minDurationSeconds(), task.maxDurationSeconds());
        if (!aspectRatio.isBlank() && !duration.isBlank()) {
            return "真实任务 · " + aspectRatio + " · " + duration;
        }
        if (!aspectRatio.isBlank()) {
            return "真实任务 · 画幅 " + aspectRatio;
        }
        if (!duration.isBlank()) {
            return "真实任务 · 时长 " + duration;
        }
        return "真实生产任务案例";
    }

    /**
     * 返回公开案例的模型摘要。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private Map<String, Object> showcaseModels(TaskRecord task) {
        GenerationRequestSnapshot snapshot = task.requestSnapshot() == null ? GenerationRequestSnapshot.empty() : task.requestSnapshot();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("textAnalysisModel", blankToNull(snapshot.textAnalysisModel()));
        row.put("imageModel", blankToNull(snapshot.imageModel()));
        row.put("videoModel", blankToNull(snapshot.videoModel()));
        return row;
    }

    /**
     * 格式化时长区间。
     * @param minSeconds 最小时长值
     * @param maxSeconds 最大时长值
     * @return 处理结果
     */
    private String durationLabel(int minSeconds, int maxSeconds) {
        if (minSeconds > 0 && maxSeconds > 0 && minSeconds != maxSeconds) {
            return minSeconds + "-" + maxSeconds + "s";
        }
        int seconds = Math.max(minSeconds, maxSeconds);
        return seconds > 0 ? seconds + "s" : "";
    }

    /**
     * 处理时长规划行。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Map<String, Object>> durationPlanRows(TaskRecord task) {
        List<Map<String, Object>> clipDurationPlan = listMapValue(task.executionContext().get("clipDurationPlan"));
        if (!clipDurationPlan.isEmpty()) {
            return clipDurationPlan;
        }
        List<Map<String, Object>> normalizedPlan = listMapValue(task.executionContext().get("durationPlan"));
        if (!normalizedPlan.isEmpty()) {
            return withClipIndexFallback(normalizedPlan);
        }
        List<Map<String, Object>> clipDiagnostics = listMapValue(task.executionContext().get("clipDurationDiagnostics"));
        if (!clipDiagnostics.isEmpty()) {
            return withClipIndexFallback(clipDiagnostics);
        }
        List<Map<String, Object>> diagnostics = listMapValue(task.executionContext().get("durationDiagnostics"));
        if (!diagnostics.isEmpty()) {
            return withClipIndexFallback(diagnostics);
        }
        return List.of();
    }

    /**
     * 处理with片段索引兜底。
     * @param rows 行值
     * @return 处理结果
     */
    private List<Map<String, Object>> withClipIndexFallback(List<Map<String, Object>> rows) {
        List<Map<String, Object>> normalized = new ArrayList<>();
        int fallbackClipIndex = 1;
        for (Map<String, Object> item : rows) {
            Map<String, Object> row = new LinkedHashMap<>(item);
            if (!row.containsKey("clipIndex")) {
                row.put("clipIndex", fallbackClipIndex);
            }
            fallbackClipIndex += 1;
            normalized.add(row);
        }
        return normalized;
    }

    /**
     * 处理解析计划片段数量。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private int resolvePlannedClipCount(TaskRecord task) {
        int plannedClipCount = intValue(task.executionContext().get("plannedClipCount"), 0);
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        plannedClipCount = listValue(task.executionContext().get("clipPrompts")).size();
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        plannedClipCount = durationPlanRows(task).size();
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        return renderedClipIndices(task).size();
    }

    /**
     * 检查是否视频结果类型。
     * @param rawValue 原始值
     * @return 是否满足条件
     */
    private boolean isVideoResultType(Object rawValue) {
        String resultType = stringValue(rawValue).toLowerCase();
        return TaskResultTypes.isVideo(resultType);
    }

    private boolean isImageResultType(Object rawValue) {
        String resultType = stringValue(rawValue).toLowerCase();
        return TaskResultTypes.IMAGE.equals(resultType) || "image".equals(resultType) || "image_generation".equals(resultType);
    }

    /**
     * 检查是否拼接结果类型。
     * @param rawValue 原始值
     * @return 是否满足条件
     */
    private boolean isJoinResultType(Object rawValue) {
        String resultType = stringValue(rawValue).toLowerCase();
        return TaskResultTypes.isJoin(resultType);
    }

    /**
     * 处理正文Preview。
     * @param transcriptText 正文文本值
     * @return 处理结果
     */
    private String transcriptPreview(String transcriptText) {
        String normalized = stringValue(transcriptText);
        if (normalized.isBlank()) {
            return null;
        }
        return normalized.substring(0, Math.min(220, normalized.length()));
    }

    /**
     * 处理首个Present。
     * @param values 值
     * @return 处理结果
     */
    private Object firstPresent(Object... values) {
        for (Object value : values) {
            if (value == null) {
                continue;
            }
            if (value instanceof String text && text.isBlank()) {
                continue;
            }
            return value;
        }
        return null;
    }

    /**
     * 映射值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    /**
     * 列出值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private List<Object> listValue(Object value) {
        if (value instanceof List<?> list) {
            return (List<Object>) list;
        }
        return List.of();
    }

    /**
     * 列出Map值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listMapValue(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                rows.add((Map<String, Object>) map);
            }
        }
        return rows;
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    /**
     * 检查是否布尔值。
     * @param value 待处理的值
     * @return 是否满足条件
     */
    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        return value != null && Boolean.parseBoolean(String.valueOf(value));
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return fallback;
    }

    /**
     * 处理nullableInt。
     * @param value 待处理的值
     * @return 处理结果
     */
    private Integer nullableInt(Object value) {
        if (value == null) {
            return null;
        }
        return intValue(value, 0);
    }

    /**
     * 处理nullableDouble。
     * @param value 待处理的值
     * @return 处理结果
     */
    private Double nullableDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value != null) {
            try {
                return Double.parseDouble(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理空白转null。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String blankToNull(String value) {
        String normalized = stringValue(value);
        return normalized.isBlank() ? null : normalized;
    }

    /**
     * 过滤“失败/错误”等无信息量的泛化文案。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String specificFailureMessage(Object value) {
        String normalized = stringValue(value);
        if (normalized.isBlank()) {
            return "";
        }
        String lower = normalized.toLowerCase();
        if (List.of("error", "failed", "failure", "错误", "失败", "任务失败", "任务已失败").contains(normalized)
            || List.of("error", "failed", "failure").contains(lower)
            || List.of("spring worker 执行失败", "spring worker 执行失败。", "远端视频生成失败").contains(normalized)
            || List.of("spring worker 执行失败", "spring worker 执行失败。", "remote video generation failed").contains(lower)) {
            return "";
        }
        return normalized;
    }

    /**
     * 处理任务诊断摘要。
     * @param severity severity值
     * @param code code值
     * @param hint 提示值
     * @param recommendedAction recommendedAction值
     * @return 处理结果
     */
    private record TaskDiagnosisSummary(String severity, String code, String hint, String recommendedAction) {}

    /**
     * 处理任务失败摘要。
     * @param reason 失败原因值
     * @param stage 失败阶段值
     * @param clipIndex 失败镜头值
     */
    private record FailureSummary(String reason, String stage, Integer clipIndex) {}

    /**
     * 处理任务产物Directories。
     * @param baseDir baseDir值
     * @param runningDir runningDir值
     * @param joinedDir joinedDir值
     * @return 处理结果
     */
    private record TaskArtifactDirectories(String baseDir, String runningDir, String joinedDir) {

        /**
         * 处理转为Map。
         * @return 处理结果
         */
        Map<String, Object> toMap() {
            return Map.of(
                "baseDir", baseDir,
                "runningDir", runningDir,
                "joinedDir", joinedDir
            );
        }
    }

    /**
     * 处理任务监控快照。
     * @param currentStage current阶段值
     * @param activeAttemptStatus active尝试状态值
     * @param activeWorkerInstanceId active工作节点Instance标识值
     * @param resumeFromStage resumeFrom阶段值
     * @param resumeFromClipIndex resumeFrom片段索引值
     * @param plannedClipCount 计划片段数量值
     * @param renderedClipCount 已渲染片段数量值
     * @param contiguousRenderedClipCount contiguous已渲染片段数量值
     * @param latestRenderedClipIndex latest已渲染片段索引值
     * @param latestVideoOutputUrl latest视频输出URL值
     * @param latestJoinName latest拼接Name值
     * @param latestJoinOutputUrl latest拼接输出URL值
     * @param latestJoinClipIndex latest拼接片段索引值
     * @param latestJoinClipIndices latest拼接片段Indices值
     * @param storyboardFileUrl 分镜文件URL值
     * @param artifactDirectories 产物Directories值
     * @param latestTrace latest追踪值
     * @param latestStageRun latest阶段运行值
     * @param latestVideoOutput latest视频输出值
     * @param latestJoinOutput latest拼接输出值
     * @param renderedClipIndices 已渲染片段Indices值
     * @return 处理结果
     */
    private record TaskMonitoringSnapshot(
        String currentStage,
        String activeAttemptStatus,
        String activeWorkerInstanceId,
        String resumeFromStage,
        int resumeFromClipIndex,
        int plannedClipCount,
        int renderedClipCount,
        int contiguousRenderedClipCount,
        int latestRenderedClipIndex,
        String latestVideoOutputUrl,
        String latestJoinName,
        String latestJoinOutputUrl,
        int latestJoinClipIndex,
        List<Object> latestJoinClipIndices,
        String storyboardFileUrl,
        TaskArtifactDirectories artifactDirectories,
        Map<String, Object> latestTrace,
        Map<String, Object> latestStageRun,
        Map<String, Object> latestVideoOutput,
        Map<String, Object> latestJoinOutput,
        List<Integer> renderedClipIndices
    ) {

        /**
         * 处理转为Map。
         * @param includeVerbose includeVerbose值
         * @return 处理结果
         */
        Map<String, Object> toMap(boolean includeVerbose) {
            Map<String, Object> monitoring = new LinkedHashMap<>();
            monitoring.put("currentStage", currentStage);
            monitoring.put("activeAttemptStatus", activeAttemptStatus);
            monitoring.put("activeWorkerInstanceId", activeWorkerInstanceId);
            monitoring.put("resumeFromStage", resumeFromStage);
            monitoring.put("resumeFromClipIndex", resumeFromClipIndex);
            monitoring.put("plannedClipCount", plannedClipCount);
            monitoring.put("renderedClipCount", renderedClipCount);
            monitoring.put("contiguousRenderedClipCount", contiguousRenderedClipCount);
            monitoring.put("latestRenderedClipIndex", latestRenderedClipIndex);
            monitoring.put("latestVideoOutputUrl", latestVideoOutputUrl);
            monitoring.put("latestJoinName", latestJoinName);
            monitoring.put("latestJoinOutputUrl", latestJoinOutputUrl);
            monitoring.put("latestJoinClipIndex", latestJoinClipIndex);
            monitoring.put("latestJoinClipIndices", latestJoinClipIndices);
            monitoring.put("storyboardFileUrl", storyboardFileUrl);
            monitoring.put("artifactDirectories", artifactDirectories.toMap());
            if (includeVerbose) {
                monitoring.put("latestTrace", latestTrace);
                monitoring.put("latestStageRun", latestStageRun);
                monitoring.put("latestVideoOutput", latestVideoOutput);
                monitoring.put("latestJoinOutput", latestJoinOutput);
                monitoring.put("renderedClipIndices", renderedClipIndices);
            }
            return monitoring;
        }
    }
}
