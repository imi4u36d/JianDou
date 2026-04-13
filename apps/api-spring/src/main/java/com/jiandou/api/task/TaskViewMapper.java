package com.jiandou.api.task;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;

@Component
class TaskViewMapper {

    private final Path storageRoot;

    TaskViewMapper(@Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot) {
        this.storageRoot = Paths.get(storageRoot).toAbsolutePath().normalize();
    }

    Map<String, Object> toListItem(TaskRecord task) {
        Map<String, Object> monitoring = monitoringSummary(task, false);
        Map<String, Object> diagnosis = diagnosisSummary(task, monitoring);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", task.id);
        row.put("title", task.title);
        row.put("status", task.status);
        row.put("platform", task.platform);
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
        row.put("currentStage", monitoring.get("currentStage"));
        row.put("activeWorkerInstanceId", monitoring.get("activeWorkerInstanceId"));
        row.put("plannedClipCount", monitoring.get("plannedClipCount"));
        row.put("renderedClipCount", monitoring.get("renderedClipCount"));
        row.put("diagnosisSeverity", diagnosis.get("severity"));
        row.put("diagnosisCode", diagnosis.get("code"));
        row.put("diagnosisHint", diagnosis.get("hint"));
        row.put("recommendedAction", diagnosis.get("recommendedAction"));
        return row;
    }

    Map<String, Object> toDetail(TaskRecord task) {
        Map<String, Object> row = new LinkedHashMap<>(toListItem(task));
        row.put("artifactDirectories", artifactDirectories(task));
        row.put("introTemplate", task.introTemplate);
        row.put("outroTemplate", task.outroTemplate);
        row.put("creativePrompt", task.creativePrompt);
        row.put("taskSeed", task.taskSeed);
        row.put("effectRating", task.effectRating);
        row.put("effectRatingNote", task.effectRatingNote);
        row.put("ratedAt", task.ratedAt);
        row.put("errorMessage", task.errorMessage);
        row.put("transcriptPreview", task.transcriptText.isBlank() ? null : task.transcriptText.substring(0, Math.min(220, task.transcriptText.length())));
        row.put("transcriptCueCount", 0);
        row.put("source", null);
        row.put("sourceAssets", task.sourceAssets);
        row.put("storyboardScript", task.storyboardScript);
        row.put("materials", task.materials);
        row.put("executionContext", task.executionContext);
        row.put("requestSnapshot", task.requestSnapshot);
        row.put("sourceAssetIds", List.of());
        row.put("sourceFileNames", List.of());
        row.put("plan", List.of());
        row.put("activeAttemptId", task.activeAttemptId);
        row.put("attempts", task.attempts);
        row.put("stageRuns", task.stageRuns);
        row.put("outputs", task.outputs);
        row.put("monitoring", monitoringSummary(task, true));
        return row;
    }

    private Map<String, Object> diagnosisSummary(TaskRecord task, Map<String, Object> monitoring) {
        int plannedClipCount = intValue(monitoring.get("plannedClipCount"), 0);
        int renderedClipCount = intValue(monitoring.get("renderedClipCount"), 0);
        int contiguousRenderedClipCount = intValue(monitoring.get("contiguousRenderedClipCount"), 0);
        int joinClipIndex = intValue(monitoring.get("latestJoinClipIndex"), 0);
        boolean hasAudioClip = task.outputsView().stream()
            .filter(item -> "video".equalsIgnoreCase(stringValue(item.get("resultType"))))
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

    private Map<String, Object> diagnosis(String severity, String code, String hint, String recommendedAction) {
        Map<String, Object> diagnosis = new LinkedHashMap<>();
        diagnosis.put("severity", severity);
        diagnosis.put("code", code);
        diagnosis.put("hint", hint);
        diagnosis.put("recommendedAction", recommendedAction);
        return diagnosis;
    }

    private Map<String, Object> monitoringSummary(TaskRecord task, boolean includeVerbose) {
        Map<String, Object> activeAttempt = activeAttempt(task);
        Map<String, Object> latestTrace = latestByTimestamp(task.traceView(), "timestamp");
        Map<String, Object> latestStageRun = latestByTimestamp(task.stageRunsView(), "finishedAt");
        Map<String, Object> latestVideoOutput = latestVideoOutput(task);
        Map<String, Object> latestJoinOutput = latestJoinOutput(task);
        int plannedClipCount = intValue(task.executionContext.get("plannedClipCount"), 0);
        List<Integer> renderedClipIndices = renderedClipIndices(task);
        Map<String, Object> monitoring = new LinkedHashMap<>();
        monitoring.put("currentStage", currentStage(task, latestStageRun, latestTrace));
        monitoring.put("activeAttemptStatus", stringValue(activeAttempt.get("status")));
        monitoring.put("activeWorkerInstanceId", stringValue(activeAttempt.get("workerInstanceId")));
        monitoring.put("resumeFromStage", stringValue(activeAttempt.get("resumeFromStage")));
        monitoring.put("resumeFromClipIndex", intValue(activeAttempt.get("resumeFromClipIndex"), 0));
        monitoring.put("plannedClipCount", plannedClipCount);
        monitoring.put("renderedClipCount", renderedClipIndices.size());
        monitoring.put("contiguousRenderedClipCount", contiguousClipCount(renderedClipIndices));
        monitoring.put("latestRenderedClipIndex", renderedClipIndices.isEmpty() ? 0 : renderedClipIndices.get(renderedClipIndices.size() - 1));
        monitoring.put("latestVideoOutputUrl", firstNonBlank(stringValue(latestVideoOutput.get("downloadUrl")), stringValue(latestVideoOutput.get("previewUrl"))));
        monitoring.put("latestJoinName", firstNonBlank(stringValue(task.executionContext.get("latestJoinName")), stringValue(mapValue(latestJoinOutput.get("extra")).get("joinName"))));
        monitoring.put("latestJoinOutputUrl", firstNonBlank(stringValue(task.executionContext.get("latestJoinOutputUrl")), stringValue(latestJoinOutput.get("downloadUrl"))));
        monitoring.put("latestJoinClipIndex", intValue(task.executionContext.get("latestJoinClipIndex"), intValue(latestJoinOutput.get("clipIndex"), 0)));
        monitoring.put("latestJoinClipIndices", listValue(task.executionContext.get("latestJoinClipIndices")));
        monitoring.put("storyboardFileUrl", stringValue(task.executionContext.get("storyboardFileUrl")));
        monitoring.put("artifactDirectories", artifactDirectories(task));
        if (includeVerbose) {
            monitoring.put("latestTrace", latestTrace);
            monitoring.put("latestStageRun", latestStageRun);
            monitoring.put("latestVideoOutput", latestVideoOutput);
            monitoring.put("latestJoinOutput", latestJoinOutput);
            monitoring.put("activeAttempt", activeAttempt);
        }
        return monitoring;
    }

    private Map<String, Object> artifactDirectories(TaskRecord task) {
        String baseRelativeDir = TaskArtifactNaming.taskBaseRelativeDir(task);
        String runningRelativeDir = TaskArtifactNaming.taskRunningRelativeDir(task);
        String joinedRelativeDir = TaskArtifactNaming.taskJoinedRelativeDir(task);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("storageRoot", storageRoot.toString());
        row.put("baseRelativeDir", baseRelativeDir);
        row.put("baseAbsoluteDir", storageRoot.resolve(baseRelativeDir).normalize().toString());
        row.put("runningRelativeDir", runningRelativeDir);
        row.put("runningAbsoluteDir", storageRoot.resolve(runningRelativeDir).normalize().toString());
        row.put("joinedRelativeDir", joinedRelativeDir);
        row.put("joinedAbsoluteDir", storageRoot.resolve(joinedRelativeDir).normalize().toString());
        row.put("runningPublicBaseUrl", storagePublicBaseUrl(runningRelativeDir));
        row.put("joinedPublicBaseUrl", storagePublicBaseUrl(joinedRelativeDir));
        row.put("storyboardFileName", TaskArtifactNaming.storyboardFileName(task, "md"));
        row.put("firstFramePattern", "clip{n}-first.<ext>");
        row.put("lastFramePattern", "clip{n}-last.<ext>");
        row.put("clipPattern", "clip{n}.<ext>");
        row.put("joinPattern", "join-1-2[-3...].mp4");
        return row;
    }

    private String storagePublicBaseUrl(String relativeDir) {
        return "/storage/" + relativeDir.replace('\\', '/') + "/";
    }

    private Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId == null || task.activeAttemptId.isBlank()) {
            return Map.of();
        }
        for (Map<String, Object> attempt : task.attemptsView()) {
            if (task.activeAttemptId.equals(stringValue(attempt.get("attemptId")))) {
                return attempt;
            }
        }
        return Map.of();
    }

    private Map<String, Object> latestVideoOutput(TaskRecord task) {
        List<Map<String, Object>> videos = task.outputsView().stream()
            .filter(item -> "video".equalsIgnoreCase(stringValue(item.get("resultType"))))
            .sorted(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .toList();
        return videos.isEmpty() ? Map.of() : videos.get(videos.size() - 1);
    }

    private Map<String, Object> latestJoinOutput(TaskRecord task) {
        List<Map<String, Object>> joins = task.outputsView().stream()
            .filter(item -> "video_join".equalsIgnoreCase(stringValue(item.get("resultType"))))
            .sorted(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .toList();
        return joins.isEmpty() ? Map.of() : joins.get(joins.size() - 1);
    }

    private List<Integer> renderedClipIndices(TaskRecord task) {
        List<Integer> indices = new ArrayList<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            int clipIndex = intValue(output.get("clipIndex"), 0);
            if (clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        indices.sort(Integer::compareTo);
        return indices;
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

    private String currentStage(TaskRecord task, Map<String, Object> latestStageRun, Map<String, Object> latestTrace) {
        String stageName = stringValue(latestStageRun.get("stageName"));
        if (!stageName.isBlank()) {
            return stageName;
        }
        String traceStage = stringValue(latestTrace.get("stage"));
        if (!traceStage.isBlank()) {
            return traceStage;
        }
        return switch (task.status) {
            case "ANALYZING" -> "analysis";
            case "PLANNING" -> "planning";
            case "RENDERING" -> "render";
            case "COMPLETED", "FAILED", "PAUSED" -> "pipeline";
            default -> "dispatch";
        };
    }

    private Map<String, Object> latestByTimestamp(List<Map<String, Object>> rows, String timestampKey) {
        List<Map<String, Object>> ordered = rows.stream()
            .filter(item -> !stringValue(item.get(timestampKey)).isBlank())
            .sorted((left, right) -> stringValue(right.get(timestampKey)).compareTo(stringValue(left.get(timestampKey))))
            .toList();
        return ordered.isEmpty() ? Map.of() : ordered.get(0);
    }

    @SuppressWarnings("unchecked")
    private List<Object> listValue(Object value) {
        if (value instanceof List<?> list) {
            return (List<Object>) list;
        }
        return List.of();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
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

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return "true".equalsIgnoreCase(stringValue(value));
    }
}
