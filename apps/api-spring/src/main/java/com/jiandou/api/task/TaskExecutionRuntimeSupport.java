package com.jiandou.api.task;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
final class TaskExecutionRuntimeSupport {

    private final TaskRepository taskRepository;

    TaskExecutionRuntimeSupport(TaskRepository taskRepository) {
        this.taskRepository = taskRepository;
    }

    Map<String, Object> activeAttempt(TaskRecord task) {
        if (task.activeAttemptId == null || task.activeAttemptId.isBlank()) {
            return null;
        }
        for (Map<String, Object> row : task.attemptsView()) {
            if (task.activeAttemptId.equals(stringValue(row.get("attemptId")))) {
                return row;
            }
        }
        return null;
    }

    int[] resolveDimensions(TaskRecord task) {
        String requestedVideoSize = task.requestSnapshot == null ? "" : stringValue(task.requestSnapshot.videoSize());
        if (!requestedVideoSize.isBlank()) {
            String normalized = requestedVideoSize.toLowerCase().replace("x", "*");
            String[] parts = normalized.split("\\*");
            if (parts.length == 2) {
                try {
                    return new int[] {Integer.parseInt(parts[0]), Integer.parseInt(parts[1])};
                } catch (NumberFormatException ignored) {
                }
            }
        }
        if ("16:9".equals(task.aspectRatio)) {
            return new int[] {1280, 720};
        }
        return new int[] {720, 1280};
    }

    int resolveDurationSeconds(TaskRecord task) {
        if (task.requestSnapshot != null && task.requestSnapshot.videoDuration() != null && !task.requestSnapshot.videoDuration().auto()) {
            Integer requestedSeconds = task.requestSnapshot.videoDuration().seconds();
            if (requestedSeconds != null) {
                return Math.max(1, requestedSeconds);
            }
        }
        if (task.maxDurationSeconds > 0) {
            return task.maxDurationSeconds;
        }
        if (task.minDurationSeconds > 0) {
            return task.minDurationSeconds;
        }
        return 8;
    }

    void assertTaskStillActive(TaskRecord task) {
        TaskRecord latest = taskRepository.findById(task.id);
        if (latest == null) {
            throw new TaskExecutionAbortedException("MISSING", "任务不存在，停止执行。");
        }
        if (isTaskExecutionActive(latest.status)) {
            return;
        }
        task.status = latest.status;
        task.progress = latest.progress;
        task.errorMessage = latest.errorMessage;
        task.finishedAt = latest.finishedAt;
        task.isQueued = latest.isQueued;
        task.queuePosition = latest.queuePosition;
        task.activeAttemptId = latest.activeAttemptId;
        task.executionContext = latest.executionContext;
        throw new TaskExecutionAbortedException(
            latest.status,
            latest.errorMessage == null || latest.errorMessage.isBlank() ? "任务已停止执行。" : latest.errorMessage
        );
    }

    Map<String, Object> buildScriptRunRequest(TaskRecord task) {
        String sourceText = !task.transcriptText.isBlank() ? task.transcriptText : (!task.creativePrompt.isBlank() ? task.creativePrompt : task.title);
        return Map.of(
            "kind", "script",
            "input", Map.of("text", sourceText),
            "model", Map.of("textAnalysisModel", textAnalysisModel(task)),
            "options", Map.of("visualStyle", "AI 自动决策"),
            "storage", Map.of(
                "relativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
                "fileName", TaskArtifactNaming.storyboardFileName(task, "md")
            )
        );
    }

    Map<String, Object> buildImageRunRequest(TaskRecord task, int clipIndex, String prompt, int width, int height, String referenceImageUrl) {
        return buildImageRunRequest(task, clipIndex, prompt, width, height, referenceImageUrl, 0, "first");
    }

    Map<String, Object> buildImageRunRequest(
        TaskRecord task,
        int clipIndex,
        String prompt,
        int width,
        int height,
        String referenceImageUrl,
        int durationSeconds,
        String frameRole
    ) {
        String normalizedFrameRole = normalizeFrameRole(frameRole);
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", prompt);
        input.put("width", width);
        input.put("height", height);
        input.put("frameRole", normalizedFrameRole);
        if (durationSeconds > 0) {
            input.put("durationSeconds", durationSeconds);
        }
        Integer taskSeed = taskSeed(task);
        if (taskSeed != null) {
            input.put("seed", taskSeed);
        }
        if (referenceImageUrl != null && !referenceImageUrl.isBlank()) {
            input.put("referenceImageUrl", referenceImageUrl);
        }
        return Map.of(
            "kind", "image",
            "input", input,
            "model", Map.of(
                "textAnalysisModel", textAnalysisModel(task),
                "providerModel", imageModel(task)
            ),
            "options", Map.of("stylePreset", stylePreset(task)),
            "storage", Map.of(
                "relativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
                "fileStem", "clip" + Math.max(1, clipIndex) + "-" + normalizedFrameRole
            )
        );
    }

    Map<String, Object> buildVideoRunRequest(
        TaskRecord task,
        int clipIndex,
        String prompt,
        String videoSize,
        int durationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds,
        String firstFrameUrl,
        String lastFrameUrl
    ) {
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", buildVideoClipExecutionPrompt(prompt));
        input.put("videoSize", videoSize);
        input.put("durationSeconds", durationSeconds);
        input.put("minDurationSeconds", minDurationSeconds);
        input.put("maxDurationSeconds", maxDurationSeconds);
        input.put("firstFrameUrl", firstFrameUrl);
        if (lastFrameUrl != null && !lastFrameUrl.isBlank()) {
            input.put("lastFrameUrl", lastFrameUrl);
        }
        input.put("generateAudio", true);
        input.put("returnLastFrame", true);
        Integer taskSeed = taskSeed(task);
        if (taskSeed != null) {
            input.put("seed", taskSeed);
        }
        return Map.of(
            "kind", "video",
            "input", input,
            "model", Map.of(
                "textAnalysisModel", textAnalysisModel(task),
                "visionModel", visionModel(task),
                "providerModel", videoModel(task)
            ),
            "options", Map.of("stylePreset", stylePreset(task)),
            "storage", Map.of(
                "relativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
                "fileStem", "clip" + Math.max(1, clipIndex)
            )
        );
    }

    private boolean isTaskExecutionActive(String status) {
        return "PENDING".equals(status)
            || "ANALYZING".equals(status)
            || "PLANNING".equals(status)
            || "RENDERING".equals(status);
    }

    private String buildVideoClipExecutionPrompt(String prompt) {
        return truncateText(prompt, 2200);
    }

    private String textAnalysisModel(TaskRecord task) {
        return requiredSnapshotModel(task, "textAnalysisModel", "文本模型");
    }

    private String imageModel(TaskRecord task) {
        return requiredSnapshotModel(task, "imageModel", "关键帧模型");
    }

    private String videoModel(TaskRecord task) {
        return requiredSnapshotModel(task, "videoModel", "视频模型");
    }

    private String visionModel(TaskRecord task) {
        return requiredSnapshotModel(task, "visionModel", "视觉模型");
    }

    private String stylePreset(TaskRecord task) {
        String configured = task.requestSnapshot == null ? "" : stringValue(task.requestSnapshot.stylePreset());
        return configured.isBlank() ? "cinematic" : configured;
    }

    private Integer taskSeed(TaskRecord task) {
        Integer configured = task.requestSnapshot == null ? null : task.requestSnapshot.seed();
        if (configured != null) {
            return configured;
        }
        return task == null ? null : task.taskSeed;
    }

    private String requiredSnapshotModel(TaskRecord task, String fieldName, String label) {
        String configured = task.requestSnapshot == null ? "" : stringValue(task.requestSnapshot.modelValue(fieldName));
        if (!configured.isBlank()) {
            return configured;
        }
        throw new IllegalStateException("任务缺少必选模型：" + label + "（" + fieldName + "）");
    }

    private String truncateText(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        String normalized = value.replace('\n', ' ').trim();
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, maxLength) + "...";
    }

    private String normalizeFrameRole(String frameRole) {
        return "last".equalsIgnoreCase(stringValue(frameRole)) ? "last" : "first";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }
}
