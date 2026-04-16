package com.jiandou.api.task.view;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.task.TaskRecord;
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
import org.springframework.stereotype.Component;

/**
 * 负责把任务聚合对象转换为接口返回结构。
 * 当前阶段优先保持前端字段兼容，但内部已经开始收敛为更明确的视图对象。
 */
@Component
public class TaskViewMapper {

    private final Path storageRoot;

    public TaskViewMapper(JiandouStorageProperties storageProperties) {
        this.storageRoot = storageProperties.resolveRootDir();
    }

    /**
     * 处理转为列表Item。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Map<String, Object> toListItem(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        TaskDiagnosisSummary diagnosis = diagnosisSummary(task, monitoring);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", task.id());
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
        return row;
    }

    /**
     * 详情视图在列表字段基础上补充上下文、素材和运行信息。
     */
    public Map<String, Object> toDetail(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
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
        row.put("transcriptPreview", transcriptPreview(task.transcriptText()));
        row.put("transcriptCueCount", 0);
        row.put("source", null);
        row.put("sourceAssets", task.sourceAssets());
        row.put("storyboardScript", task.storyboardScript());
        row.put("materials", task.materials());
        row.put("executionContext", task.executionContext());
        row.put("requestSnapshot", task.requestSnapshot() == null ? Map.of() : task.requestSnapshot().toMap());
        row.put("durationDiagnostics", durationDiagnostics(task));
        row.put("sourceAssetIds", List.of());
        row.put("sourceFileNames", List.of());
        row.put("plan", List.of());
        row.put("activeAttemptId", task.activeAttemptId());
        row.put("attempts", task.attempts());
        row.put("stageRuns", task.stageRuns());
        row.put("outputs", task.outputs());
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
     * 处理任务诊断摘要。
     * @param severity severity值
     * @param code code值
     * @param hint 提示值
     * @param recommendedAction recommendedAction值
     * @return 处理结果
     */
    private record TaskDiagnosisSummary(String severity, String code, String hint, String recommendedAction) {}

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
