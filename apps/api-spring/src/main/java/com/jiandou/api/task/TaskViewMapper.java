package com.jiandou.api.task;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 负责把任务聚合对象转换为接口返回结构。
 * 当前阶段优先保持前端字段兼容，但内部已经开始收敛为更明确的视图对象。
 */
@Component
class TaskViewMapper {

    private final Path storageRoot;

    TaskViewMapper(@Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot) {
        this.storageRoot = Paths.get(storageRoot).toAbsolutePath().normalize();
    }

    Map<String, Object> toListItem(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        TaskDiagnosisSummary diagnosis = diagnosisSummary(task, monitoring);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", task.id);
        row.put("title", task.title);
        row.put("status", task.status);
        row.put("progress", task.progress);
        row.put("createdAt", task.createdAt);
        row.put("updatedAt", task.updatedAt);
        row.put("sourceFileName", task.sourceFileName);
        row.put("aspectRatio", task.aspectRatio);
        row.put("minDurationSeconds", task.minDurationSeconds);
        row.put("maxDurationSeconds", task.maxDurationSeconds);
        row.put("retryCount", task.retryCount);
        row.put("startedAt", task.startedAt);
        row.put("finishedAt", task.finishedAt);
        row.put("completedOutputCount", task.completedOutputCount);
        row.put("taskSeed", task.taskSeed);
        row.put("effectRating", task.effectRating);
        row.put("effectRatingNote", task.effectRatingNote);
        row.put("ratedAt", task.ratedAt);
        row.put("hasTranscript", task.hasTranscript);
        row.put("hasTimedTranscript", task.hasTimedTranscript);
        row.put("sourceAssetCount", task.sourceAssetCount);
        row.put("editingMode", task.editingMode);
        row.put("isQueued", task.isQueued);
        row.put("queuePosition", task.queuePosition);
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
    Map<String, Object> toDetail(TaskRecord task) {
        TaskMonitoringSnapshot monitoring = monitoringSummary(task);
        Map<String, Object> row = new LinkedHashMap<>(toListItem(task));
        row.put("artifactDirectories", monitoring.artifactDirectories().toMap());
        row.put("introTemplate", task.introTemplate);
        row.put("outroTemplate", task.outroTemplate);
        row.put("creativePrompt", task.creativePrompt);
        row.put("taskSeed", task.taskSeed);
        row.put("effectRating", task.effectRating);
        row.put("effectRatingNote", task.effectRatingNote);
        row.put("ratedAt", task.ratedAt);
        row.put("errorMessage", task.errorMessage);
        row.put("transcriptPreview", transcriptPreview(task.transcriptText));
        row.put("transcriptCueCount", 0);
        row.put("source", null);
        row.put("sourceAssets", task.sourceAssets);
        row.put("storyboardScript", task.storyboardScript);
        row.put("materials", task.materials);
        row.put("executionContext", task.executionContext);
        row.put("requestSnapshot", task.requestSnapshot == null ? Map.of() : task.requestSnapshot.toMap());
        row.put("durationDiagnostics", durationDiagnostics(task));
        row.put("sourceAssetIds", List.of());
        row.put("sourceFileNames", List.of());
        row.put("plan", List.of());
        row.put("activeAttemptId", task.activeAttemptId);
        row.put("attempts", task.attempts);
        row.put("stageRuns", task.stageRuns);
        row.put("outputs", task.outputs);
        row.put("monitoring", monitoring.toMap(true));
        return row;
    }

    private TaskDiagnosisSummary diagnosisSummary(TaskRecord task, TaskMonitoringSnapshot monitoring) {
        int plannedClipCount = monitoring.plannedClipCount();
        int renderedClipCount = monitoring.renderedClipCount();
        int contiguousRenderedClipCount = monitoring.contiguousRenderedClipCount();
        int joinClipIndex = monitoring.latestJoinClipIndex();
        boolean hasAudioClip = task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .anyMatch(item -> boolValue(mapValue(item.get("extra")).get("hasAudio")));
        if ("FAILED".equals(task.status)) {
            return diagnosis("high", "task_failed", "任务已失败，建议查看诊断并执行恢复重试。", contiguousRenderedClipCount > 0
                ? "从失败镜头继续 retry"
                : "从分析阶段重新 retry");
        }
        if ("PENDING".equals(task.status) && !task.isQueued) {
            return diagnosis("high", "pending_not_queued", "任务处于 PENDING，但当前未在队列中。", "重新 enqueue 或 retry");
        }
        if ("COMPLETED".equals(task.status) && plannedClipCount > 0 && renderedClipCount < plannedClipCount) {
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
                stringValue(task.executionContext.get("workerInstanceId")),
                stringValue(latestStageRun.get("workerInstanceId")),
                stringValue(latestTrace.get("workerInstanceId"))
            ),
            firstNonBlank(
                stringValue(activeAttempt.get("resumeFromStage")),
                stringValue(attemptPayload.get("resumeFromStage")),
                stringValue(task.executionContext.get("attemptResumeFromStage"))
            ),
            intValue(
                firstPresent(
                    activeAttempt.get("resumeFromClipIndex"),
                    attemptPayload.get("resumeFromClipIndex"),
                    task.executionContext.get("attemptResumeFromClipIndex")
                ),
                0
            ),
            plannedClipCount,
            renderedClipIndices.size(),
            contiguousClipCount(renderedClipIndices),
            renderedClipIndices.isEmpty() ? 0 : renderedClipIndices.get(renderedClipIndices.size() - 1),
            firstNonBlank(stringValue(latestVideoOutput.get("downloadUrl")), stringValue(latestVideoOutput.get("previewUrl"))),
            firstNonBlank(stringValue(task.executionContext.get("latestJoinName")), stringValue(mapValue(latestJoinOutput.get("extra")).get("joinName"))),
            firstNonBlank(stringValue(task.executionContext.get("latestJoinOutputUrl")), stringValue(latestJoinOutput.get("downloadUrl"))),
            intValue(task.executionContext.get("latestJoinClipIndex"), intValue(latestJoinOutput.get("clipIndex"), 0)),
            listValue(task.executionContext.get("latestJoinClipIndices")),
            stringValue(task.executionContext.get("storyboardFileUrl")),
            artifactDirectories(task),
            latestTrace,
            latestStageRun,
            latestVideoOutput,
            latestJoinOutput,
            renderedClipIndices
        );
    }

    private TaskArtifactDirectories artifactDirectories(TaskRecord task) {
        return new TaskArtifactDirectories(
            storageRoot.resolve(TaskArtifactNaming.taskBaseRelativeDir(task)).toString(),
            storageRoot.resolve(TaskArtifactNaming.taskRunningRelativeDir(task)).toString(),
            storageRoot.resolve(TaskArtifactNaming.taskJoinedRelativeDir(task)).toString()
        );
    }

    private Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId == null || task.activeAttemptId.isBlank()) {
            return latestAttempt(task);
        }
        for (Map<String, Object> item : task.attemptsView()) {
            if (task.activeAttemptId.equals(stringValue(item.get("attemptId")))) {
                return item;
            }
        }
        return latestAttempt(task);
    }

    private Map<String, Object> latestByTimestamp(List<Map<String, Object>> rows, String fieldName) {
        return rows.stream()
            .max(Comparator.comparing(item -> stringValue(item.get(fieldName))))
            .orElse(Map.of());
    }

    private Map<String, Object> latestAttempt(TaskRecord task) {
        return task.attemptsView().stream()
            .max(Comparator.comparing(this::attemptSortKey))
            .orElse(Map.of());
    }

    private String attemptSortKey(Map<String, Object> item) {
        return firstNonBlank(
            stringValue(item.get("finishedAt")),
            stringValue(item.get("startedAt")),
            stringValue(item.get("claimedAt")),
            stringValue(item.get("queueEnteredAt"))
        );
    }

    private Map<String, Object> latestStageRun(TaskRecord task) {
        return task.stageRunsView().stream()
            .max(Comparator.comparing(this::stageRunSortKey))
            .orElse(Map.of());
    }

    private String stageRunSortKey(Map<String, Object> stageRun) {
        return firstNonBlank(
            stringValue(stageRun.get("finishedAt")),
            stringValue(stageRun.get("updatedAt")),
            stringValue(stageRun.get("startedAt")),
            stringValue(stageRun.get("createdAt"))
        );
    }

    private Map<String, Object> latestVideoOutput(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .max(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .orElse(Map.of());
    }

    private Map<String, Object> latestJoinOutput(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isJoinResultType(item.get("resultType")))
            .max(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .orElse(Map.of());
    }

    private String currentStage(TaskRecord task, Map<String, Object> activeAttempt, Map<String, Object> latestStageRun, Map<String, Object> latestTrace) {
        String stage = firstNonBlank(
            stringValue(task.executionContext.get("currentStage")),
            stringValue(latestStageRun.get("stageName")),
            stringValue(latestStageRun.get("stage")),
            stringValue(activeAttempt.get("stageName")),
            stringValue(activeAttempt.get("resumeFromStage")),
            stringValue(latestTrace.get("stage"))
        );
        if (!stage.isBlank()) {
            return stage;
        }
        return switch (stringValue(task.status).toUpperCase()) {
            case "ANALYZING" -> "analysis";
            case "PLANNING" -> "planning";
            case "RENDERING" -> "render";
            case "RUNNING" -> "dispatch";
            case "PAUSED" -> "paused";
            case "PENDING" -> task.isQueued ? "dispatch" : "";
            default -> "";
        };
    }

    private List<Integer> renderedClipIndices(TaskRecord task) {
        return task.outputsView().stream()
            .filter(item -> isVideoResultType(item.get("resultType")))
            .map(item -> intValue(item.get("clipIndex"), 0))
            .filter(item -> item > 0)
            .sorted()
            .toList();
    }

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

    private List<Map<String, Object>> durationPlanRows(TaskRecord task) {
        List<Map<String, Object>> clipDurationPlan = listMapValue(task.executionContext.get("clipDurationPlan"));
        if (!clipDurationPlan.isEmpty()) {
            return clipDurationPlan;
        }
        List<Map<String, Object>> normalizedPlan = listMapValue(task.executionContext.get("durationPlan"));
        if (!normalizedPlan.isEmpty()) {
            return withClipIndexFallback(normalizedPlan);
        }
        List<Map<String, Object>> clipDiagnostics = listMapValue(task.executionContext.get("clipDurationDiagnostics"));
        if (!clipDiagnostics.isEmpty()) {
            return withClipIndexFallback(clipDiagnostics);
        }
        List<Map<String, Object>> diagnostics = listMapValue(task.executionContext.get("durationDiagnostics"));
        if (!diagnostics.isEmpty()) {
            return withClipIndexFallback(diagnostics);
        }
        return List.of();
    }

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

    private int resolvePlannedClipCount(TaskRecord task) {
        int plannedClipCount = intValue(task.executionContext.get("plannedClipCount"), 0);
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        plannedClipCount = listValue(task.executionContext.get("clipPrompts")).size();
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        plannedClipCount = durationPlanRows(task).size();
        if (plannedClipCount > 0) {
            return plannedClipCount;
        }
        return renderedClipIndices(task).size();
    }

    private boolean isVideoResultType(Object rawValue) {
        String resultType = stringValue(rawValue).toLowerCase();
        return "video".equals(resultType) || "video_clip".equals(resultType);
    }

    private boolean isJoinResultType(Object rawValue) {
        String resultType = stringValue(rawValue).toLowerCase();
        return "video_join".equals(resultType) || "join_video".equals(resultType) || "joined_video".equals(resultType);
    }

    private String transcriptPreview(String transcriptText) {
        String normalized = stringValue(transcriptText);
        if (normalized.isBlank()) {
            return null;
        }
        return normalized.substring(0, Math.min(220, normalized.length()));
    }

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

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        return value != null && Boolean.parseBoolean(String.valueOf(value));
    }

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

    private Integer nullableInt(Object value) {
        if (value == null) {
            return null;
        }
        return intValue(value, 0);
    }

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

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private record TaskDiagnosisSummary(String severity, String code, String hint, String recommendedAction) {}

    private record TaskArtifactDirectories(String baseDir, String runningDir, String joinedDir) {

        Map<String, Object> toMap() {
            return Map.of(
                "baseDir", baseDir,
                "runningDir", runningDir,
                "joinedDir", joinedDir
            );
        }
    }

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
