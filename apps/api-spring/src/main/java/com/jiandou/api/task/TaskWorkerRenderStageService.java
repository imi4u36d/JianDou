package com.jiandou.api.task;

import com.jiandou.api.generation.application.GenerationApplicationService;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
final class TaskWorkerRenderStageService {

    private static final long DEFAULT_VIDEO_RUN_POLL_INTERVAL_MILLIS = 1000L;
    private static final int DEFAULT_VIDEO_RUN_MAX_POLLS = 240;

    private final TaskRepository taskRepository;
    private final TaskExecutionCoordinator executionCoordinator;
    private final GenerationApplicationService generationApplicationService;
    private final TaskExecutionRuntimeSupport runtimeSupport;
    private final TaskExecutionArtifactAssembler artifactAssembler;
    private final TaskWorkerStatusStageService statusStageService;
    private final TaskWorkerJoinStageService joinStageService;
    private final long videoRunPollIntervalMillis;
    private final int videoRunMaxPolls;

    @Autowired
    TaskWorkerRenderStageService(
        TaskRepository taskRepository,
        TaskExecutionCoordinator executionCoordinator,
        GenerationApplicationService generationApplicationService,
        TaskExecutionRuntimeSupport runtimeSupport,
        TaskExecutionArtifactAssembler artifactAssembler,
        TaskWorkerStatusStageService statusStageService,
        TaskWorkerJoinStageService joinStageService
    ) {
        this(
            taskRepository,
            executionCoordinator,
            generationApplicationService,
            runtimeSupport,
            artifactAssembler,
            statusStageService,
            joinStageService,
            DEFAULT_VIDEO_RUN_POLL_INTERVAL_MILLIS,
            DEFAULT_VIDEO_RUN_MAX_POLLS
        );
    }

    TaskWorkerRenderStageService(
        TaskRepository taskRepository,
        TaskExecutionCoordinator executionCoordinator,
        GenerationApplicationService generationApplicationService,
        TaskExecutionRuntimeSupport runtimeSupport,
        TaskExecutionArtifactAssembler artifactAssembler,
        TaskWorkerStatusStageService statusStageService,
        TaskWorkerJoinStageService joinStageService,
        long videoRunPollIntervalMillis,
        int videoRunMaxPolls
    ) {
        this.taskRepository = taskRepository;
        this.executionCoordinator = executionCoordinator;
        this.generationApplicationService = generationApplicationService;
        this.runtimeSupport = runtimeSupport;
        this.artifactAssembler = artifactAssembler;
        this.statusStageService = statusStageService;
        this.joinStageService = joinStageService;
        this.videoRunPollIntervalMillis = Math.max(0L, videoRunPollIntervalMillis);
        this.videoRunMaxPolls = Math.max(1, videoRunMaxPolls);
    }

    RenderStageResult render(TaskRecord task, TaskWorkerExecutionContext runContext, RenderStageRequest request) {
        List<String> imageRunIds = new ArrayList<>();
        List<String> videoRunIds = new ArrayList<>();
        String previousClipLastFrameUrl = request.previousClipLastFrameUrl();
        String latestVideoOutputUrl = "";
        if (request.reuseStoryboard() && request.renderStartIndex() > 1) {
            executionCoordinator.recordTrace(task, "planning", "planning.keyframe_reused_for_resume", "检测到已有进度，跳过已完成镜头并从失败镜头继续。", "INFO", Map.of(
                "completedClipCount", request.completedClipCount(),
                "renderStartIndex", request.renderStartIndex(),
                "existingClipIndices", request.existingVideoClipIndices(),
                "lastFrameUrl", previousClipLastFrameUrl,
                "resumeFromStage", request.requestedResumeStage(),
                "resumeFromClipIndex", request.requestedResumeClipIndex()
            ));
        }

        for (int index = Math.max(0, request.renderStartIndex() - 1); index < request.shotPlans().size(); index++) {
            runtimeSupport.assertTaskStillActive(task);
            int clipIndex = index + 1;
            TaskStoryboardPlanner.StoryboardShotPlan shotPlan = request.shotPlans().get(index);
            String clipPrompt = shotPlan.videoPrompt();
            String firstFramePrompt = firstNonBlank(
                shotPlan.imagePrompt(),
                shotPlan.firstFramePrompt(),
                shotPlan.lastFramePrompt(),
                clipPrompt
            );
            int[] clipDuration = request.clipDurationPlan().get(index);
            int clipDurationSeconds = clipDuration[0];
            int clipMinDuration = clipDuration[1];
            int clipMaxDuration = clipDuration[2];
            Map<String, Object> imageRun = Map.of();
            Map<String, Object> imageResult = Map.of();
            Map<String, Object> imageMaterial;
            String firstFrameUrl;
            boolean reusePreviousLastFrame = clipIndex > 1 && !previousClipLastFrameUrl.isBlank();
            if (reusePreviousLastFrame) {
                // 连续镜头模式下，第 2 镜及以后直接复用上一镜尾帧作为首帧输入，不再额外发起关键帧生成。
                imageMaterial = artifactAssembler.createReferenceFrameMaterial(task, clipIndex, previousClipLastFrameUrl, "first");
                executionCoordinator.recordMaterial(task, imageMaterial);
                putExecutionContext(task, "imageRunId", null);
                putExecutionContext(task, "keyframeOutputUrl", stringValue(imageMaterial.get("fileUrl")));
                putExecutionContext(task, "keyframeRemoteSourceUrl", previousClipLastFrameUrl);
                taskRepository.save(task);
                firstFrameUrl = firstNonBlank(
                    stringValue(imageMaterial.get("remoteUrl")),
                    previousClipLastFrameUrl,
                    stringValue(imageMaterial.get("fileUrl"))
                );
                executionCoordinator.recordTrace(task, "planning", "planning.keyframe_reused_from_last_frame", "复用上一镜尾帧作为当前镜头首帧。", "INFO", Map.of(
                    "clipIndex", clipIndex,
                    "firstFrameUrl", firstFrameUrl,
                    "sourceLastFrameUrl", previousClipLastFrameUrl
                ));
                statusStageService.recordStageRun(
                    task,
                    runContext,
                    100 + clipIndex,
                    "planning",
                    clipIndex,
                    Map.of(
                        "aspectRatio", task.aspectRatio,
                        "clipPrompt", truncateText(clipPrompt, 160),
                        "targetDurationSeconds", clipDurationSeconds
                    ),
                    Map.of(
                        "summary", "已复用上一镜尾帧作为首帧",
                        "imageRunId", "",
                        "imageUrl", stringValue(imageMaterial.get("fileUrl")),
                        "remoteImageUrl", firstFrameUrl
                    )
                );
            } else {
                Map<String, Object> imageRequest = runtimeSupport.buildImageRunRequest(
                    task,
                    clipIndex,
                    firstFramePrompt,
                    request.width(),
                    request.height(),
                    previousClipLastFrameUrl,
                    clipDurationSeconds,
                    "first"
                );
                imageRun = generationApplicationService.createRun(imageRequest);
                runtimeSupport.assertTaskStillActive(task);
                imageResult = resultMap(imageRun);
                Map<String, Object> imageMetadata = mapValue(imageResult.get("metadata"));
                String keyframeSourceUrl = stringValue(imageMetadata.get("remoteSourceUrl"));
                if (keyframeSourceUrl.isBlank()) {
                    keyframeSourceUrl = stringValue(imageResult.get("outputUrl"));
                }
                putExecutionContext(task, "imageRunId", stringValue(imageRun.get("id")));
                putExecutionContext(task, "keyframeOutputUrl", stringValue(imageResult.get("outputUrl")));
                putExecutionContext(task, "keyframeRemoteSourceUrl", keyframeSourceUrl);
                taskRepository.save(task);
                Map<String, Object> imageModelCall = statusStageService.createModelCall(task, "planning", "generation.image", imageRequest, imageRun, imageResult, clipIndex, "image");
                executionCoordinator.recordModelCall(task, imageModelCall);
                statusStageService.recordRunCallChain(task, "planning", imageRun, imageResult);
                imageMaterial = artifactAssembler.createImageMaterial(task, imageRun, imageResult, clipIndex, "first");
                executionCoordinator.recordMaterial(task, imageMaterial);
                putExecutionContext(task, "keyframeOutputUrl", stringValue(imageMaterial.get("fileUrl")));
                imageRunIds.add(stringValue(imageRun.get("id")));
                taskRepository.save(task);
                firstFrameUrl = firstNonBlank(
                    keyframeSourceUrl,
                    stringValue(imageMaterial.get("remoteUrl")),
                    stringValue(imageMaterial.get("fileUrl")),
                    previousClipLastFrameUrl
                );
                statusStageService.recordStageRun(
                    task,
                    runContext,
                    100 + clipIndex,
                    "planning",
                    clipIndex,
                    Map.of(
                        "aspectRatio", task.aspectRatio,
                        "clipPrompt", truncateText(clipPrompt, 160),
                        "targetDurationSeconds", clipDurationSeconds
                    ),
                    Map.of(
                        "summary", "首帧关键画面已生成",
                        "imageRunId", stringValue(imageRun.get("id")),
                        "imageUrl", stringValue(imageMaterial.get("fileUrl")),
                        "remoteImageUrl", firstFrameUrl
                    )
                );
            }
            if (clipIndex == 1) {
                statusStageService.updateStatus(task, runContext, "RENDERING", 55, "render", "task.rendering", "任务开始按分镜生成视频输出。");
            } else {
                task.progress = Math.min(94, 55 + (int) Math.round(35.0 * index / Math.max(1, request.shotPlans().size())));
                taskRepository.save(task);
            }
            Map<String, Object> videoRequest = runtimeSupport.buildVideoRunRequest(
                task,
                clipIndex,
                clipPrompt,
                request.videoSize(),
                clipDurationSeconds,
                clipMinDuration,
                clipMaxDuration,
                firstFrameUrl,
                ""
            );
            Map<String, Object> videoRun = generationApplicationService.createRun(videoRequest);
            videoRun = awaitCompletedVideoRun(videoRun);
            runtimeSupport.assertTaskStillActive(task);
            Map<String, Object> videoResult = resultMap(videoRun);
            Map<String, Object> videoMetadata = mapValue(videoResult.get("metadata"));
            String resolvedLastFrameUrl = firstNonBlank(
                artifactAssembler.extractLastFrameUrl(videoResult),
                stringValue(videoMetadata.get("requestedLastFrameUrl"))
            );
            artifactAssembler.normalizeOptionalTaskArtifact(
                task,
                resolvedLastFrameUrl,
                TaskArtifactNaming.lastFrameFileName(clipIndex, fileExtOrDefault(fileNameFromUrl(resolvedLastFrameUrl), "png"))
            );
            putExecutionContext(task, "videoRunId", stringValue(videoRun.get("id")));
            putExecutionContext(task, "videoOutputUrl", stringValue(videoResult.get("outputUrl")));
            putExecutionContext(task, "videoThumbnailUrl", stringValue(videoResult.get("thumbnailUrl")));
            putExecutionContext(task, "firstFrameUrl", firstNonBlank(stringValue(videoMetadata.get("firstFrameUrl")), firstFrameUrl));
            putExecutionContext(task, "lastFrameUrl", resolvedLastFrameUrl);
            putExecutionContext(task, "videoRemoteTaskId", stringValue(videoMetadata.get("taskId")));
            putExecutionContext(task, "videoRemoteSourceUrl", stringValue(videoMetadata.get("remoteSourceUrl")));
            taskRepository.save(task);
            Map<String, Object> videoModelCall = statusStageService.createModelCall(task, "render", "generation.video", videoRequest, videoRun, videoResult, clipIndex, "video");
            executionCoordinator.recordModelCall(task, videoModelCall);
            statusStageService.recordRunCallChain(task, "render", videoRun, videoResult);
            Map<String, Object> videoMaterial = artifactAssembler.createVideoMaterial(task, videoRun, videoResult, clipIndex, clipDurationSeconds);
            executionCoordinator.recordMaterial(task, videoMaterial);
            putExecutionContext(task, "videoOutputUrl", stringValue(videoMaterial.get("fileUrl")));
            latestVideoOutputUrl = stringValue(videoMaterial.get("fileUrl"));
            task.completedOutputCount = Math.max(task.completedOutputCount, clipIndex);
            taskRepository.save(task);
            Map<String, Object> videoOutput = artifactAssembler.createResult(
                task,
                videoRun,
                videoResult,
                videoMaterial,
                imageMaterial,
                videoModelCall,
                resolvedLastFrameUrl,
                clipIndex,
                clipDurationSeconds,
                clipMinDuration,
                clipMaxDuration
            );
            executionCoordinator.recordResult(task, videoOutput);
            statusStageService.recordStageRun(
                task,
                runContext,
                200 + clipIndex,
                "render",
                clipIndex,
                Map.of(
                    "imageRunId", stringValue(imageRun.get("id")),
                    "posterUrl", stringValue(imageMaterial.get("fileUrl")),
                    "targetDurationSeconds", clipDurationSeconds
                ),
                Map.of(
                    "videoRunId", stringValue(videoRun.get("id")),
                    "outputUrl", stringValue(videoMaterial.get("fileUrl")),
                    "remoteTaskId", stringValue(videoMetadata.get("taskId")),
                    "lastFrameUrl", resolvedLastFrameUrl
                )
            );
            executionCoordinator.recordTrace(task, "render", "render.clip_completed", "当前分镜片段已生成完成。", "INFO", Map.of(
                "clipIndex", clipIndex,
                "clipCount", request.shotPlans().size(),
                "outputUrl", stringValue(videoMaterial.get("fileUrl")),
                "firstFrameUrl", firstFrameUrl,
                "lastFrameUrl", resolvedLastFrameUrl
            ));
            videoRunIds.add(stringValue(videoRun.get("id")));
            previousClipLastFrameUrl = stringValue(resolvedLastFrameUrl);
            joinStageService.scheduleJoin(task);
        }

        runtimeSupport.assertTaskStillActive(task);
        if (latestVideoOutputUrl.isBlank()) {
            latestVideoOutputUrl = resolveLatestVideoOutputUrl(task);
        }
        joinStageService.scheduleJoin(task);
        putExecutionContext(task, "clipImageRunIds", mergeStringListContext(task.executionContext.get("clipImageRunIds"), imageRunIds));
        putExecutionContext(task, "clipVideoRunIds", mergeStringListContext(task.executionContext.get("clipVideoRunIds"), videoRunIds));
        task.completedOutputCount = request.shotPlans().size();
        putExecutionContext(task, "resumeExistingOutputCount", null);
        putExecutionContext(task, "resumeExistingClipIndices", null);
        putExecutionContext(task, "resumeRenderFromClipIndex", null);
        putExecutionContext(task, "attemptResumeFromStage", null);
        putExecutionContext(task, "attemptResumeFromClipIndex", null);
        taskRepository.save(task);
        return new RenderStageResult(imageRunIds, videoRunIds, latestVideoOutputUrl, request.shotPlans().size());
    }

    Map<String, Object> awaitCompletedVideoRun(Map<String, Object> initialRun) {
        String currentStatus = normalizedRunStatus(initialRun);
        if (!isVideoRunActive(currentStatus)) {
            assertVideoRunSucceeded(initialRun, currentStatus);
            return initialRun;
        }
        String runId = stringValue(initialRun.get("id"));
        if (runId.isBlank()) {
            throw new IllegalStateException("video run is active but missing run id");
        }
        Map<String, Object> currentRun = initialRun;
        for (int poll = 0; poll < videoRunMaxPolls; poll++) {
            currentRun = generationApplicationService.getRun(runId);
            currentStatus = normalizedRunStatus(currentRun);
            if (!isVideoRunActive(currentStatus)) {
                assertVideoRunSucceeded(currentRun, currentStatus);
                return currentRun;
            }
            sleepBeforeNextVideoPoll();
        }
        throw new IllegalStateException(
            "video run wait timeout: runId=" + runId + ", status=" + currentStatus + ", maxPolls=" + videoRunMaxPolls
        );
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> resultMap(Map<String, Object> run) {
        Object result = run.get("result");
        if (result instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private String resolveLatestVideoOutputUrl(TaskRecord task) {
        int latestClipIndex = 0;
        String latestOutputUrl = "";
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            int clipIndex = intValue(output.get("clipIndex"), 0);
            if (clipIndex >= latestClipIndex) {
                latestClipIndex = clipIndex;
                latestOutputUrl = firstNonBlank(stringValue(output.get("downloadUrl")), stringValue(output.get("previewUrl")));
            }
        }
        return latestOutputUrl;
    }

    private void putExecutionContext(TaskRecord task, String key, Object value) {
        if (task.executionContext == null) {
            task.executionContext = new LinkedHashMap<>();
        }
        if (value == null) {
            task.executionContext.remove(key);
            return;
        }
        String normalized = value instanceof String str ? str.trim() : null;
        if (normalized != null && normalized.isEmpty()) {
            task.executionContext.remove(key);
            return;
        }
        task.executionContext.put(key, value);
    }

    private List<String> mergeStringListContext(Object existing, List<String> appended) {
        LinkedHashSet<String> merged = new LinkedHashSet<>();
        if (existing instanceof List<?> list) {
            for (Object item : list) {
                String value = stringValue(item);
                if (!value.isBlank()) {
                    merged.add(value);
                }
            }
        }
        for (String item : appended) {
            String value = stringValue(item);
            if (!value.isBlank()) {
                merged.add(value);
            }
        }
        return new ArrayList<>(merged);
    }

    private String fileNameFromUrl(String url) {
        String normalized = stringValue(url)
            .replaceAll("[?#].*$", "")
            .replaceAll("/+$", "");
        int index = normalized.lastIndexOf('/');
        return index >= 0 ? normalized.substring(index + 1) : normalized;
    }

    private String fileExtOrDefault(String fileName, String fallback) {
        String resolved = fileExt(fileName);
        return resolved.isBlank() ? fallback : resolved;
    }

    private String fileExt(String fileName) {
        String normalized = stringValue(fileName).replaceAll("[?#].*$", "");
        int index = normalized.lastIndexOf('.');
        if (index < 0 || index == normalized.length() - 1) {
            return "";
        }
        String candidate = normalized.substring(index + 1).toLowerCase();
        if (!candidate.matches("[a-z0-9]{1,10}")) {
            return "";
        }
        return candidate;
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
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

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    private String normalizedRunStatus(Map<String, Object> run) {
        return stringValue(run == null ? null : run.get("status")).toLowerCase();
    }

    private boolean isVideoRunActive(String status) {
        return "accepted".equals(status)
            || "queued".equals(status)
            || "submitted".equals(status)
            || "running".equals(status);
    }

    private void assertVideoRunSucceeded(Map<String, Object> run, String status) {
        if ("succeeded".equals(status) || "completed".equals(status) || "success".equals(status)) {
            return;
        }
        Map<String, Object> result = resultMap(run);
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String message = firstNonBlank(
            stringValue(result.get("error")),
            stringValue(metadata.get("taskMessage")),
            stringValue(metadata.get("message"))
        );
        throw new IllegalStateException(
            "video run did not complete successfully: runId=" + stringValue(run == null ? null : run.get("id"))
                + ", status=" + status
                + (message.isBlank() ? "" : ", error=" + message)
        );
    }

    private void sleepBeforeNextVideoPoll() {
        if (videoRunPollIntervalMillis <= 0L) {
            return;
        }
        try {
            Thread.sleep(videoRunPollIntervalMillis);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("video run wait interrupted", ex);
        }
    }

    record RenderStageRequest(
        boolean reuseStoryboard,
        int renderStartIndex,
        int completedClipCount,
        String requestedResumeStage,
        int requestedResumeClipIndex,
        List<Integer> existingVideoClipIndices,
        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans,
        List<int[]> clipDurationPlan,
        int width,
        int height,
        int durationSeconds,
        String videoSize,
        String previousClipLastFrameUrl
    ) {
    }

    record RenderStageResult(
        List<String> imageRunIds,
        List<String> videoRunIds,
        String latestVideoOutputUrl,
        int clipCount
    ) {
    }
}
