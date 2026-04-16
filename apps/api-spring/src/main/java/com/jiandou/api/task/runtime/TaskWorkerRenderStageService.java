package com.jiandou.api.task.runtime;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.GenerationRunStatuses;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.application.TaskExecutionCoordinator;
import com.jiandou.api.task.domain.TaskArtifactNaming;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.persistence.TaskRepository;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 任务工作节点Render阶段服务。
 */
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

    /**
     * 渲染render。
     * @param task 要处理的任务对象
     * @param runContext 运行Context值
     * @param request 请求体
     * @return 处理结果
     */
    RenderStageResult render(TaskRecord task, TaskWorkerExecutionContext runContext, RenderStageRequest request) {
        List<String> imageRunIds = new ArrayList<>();
        List<String> videoRunIds = new ArrayList<>();
        String previousClipLastFrameUrl = request.previousClipLastFrameUrl();
        String latestVideoOutputUrl = "";
        if (request.reuseStoryboard() && request.renderStartIndex() > 1) {
            executionCoordinator.recordTrace(task, TaskStage.PLANNING.code(), "planning.keyframe_reused_for_resume", "检测到已有进度，跳过已完成镜头并从失败镜头继续。", "INFO", Map.of(
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
                executionCoordinator.recordTrace(task, TaskStage.PLANNING.code(), "planning.keyframe_reused_from_last_frame", "复用上一镜尾帧作为当前镜头首帧。", "INFO", Map.of(
                    "clipIndex", clipIndex,
                    "firstFrameUrl", firstFrameUrl,
                    "sourceLastFrameUrl", previousClipLastFrameUrl
                ));
                statusStageService.recordStageRun(
                    task,
                    runContext,
                    100 + clipIndex,
                    TaskStage.PLANNING.code(),
                    clipIndex,
                    Map.of(
                        "aspectRatio", task.aspectRatio(),
                        /**
                         * 处理truncate文本。
                         * @param clipPrompt 片段提示词值
                         * @param 160 160值
                         * @return 处理结果
                         */
                        "clipPrompt", truncateText(clipPrompt, 160),
                        "targetDurationSeconds", clipDurationSeconds
                    ),
                    Map.of(
                        "summary", "已复用上一镜尾帧作为首帧",
                        "imageRunId", "",
                        /**
                         * 处理string值。
                         * @param imageMaterial.get("fileUrl" 图像Material.get("fileUrl"值
                         * @return 处理结果
                         */
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
                Map<String, Object> imageModelCall = statusStageService.createModelCall(task, TaskStage.PLANNING.code(), "generation.image", imageRequest, imageRun, imageResult, clipIndex, GenerationModelKinds.IMAGE);
                executionCoordinator.recordModelCall(task, imageModelCall);
                statusStageService.recordRunCallChain(task, TaskStage.PLANNING.code(), imageRun, imageResult);
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
                    TaskStage.PLANNING.code(),
                    clipIndex,
                    Map.of(
                        "aspectRatio", task.aspectRatio(),
                        /**
                         * 处理truncate文本。
                         * @param clipPrompt 片段提示词值
                         * @param 160 160值
                         * @return 处理结果
                         */
                        "clipPrompt", truncateText(clipPrompt, 160),
                        "targetDurationSeconds", clipDurationSeconds
                    ),
                    Map.of(
                        "summary", "首帧关键画面已生成",
                        /**
                         * 处理string值。
                         * @param imageRun.get("id" 图像运行.get("标识"值
                         * @return 处理结果
                         */
                        "imageRunId", stringValue(imageRun.get("id")),
                        /**
                         * 处理string值。
                         * @param imageMaterial.get("fileUrl" 图像Material.get("fileUrl"值
                         * @return 处理结果
                         */
                        "imageUrl", stringValue(imageMaterial.get("fileUrl")),
                        "remoteImageUrl", firstFrameUrl
                    )
                );
            }
            if (index == Math.max(0, request.renderStartIndex() - 1)) {
                statusStageService.updateStatus(task, runContext, TaskStatus.RENDERING.value(), 55, TaskStage.RENDER.code(), "task.rendering", "任务开始按分镜生成视频输出。");
            } else {
                task.setProgress(Math.min(94, 55 + (int) Math.round(35.0 * index / Math.max(1, request.shotPlans().size()))));
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
            Map<String, Object> videoModelCall = statusStageService.createModelCall(task, TaskStage.RENDER.code(), "generation.video", videoRequest, videoRun, videoResult, clipIndex, GenerationModelKinds.VIDEO);
            executionCoordinator.recordModelCall(task, videoModelCall);
            statusStageService.recordRunCallChain(task, TaskStage.RENDER.code(), videoRun, videoResult);
            Map<String, Object> videoMaterial = artifactAssembler.createVideoMaterial(task, videoRun, videoResult, clipIndex, clipDurationSeconds);
            executionCoordinator.recordMaterial(task, videoMaterial);
            putExecutionContext(task, "videoOutputUrl", stringValue(videoMaterial.get("fileUrl")));
            latestVideoOutputUrl = stringValue(videoMaterial.get("fileUrl"));
            task.setCompletedOutputCount(Math.max(task.completedOutputCount(), clipIndex));
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
                TaskStage.RENDER.code(),
                clipIndex,
                Map.of(
                    /**
                     * 处理string值。
                     * @param imageRun.get("id" 图像运行.get("标识"值
                     * @return 处理结果
                     */
                    "imageRunId", stringValue(imageRun.get("id")),
                    /**
                     * 处理string值。
                     * @param imageMaterial.get("fileUrl" 图像Material.get("fileUrl"值
                     * @return 处理结果
                     */
                    "posterUrl", stringValue(imageMaterial.get("fileUrl")),
                    "targetDurationSeconds", clipDurationSeconds
                ),
                Map.of(
                    /**
                     * 处理string值。
                     * @param videoRun.get("id" 视频运行.get("标识"值
                     * @return 处理结果
                     */
                    "videoRunId", stringValue(videoRun.get("id")),
                    /**
                     * 处理string值。
                     * @param videoMaterial.get("fileUrl" 视频Material.get("fileUrl"值
                     * @return 处理结果
                     */
                    "outputUrl", stringValue(videoMaterial.get("fileUrl")),
                    /**
                     * 处理string值。
                     * @param videoMetadata.get("taskId" 视频Metadata.get("任务标识"值
                     * @return 处理结果
                     */
                    "remoteTaskId", stringValue(videoMetadata.get("taskId")),
                    "lastFrameUrl", resolvedLastFrameUrl
                )
            );
            executionCoordinator.recordTrace(task, TaskStage.RENDER.code(), "render.clip_completed", "当前分镜片段已生成完成。", "INFO", Map.of(
                "clipIndex", clipIndex,
                "clipCount", request.shotPlans().size(),
                /**
                 * 处理string值。
                 * @param videoMaterial.get("fileUrl" 视频Material.get("fileUrl"值
                 * @return 处理结果
                 */
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
        putExecutionContext(task, "clipImageRunIds", mergeStringListContext(task.executionContext().get("clipImageRunIds"), imageRunIds));
        putExecutionContext(task, "clipVideoRunIds", mergeStringListContext(task.executionContext().get("clipVideoRunIds"), videoRunIds));
        task.setCompletedOutputCount(request.shotPlans().size());
        putExecutionContext(task, "resumeExistingOutputCount", null);
        putExecutionContext(task, "resumeExistingClipIndices", null);
        putExecutionContext(task, "resumeRenderFromClipIndex", null);
        putExecutionContext(task, "attemptResumeFromStage", null);
        putExecutionContext(task, "attemptResumeFromClipIndex", null);
        taskRepository.save(task);
        return new RenderStageResult(imageRunIds, videoRunIds, latestVideoOutputUrl, request.shotPlans().size());
    }

    /**
     * 处理awaitCompleted视频运行。
     * @param initialRun 初始运行值
     * @return 处理结果
     */
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

    /**
     * 处理结果Map。
     * @param run 运行值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> resultMap(Map<String, Object> run) {
        Object result = run.get("result");
        if (result instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
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
     * 处理解析Latest视频输出URL。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private String resolveLatestVideoOutputUrl(TaskRecord task) {
        int latestClipIndex = 0;
        String latestOutputUrl = "";
        for (Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.get("resultType"))) {
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

    /**
     * 处理put执行Context。
     * @param task 要处理的任务对象
     * @param key key值
     * @param value 待处理的值
     */
    private void putExecutionContext(TaskRecord task, String key, Object value) {
        if (task.executionContext() == null) {
            task.setExecutionContext(new LinkedHashMap<>());
        }
        if (value == null) {
            task.executionContext().remove(key);
            return;
        }
        String normalized = value instanceof String str ? str.trim() : null;
        if (normalized != null && normalized.isEmpty()) {
            task.executionContext().remove(key);
            return;
        }
        task.executionContext().put(key, value);
    }

    /**
     * 处理mergeString列表Context。
     * @param existing existing值
     * @param appended appended值
     * @return 处理结果
     */
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

    /**
     * 处理文件NameFromURL。
     * @param url URL值
     * @return 处理结果
     */
    private String fileNameFromUrl(String url) {
        String normalized = stringValue(url)
            .replaceAll("[?#].*$", "")
            .replaceAll("/+$", "");
        int index = normalized.lastIndexOf('/');
        return index >= 0 ? normalized.substring(index + 1) : normalized;
    }

    /**
     * 处理文件ExtOr默认。
     * @param fileName 文件Name值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private String fileExtOrDefault(String fileName, String fallback) {
        String resolved = fileExt(fileName);
        return resolved.isBlank() ? fallback : resolved;
    }

    /**
     * 处理文件Ext。
     * @param fileName 文件Name值
     * @return 处理结果
     */
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
     * 处理truncate文本。
     * @param value 待处理的值
     * @param maxLength 最大Length值
     * @return 处理结果
     */
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

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param defaultValue 默认值
     * @return 处理结果
     */
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

    /**
     * 处理normalized运行状态。
     * @param run 运行值
     * @return 处理结果
     */
    private String normalizedRunStatus(Map<String, Object> run) {
        return stringValue(run == null ? null : run.get("status")).toLowerCase();
    }

    /**
     * 检查是否视频运行Active。
     * @param status 状态值
     * @return 是否满足条件
     */
    private boolean isVideoRunActive(String status) {
        return GenerationRunStatuses.isActive(status);
    }

    /**
     * 处理assert视频运行Succeeded。
     * @param run 运行值
     * @param status 状态值
     */
    private void assertVideoRunSucceeded(Map<String, Object> run, String status) {
        if (GenerationRunStatuses.isSuccessful(status)) {
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

    /**
     * 处理sleepBeforeNext视频Poll。
     */
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

    /**
     * 渲染阶段请求。
     * @param reuseStoryboard reuse分镜值
     * @param renderStartIndex renderStart索引值
     * @param completedClipCount completed片段数量值
     * @param requestedResumeStage requestedResume阶段值
     * @param requestedResumeClipIndex requestedResume片段索引值
     * @param existingVideoClipIndices existing视频片段Indices值
     * @param shotPlans shotPlans值
     * @param clipDurationPlan 片段时长规划值
     * @param width width值
     * @param height height值
     * @param durationSeconds 时长Seconds值
     * @param videoSize 视频Size值
     * @param previousClipLastFrameUrl previous片段LastFrameURL值
     * @return 处理结果
     */
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

    /**
     * 渲染阶段结果。
     * @param imageRunIds 图像运行标识列表值
     * @param videoRunIds 视频运行标识列表值
     * @param latestVideoOutputUrl latest视频输出URL值
     * @param clipCount 片段数量值
     * @return 处理结果
     */
    record RenderStageResult(
        List<String> imageRunIds,
        List<String> videoRunIds,
        String latestVideoOutputUrl,
        int clipCount
    ) {
    }
}
