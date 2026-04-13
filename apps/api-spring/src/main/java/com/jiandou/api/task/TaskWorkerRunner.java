package com.jiandou.api.task;

import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.application.port.TaskQueuePort;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.DependsOn;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
@DependsOn("databaseSchemaReady")
public class TaskWorkerRunner implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(TaskWorkerRunner.class);
    private static final Pattern SCRIPT_DURATION_RANGE_PATTERN = Pattern.compile("(?<left>\\d{1,3}(?:\\.\\d+)?)\\s*(?:-|~|～|—|到)\\s*(?<right>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|秒)", Pattern.CASE_INSENSITIVE);
    private static final Pattern SCRIPT_DURATION_VALUE_PATTERN = Pattern.compile("(?<![\\d.])(?<value>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|秒)(?![a-zA-Z])", Pattern.CASE_INSENSITIVE);
    private static final Pattern SHOT_HEADING_PATTERN = Pattern.compile("^\\s*#{2,4}\\s*分镜\\s*(?<index>[0-9一二三四五六七八九十百千两]+)?\\s*[·\\-：:]*\\s*(?<title>.*)$");

    private final TaskRepository taskRepository;
    private final TaskQueuePort taskQueuePort;
    private final TaskExecutionCoordinator executionCoordinator;
    private final JoinOutputService joinOutputService;
    private final GenerationApplicationService generationApplicationService;
    private final LocalMediaArtifactService localMediaArtifactService;
    private final String executionMode;
    private final int staleWorkerTimeoutSeconds;
    private final String workerInstanceId = "spring_worker_" + UUID.randomUUID().toString().replace("-", "");
    private final String workerType = "spring_queue_worker";
    private ScheduledExecutorService pollExecutor;
    private ScheduledExecutorService maintenanceExecutor;
    private volatile boolean running;

    public TaskWorkerRunner(
        TaskRepository taskRepository,
        TaskQueuePort taskQueuePort,
        TaskExecutionCoordinator executionCoordinator,
        JoinOutputService joinOutputService,
        GenerationApplicationService generationApplicationService,
        LocalMediaArtifactService localMediaArtifactService,
        @Value("${JIANDOU_EXECUTION_MODE:queue}") String executionMode,
        @Value("${JIANDOU_WORKER_STALE_TIMEOUT_SECONDS:30}") int staleWorkerTimeoutSeconds
    ) {
        this.taskRepository = taskRepository;
        this.taskQueuePort = taskQueuePort;
        this.executionCoordinator = executionCoordinator;
        this.joinOutputService = joinOutputService;
        this.generationApplicationService = generationApplicationService;
        this.localMediaArtifactService = localMediaArtifactService;
        this.executionMode = executionMode == null ? "queue" : executionMode.trim().toLowerCase();
        this.staleWorkerTimeoutSeconds = Math.max(10, staleWorkerTimeoutSeconds);
    }

    @Override
    public void start() {
        if (running || !"queue".equals(executionMode)) {
            return;
        }
        running = true;
        executionCoordinator.upsertWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("executionMode", executionMode));
        pollExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "jiandou-spring-worker");
            thread.setDaemon(true);
            return thread;
        });
        maintenanceExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "jiandou-spring-worker-maintenance");
            thread.setDaemon(true);
            return thread;
        });
        pollExecutor.scheduleWithFixedDelay(this::pollOnce, 500, 1000, TimeUnit.MILLISECONDS);
        maintenanceExecutor.scheduleWithFixedDelay(this::maintenanceTick, 500, 2000, TimeUnit.MILLISECONDS);
    }

    @Override
    public void stop() {
        running = false;
        executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "STOPPED", Map.of("executionMode", executionMode));
        if (pollExecutor != null) {
            pollExecutor.shutdownNow();
            pollExecutor = null;
        }
        if (maintenanceExecutor != null) {
            maintenanceExecutor.shutdownNow();
            maintenanceExecutor = null;
        }
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public boolean isAutoStartup() {
        return true;
    }

    @Override
    public int getPhase() {
        return Integer.MAX_VALUE;
    }

    private void pollOnce() {
        try {
            String claimedTaskId = taskQueuePort.claimNext(workerInstanceId);
            if (claimedTaskId == null || claimedTaskId.isBlank()) {
                return;
            }
            processTask(claimedTaskId);
        } catch (Exception ex) {
            log.warn("worker poll failed: workerInstanceId={}", workerInstanceId, ex);
        }
    }

    private void maintenanceTick() {
        try {
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("executionMode", executionMode));
            executionCoordinator.recoverStaleClaims(OffsetDateTime.now(ZoneOffset.UTC).minusSeconds(staleWorkerTimeoutSeconds), 20);
        } catch (Exception ex) {
            log.warn("worker maintenance failed: workerInstanceId={}", workerInstanceId, ex);
        }
    }

    private void processTask(String taskId) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null) {
            taskQueuePort.remove(taskId);
            return;
        }
        if (!"PENDING".equals(task.status)) {
            taskQueuePort.remove(taskId);
            return;
        }
        try {
            taskQueuePort.remove(task.id);
            task.isQueued = false;
            task.queuePosition = null;
            if (task.startedAt == null || task.startedAt.isBlank()) {
                task.startedAt = nowIso();
            }
            assertTaskStillActive(task);
            Map<String, Object> activeAttempt = activeAttempt(task);
            int[] dimensions = resolveDimensions(task);
            int durationSeconds = resolveDurationSeconds(task);
            String videoSize = dimensions[0] + "*" + dimensions[1];
            List<Integer> existingVideoClipIndices = existingVideoClipIndices(task);
            int completedClipCount = lastContiguousCompletedClipIndex(existingVideoClipIndices);
            int renderStartIndex = Math.max(1, completedClipCount + 1);
            String requestedResumeStage = stringValue(activeAttempt == null ? null : activeAttempt.get("resumeFromStage"));
            int requestedResumeClipIndex = intValue(activeAttempt == null ? null : activeAttempt.get("resumeFromClipIndex"), renderStartIndex);
            boolean reuseStoryboard = !requestedResumeStage.isBlank() || completedClipCount > 0;
            putExecutionContext(task, "durationSeconds", durationSeconds);
            putExecutionContext(task, "videoSize", videoSize);
            putExecutionContext(task, "workerInstanceId", workerInstanceId);
            putExecutionContext(task, "resumeExistingClipIndices", existingVideoClipIndices);
            putExecutionContext(task, "resumeExistingOutputCount", completedClipCount);
            putExecutionContext(task, "resumeRenderFromClipIndex", renderStartIndex);
            putExecutionContext(task, "attemptResumeFromStage", requestedResumeStage);
            putExecutionContext(task, "attemptResumeFromClipIndex", requestedResumeClipIndex);
            taskRepository.save(task);

            executionCoordinator.markActiveAttemptRunning(task, workerInstanceId);
            assertTaskStillActive(task);
            Map<String, Object> scriptRun = Map.of();
            String storyboardMarkdown;
            if (reuseStoryboard && task.storyboardScript != null && !task.storyboardScript.isBlank()) {
                storyboardMarkdown = task.storyboardScript;
                executionCoordinator.recordTrace(task, "analysis", "analysis.reused", "检测到已有分镜脚本，跳过分析并继续后续镜头。", "INFO", Map.of(
                    "completedClipCount", completedClipCount,
                    "renderStartIndex", renderStartIndex,
                    "resumeFromStage", requestedResumeStage,
                    "resumeFromClipIndex", requestedResumeClipIndex
                ));
            } else {
                updateStatus(task, "ANALYZING", 10, "analysis", "task.analyzing", "任务开始分析文本与镜头约束。");

                Map<String, Object> scriptRequest = buildScriptRunRequest(task);
                scriptRun = generationApplicationService.createRun(scriptRequest);
                assertTaskStillActive(task);
                Map<String, Object> scriptResult = resultMap(scriptRun);
                storyboardMarkdown = stringValue(scriptResult.get("scriptMarkdown"));
                if (storyboardMarkdown.isBlank()) {
                    storyboardMarkdown = buildFallbackStoryboard(task, durationSeconds, dimensions[0], dimensions[1]);
                }
                task.storyboardScript = storyboardMarkdown;
                putExecutionContext(task, "analysisRunId", stringValue(scriptRun.get("id")));
                putExecutionContext(task, "scriptRunId", stringValue(scriptRun.get("id")));
                putExecutionContext(task, "analysisScriptText", storyboardMarkdown);
                putExecutionContext(task, "analysisPrompt", stringValue(scriptResult.get("prompt")));
                taskRepository.save(task);
                createStageRun(
                    task,
                    1,
                    "analysis",
                    1,
                    Map.of("title", task.title, "aspectRatio", task.aspectRatio),
                    Map.of("summary", "文本分析完成", "scriptRunId", stringValue(scriptRun.get("id")))
                );
                Map<String, Object> analysisModelCall = createModelCall(task, "analysis", "generation.script", scriptRequest, scriptRun, scriptResult, 1, "script");
                executionCoordinator.recordModelCall(task, analysisModelCall);
                recordRunCallChain(task, "analysis", scriptRun, scriptResult);
                Map<String, Object> scriptMaterial = createTextMaterial(task, scriptRun, scriptResult);
                executionCoordinator.recordMaterial(task, scriptMaterial);
                putExecutionContext(task, "storyboardFileUrl", stringValue(scriptMaterial.get("fileUrl")));
                taskRepository.save(task);
            }

            List<String> clipPrompts = buildSequentialClipPrompts(task, storyboardMarkdown);
            int storyboardClipCount = clipPrompts.size();
            int requestedOutputCount = resolveRequestedOutputCount(task, storyboardClipCount);
            if (requestedOutputCount < clipPrompts.size()) {
                clipPrompts = new ArrayList<>(clipPrompts.subList(0, requestedOutputCount));
            }
            List<int[]> clipDurationPlan = buildClipDurationPlan(task, durationSeconds, clipPrompts.size(), storyboardMarkdown);
            putExecutionContext(task, "storyboardClipCount", storyboardClipCount);
            putExecutionContext(task, "requestedOutputCount", requestSnapshotOutputCount(task));
            putExecutionContext(task, "plannedClipCount", clipPrompts.size());
            putExecutionContext(task, "clipPrompts", clipPrompts);
            taskRepository.save(task);
            executionCoordinator.recordTrace(task, "planning", "planning.shots_resolved", "已完成分镜数量解析，按镜头顺序生成。", "INFO", Map.of(
                "clipCount", clipPrompts.size(),
                "storyboardClipCount", storyboardClipCount,
                "requestedOutputCount", requestSnapshotOutputCount(task),
                "completedClipCount", completedClipCount,
                "renderStartIndex", renderStartIndex,
                "durationPlan", clipDurationPlan.stream().map(item -> Map.of(
                    "targetDurationSeconds", item[0],
                    "minDurationSeconds", item[1],
                    "maxDurationSeconds", item[2]
                )).toList()
            ));

            updateStatus(task, "PLANNING", 35, "planning", "task.planning", "任务开始按分镜生成关键画面。");
            List<String> imageRunIds = new ArrayList<>();
            List<String> videoRunIds = new ArrayList<>();
            String previousClipLastFrameUrl = resolveResumeLastFrameUrl(task, completedClipCount);
            String latestVideoOutputUrl = "";
            if (reuseStoryboard && renderStartIndex > 1) {
                executionCoordinator.recordTrace(task, "planning", "planning.keyframe_reused_for_resume", "检测到已有进度，跳过已完成镜头并从失败镜头继续。", "INFO", Map.of(
                    "completedClipCount", completedClipCount,
                    "renderStartIndex", renderStartIndex,
                    "existingClipIndices", existingVideoClipIndices,
                    "lastFrameUrl", previousClipLastFrameUrl,
                    "resumeFromStage", requestedResumeStage,
                    "resumeFromClipIndex", requestedResumeClipIndex
                ));
            }

            for (int index = Math.max(0, renderStartIndex - 1); index < clipPrompts.size(); index++) {
                assertTaskStillActive(task);
                int clipIndex = index + 1;
                String clipPrompt = clipPrompts.get(index);
                int[] clipDuration = clipDurationPlan.get(index);
                int clipDurationSeconds = clipDuration[0];
                int clipMinDuration = clipDuration[1];
                int clipMaxDuration = clipDuration[2];

                Map<String, Object> imageRequest = buildImageRunRequest(
                    task,
                    clipIndex,
                    clipPrompt,
                    dimensions[0],
                    dimensions[1],
                    previousClipLastFrameUrl,
                    clipDurationSeconds,
                    "first"
                );
                Map<String, Object> imageRun = generationApplicationService.createRun(imageRequest);
                assertTaskStillActive(task);
                Map<String, Object> imageResult = resultMap(imageRun);
                Map<String, Object> imageMetadata = mapValue(imageResult.get("metadata"));
                String keyframeSourceUrl = stringValue(imageMetadata.get("remoteSourceUrl"));
                if (keyframeSourceUrl.isBlank()) {
                    keyframeSourceUrl = stringValue(imageResult.get("outputUrl"));
                }
                putExecutionContext(task, "imageRunId", stringValue(imageRun.get("id")));
                putExecutionContext(task, "keyframeOutputUrl", stringValue(imageResult.get("outputUrl")));
                putExecutionContext(task, "keyframeRemoteSourceUrl", keyframeSourceUrl);
                taskRepository.save(task);
                Map<String, Object> imageModelCall = createModelCall(task, "planning", "generation.image", imageRequest, imageRun, imageResult, clipIndex, "image");
                executionCoordinator.recordModelCall(task, imageModelCall);
                recordRunCallChain(task, "planning", imageRun, imageResult);
                Map<String, Object> imageMaterial = createImageMaterial(task, imageRun, imageResult, clipIndex, "first");
                executionCoordinator.recordMaterial(task, imageMaterial);
                putExecutionContext(task, "keyframeOutputUrl", stringValue(imageMaterial.get("fileUrl")));
                imageRunIds.add(stringValue(imageRun.get("id")));
                taskRepository.save(task);
                String firstFrameUrl = firstNonBlank(keyframeSourceUrl, stringValue(imageMaterial.get("remoteUrl")), stringValue(imageMaterial.get("fileUrl")), previousClipLastFrameUrl);
                createStageRun(
                    task,
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

                if (clipIndex == 1) {
                    updateStatus(task, "RENDERING", 55, "render", "task.rendering", "任务开始按分镜生成视频输出。");
                } else {
                    task.progress = Math.min(94, 55 + (int) Math.round(35.0 * index / Math.max(1, clipPrompts.size())));
                    taskRepository.save(task);
                }
                Map<String, Object> videoRequest = buildVideoRunRequest(
                    task,
                    clipIndex,
                    clipPrompt,
                    videoSize,
                    clipDurationSeconds,
                    clipMinDuration,
                    clipMaxDuration,
                    firstFrameUrl
                );
                Map<String, Object> videoRun = generationApplicationService.createRun(videoRequest);
                assertTaskStillActive(task);
                Map<String, Object> videoResult = resultMap(videoRun);
                Map<String, Object> videoMetadata = mapValue(videoResult.get("metadata"));
                String resolvedLastFrameUrl = extractLastFrameUrl(videoResult);
                normalizeOptionalTaskArtifact(
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
                Map<String, Object> videoModelCall = createModelCall(task, "render", "generation.video", videoRequest, videoRun, videoResult, clipIndex, "video");
                executionCoordinator.recordModelCall(task, videoModelCall);
                recordRunCallChain(task, "render", videoRun, videoResult);
                Map<String, Object> videoMaterial = createVideoMaterial(task, videoRun, videoResult, clipIndex);
                executionCoordinator.recordMaterial(task, videoMaterial);
                putExecutionContext(task, "videoOutputUrl", stringValue(videoMaterial.get("fileUrl")));
                latestVideoOutputUrl = stringValue(videoMaterial.get("fileUrl"));
                task.completedOutputCount = Math.max(task.completedOutputCount, clipIndex);
                taskRepository.save(task);
                Map<String, Object> videoOutput = createResult(task, videoRun, videoResult, videoMaterial, imageMaterial, videoModelCall, resolvedLastFrameUrl, clipIndex);
                executionCoordinator.recordResult(task, videoOutput);
                createStageRun(
                    task,
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
                    "clipCount", clipPrompts.size(),
                    "outputUrl", stringValue(videoMaterial.get("fileUrl")),
                    "firstFrameUrl", firstFrameUrl,
                    "lastFrameUrl", resolvedLastFrameUrl
                ));
                videoRunIds.add(stringValue(videoRun.get("id")));
                previousClipLastFrameUrl = firstNonBlank(resolvedLastFrameUrl, previousClipLastFrameUrl);
                joinOutputService.scheduleJoin(task.id, maxVideoClipIndex(task));
            }

            assertTaskStillActive(task);
            if (latestVideoOutputUrl.isBlank()) {
                latestVideoOutputUrl = resolveLatestVideoOutputUrl(task);
            }
            if (maxVideoClipIndex(task) > 1) {
                joinOutputService.scheduleJoin(task.id, maxVideoClipIndex(task));
            }
            putExecutionContext(task, "clipImageRunIds", mergeStringListContext(task.executionContext.get("clipImageRunIds"), imageRunIds));
            putExecutionContext(task, "clipVideoRunIds", mergeStringListContext(task.executionContext.get("clipVideoRunIds"), videoRunIds));
            task.completedOutputCount = clipPrompts.size();
            putExecutionContext(task, "resumeExistingOutputCount", null);
            putExecutionContext(task, "resumeExistingClipIndices", null);
            putExecutionContext(task, "resumeRenderFromClipIndex", null);
            putExecutionContext(task, "attemptResumeFromStage", null);
            putExecutionContext(task, "attemptResumeFromClipIndex", null);
            String previousStatus = task.status;
            task.status = "COMPLETED";
            task.progress = 100;
            task.finishedAt = nowIso();
            executionCoordinator.markActiveAttemptFinished(task, "COMPLETED", "");
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("lastTaskId", task.id, "lastTaskStatus", "COMPLETED"));
            executionCoordinator.recordTrace(task, "pipeline", "task.completed", "Spring worker 已通过 generation 服务完成分镜视频生成。", "INFO", Map.of(
                "scriptRunId", stringValue(scriptRun.get("id")),
                "imageRunIds", imageRunIds,
                "videoRunIds", videoRunIds,
                "clipCount", clipPrompts.size(),
                "outputUrl", latestVideoOutputUrl
            ));
            executionCoordinator.recordStatusHistory(task, previousStatus, "COMPLETED", "pipeline", "task.completed", "任务执行完成。");
            taskRepository.save(task);
            executionCoordinator.recomputeQueuePositions(taskRepository.findAll());
        } catch (TaskExecutionAbortedException ex) {
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of(
                "lastTaskId", task.id,
                "lastTaskStatus", ex.taskStatus()
            ));
        } catch (Exception ex) {
            failTask(task, ex);
        }
    }

    private void updateStatus(TaskRecord task, String nextStatus, int progress, String stage, String event, String message) {
        String previousStatus = task.status;
        task.status = nextStatus;
        task.progress = progress;
        executionCoordinator.recordTrace(task, stage, event, message, "INFO", Map.of("workerInstanceId", workerInstanceId));
        executionCoordinator.recordStatusHistory(task, previousStatus, nextStatus, stage, event, message);
        taskRepository.save(task);
    }

    private void createStageRun(TaskRecord task, int seq, String stageName, int clipIndex, Map<String, Object> inputSummary, Map<String, Object> outputSummary) {
        Map<String, Object> row = new LinkedHashMap<>();
        String now = nowIso();
        row.put("stageRunId", stableId("stgrun", task.id, stageName, String.valueOf(clipIndex)));
        row.put("attemptId", task.activeAttemptId);
        row.put("stageName", stageName);
        row.put("stageSeq", seq);
        row.put("clipIndex", clipIndex);
        row.put("status", "COMPLETED");
        row.put("workerInstanceId", workerInstanceId);
        row.put("startedAt", now);
        row.put("finishedAt", now);
        row.put("durationMs", 0);
        row.put("inputSummary", inputSummary);
        row.put("outputSummary", outputSummary);
        row.put("errorCode", "");
        row.put("errorMessage", "");
        executionCoordinator.recordStageRun(task, row);
    }

    private Map<String, Object> createModelCall(
        TaskRecord task,
        String stage,
        String operation,
        Map<String, Object> requestPayload,
        Map<String, Object> run,
        Map<String, Object> result,
        int clipIndex,
        String kind
    ) {
        Map<String, Object> modelInfo = mapValue(result.get("modelInfo"));
        String now = nowIso();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", stableId("mdlcall", task.id, stage, kind, String.valueOf(clipIndex)));
        row.put("callKind", stage);
        row.put("stage", stage);
        row.put("operation", operation);
        row.put("provider", stringValue(modelInfo.getOrDefault("provider", "spring-placeholder")));
        row.put("providerModel", stringValue(modelInfo.get("providerModel")));
        row.put("requestedModel", stringValue(modelInfo.get("requestedModel")));
        row.put("resolvedModel", stringValue(modelInfo.get("resolvedModel")));
        row.put("modelName", stringValue(modelInfo.getOrDefault("modelName", modelInfo.get("resolvedModel"))));
        row.put("modelAlias", stringValue(modelInfo.getOrDefault("modelName", modelInfo.get("resolvedModel"))));
        row.put("endpointHost", stringValue(modelInfo.get("endpointHost")));
        row.put("requestId", stringValue(run.get("id")));
        row.put("requestPayload", requestPayload);
        row.put("responsePayload", Map.of("runId", stringValue(run.get("id")), "result", result));
        row.put("httpStatus", 200);
        row.put("responseCode", 200);
        row.put("success", true);
        row.put("errorCode", "");
        row.put("errorMessage", "");
        row.put("latencyMs", 0);
        row.put("inputTokens", 0);
        row.put("outputTokens", 0);
        row.put("startedAt", stringValue(run.getOrDefault("createdAt", now)));
        row.put("finishedAt", stringValue(run.getOrDefault("updatedAt", row.get("startedAt"))));
        return row;
    }

    private void recordRunCallChain(TaskRecord task, String fallbackStage, Map<String, Object> run, Map<String, Object> result) {
        Object raw = result.get("callChain");
        if (!(raw instanceof List<?> items)) {
            return;
        }
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            String stage = stringValue(map.get("stage"));
            String event = stringValue(map.get("event"));
            String message = stringValue(map.get("message"));
            String status = stringValue(map.get("status"));
            String level = "success".equalsIgnoreCase(status) ? "INFO" : "WARN";
            executionCoordinator.recordTrace(task,
                stage.isBlank() ? fallbackStage : stage,
                event.isBlank() ? "generation.call" : event,
                message.isBlank() ? "generation run completed" : message,
                level,
                Map.of(
                    "runId", stringValue(run.get("id")),
                    "status", status,
                    "details", mapValue(map.get("details"))
                )
            );
        }
    }

    private Map<String, Object> createTextMaterial(TaskRecord task, Map<String, Object> run, Map<String, Object> result) {
        String fileUrl = stringValue(result.get("markdownUrl"));
        LocalMediaArtifactService.StoredArtifact artifact = normalizeTaskArtifact(
            task,
            fileUrl,
            TaskArtifactNaming.storyboardFileName(task, fileExtOrDefault(fileNameFromUrl(fileUrl), "md")),
            "storyboard"
        );
        return createMaterial(
            task,
            run,
            "text",
            task.title + " 分镜脚本",
            artifact.publicUrl(),
            artifact.publicUrl(),
            stringValue(result.getOrDefault("mimeType", "text/markdown")),
            0.0,
            0,
            0,
            false,
            1,
            "storyboard",
            Map.of(),
            Map.of("taskArtifact", true),
            ""
        );
    }

    private Map<String, Object> createImageMaterial(TaskRecord task, Map<String, Object> run, Map<String, Object> result, int clipIndex, String frameRole) {
        String outputUrl = stringValue(result.get("outputUrl"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String normalizedFrameRole = normalizeFrameRole(frameRole);
        LocalMediaArtifactService.StoredArtifact artifact = normalizeTaskArtifact(
            task,
            outputUrl,
            TaskArtifactNaming.clipFrameFileName(clipIndex, normalizedFrameRole, fileExtOrDefault(fileNameFromUrl(outputUrl), "png")),
            "keyframe"
        );
        return createMaterial(
            task,
            run,
            "image",
            task.title + ("last".equals(normalizedFrameRole) ? " 尾帧关键画面" : " 首帧关键画面"),
            artifact.publicUrl(),
            artifact.publicUrl(),
            stringValue(result.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            false,
            clipIndex,
            "keyframe-" + normalizedFrameRole,
            metadata,
            Map.of(
                "taskArtifact", true,
                "clipIndex", clipIndex,
                "frameRole", normalizedFrameRole,
                "remoteSourceUrl", stringValue(metadata.get("remoteSourceUrl"))
            ),
            stringValue(metadata.get("remoteSourceUrl"))
        );
    }

    private Map<String, Object> createVideoMaterial(TaskRecord task, Map<String, Object> run, Map<String, Object> result, int clipIndex) {
        String outputUrl = stringValue(result.get("outputUrl"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        LocalMediaArtifactService.StoredArtifact artifact = normalizeTaskArtifact(
            task,
            outputUrl,
            TaskArtifactNaming.clipFileName(clipIndex, fileExtOrDefault(fileNameFromUrl(outputUrl), "mp4")),
            "clip"
        );
        return createMaterial(
            task,
            run,
            "video",
            task.title + " 片段输出",
            artifact.publicUrl(),
            artifact.publicUrl(),
            stringValue(result.getOrDefault("mimeType", "video/mp4")),
            doubleValue(result.get("durationSeconds"), (double) resolveDurationSeconds(task)),
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            boolValue(result.get("hasAudio")),
            clipIndex,
            "clip",
            metadata,
            Map.of(
                "taskArtifact", true,
                "clipIndex", clipIndex,
                "firstFrameUrl", stringValue(metadata.get("firstFrameUrl")),
                "lastFrameUrl", extractLastFrameUrl(result),
                "requestedLastFrameUrl", stringValue(metadata.get("requestedLastFrameUrl")),
                "remoteSourceUrl", stringValue(metadata.get("remoteSourceUrl"))
            ),
            stringValue(metadata.get("remoteSourceUrl"))
        );
    }

    private Map<String, Object> createMaterial(
        TaskRecord task,
        Map<String, Object> run,
        String mediaType,
        String title,
        String fileUrl,
        String previewUrl,
        String mimeType,
        double durationSeconds,
        int width,
        int height,
        boolean hasAudio,
        int clipIndex,
        String kind,
        Map<String, Object> sourceMetadata,
        Map<String, Object> extraMetadata,
        String remoteUrl
    ) {
        Map<String, Object> modelInfo = mapValue(resultMap(run).get("modelInfo"));
        String absolutePath = localMediaArtifactService.resolveAbsolutePath(fileUrl);
        String fileName = fileNameFromUrl(fileUrl);
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("taskId", task.id);
        metadata.put("kind", kind);
        metadata.put("clipIndex", clipIndex);
        metadata.put("runId", stringValue(run.get("id")));
        metadata.put("sourceMetadata", sourceMetadata == null ? Map.of() : sourceMetadata);
        metadata.putAll(extraMetadata == null ? Map.of() : extraMetadata);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", stableId("asset", task.id, kind, String.valueOf(clipIndex)));
        row.put("kind", kind);
        row.put("mediaType", mediaType);
        row.put("title", title);
        row.put("originProvider", stringValue(modelInfo.getOrDefault("provider", "spring-placeholder")));
        row.put("originModel", stringValue(modelInfo.getOrDefault("resolvedModel", modelInfo.get("providerModel"))));
        row.put("remoteTaskId", firstNonBlank(stringValue(sourceMetadata.get("taskId")), stringValue(run.get("id"))));
        row.put("remoteAssetId", "");
        row.put("originalFileName", fileName);
        row.put("storedFileName", fileName);
        row.put("fileExt", fileExt(fileName));
        row.put("storageProvider", "local");
        row.put("mimeType", mimeType);
        row.put("sizeBytes", fileSize(absolutePath));
        row.put("durationSeconds", durationSeconds);
        row.put("width", width);
        row.put("height", height);
        row.put("hasAudio", hasAudio);
        row.put("storagePath", absolutePath);
        row.put("localFilePath", absolutePath);
        row.put("fileUrl", fileUrl);
        row.put("previewUrl", previewUrl);
        row.put("remoteUrl", remoteUrl);
        row.put("metadata", metadata);
        row.put("createdAt", nowIso());
        return row;
    }

    private Map<String, Object> createResult(
        TaskRecord task,
        Map<String, Object> videoRun,
        Map<String, Object> videoResult,
        Map<String, Object> videoMaterial,
        Map<String, Object> imageMaterial,
        Map<String, Object> videoModelCall,
        String resolvedLastFrameUrl,
        int clipIndex
    ) {
        Map<String, Object> videoMetadata = mapValue(videoResult.get("metadata"));
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", stableId("result", task.id, "video", String.valueOf(clipIndex)));
        row.put("resultType", "video");
        row.put("clipIndex", clipIndex);
        row.put("title", task.title + " 成片输出 #" + clipIndex);
        row.put("reason", "Spring Boot worker 已按分镜顺序完成视频片段输出。");
        row.put("sourceModelCallId", stringValue(videoModelCall.get("modelCallId")));
        row.put("materialAssetId", videoMaterial.get("id"));
        row.put("startSeconds", 0.0);
        row.put("endSeconds", doubleValue(videoResult.get("durationSeconds"), (double) resolveDurationSeconds(task)));
        row.put("durationSeconds", doubleValue(videoResult.get("durationSeconds"), (double) resolveDurationSeconds(task)));
        row.put("previewUrl", stringValue(videoMaterial.get("previewUrl")));
        row.put("downloadUrl", stringValue(videoMaterial.get("fileUrl")));
        row.put("mimeType", stringValue(videoResult.getOrDefault("mimeType", "video/mp4")));
        row.put("width", intValue(videoResult.get("width"), 0));
        row.put("height", intValue(videoResult.get("height"), 0));
        row.put("sizeBytes", fileSize(localMediaArtifactService.resolveAbsolutePath(stringValue(videoMaterial.get("fileUrl")))));
        row.put("remoteUrl", stringValue(videoMetadata.get("remoteSourceUrl")));
        row.put("extra", Map.of(
            "runId", stringValue(videoRun.get("id")),
            "posterUrl", stringValue(imageMaterial.get("fileUrl")),
            "thumbnailUrl", stringValue(videoResult.get("thumbnailUrl")),
            "hasAudio", boolValue(videoResult.get("hasAudio")),
            "clipIndex", clipIndex,
            "remoteTaskId", stringValue(videoMetadata.get("taskId")),
            "firstFrameUrl", firstNonBlank(stringValue(videoMetadata.get("firstFrameUrl")), stringValue(imageMaterial.get("remoteUrl"))),
            "lastFrameUrl", resolvedLastFrameUrl,
            "requestedLastFrameUrl", stringValue(videoMetadata.get("requestedLastFrameUrl"))
        ));
        row.put("createdAt", nowIso());
        return row;
    }

    private LocalMediaArtifactService.StoredArtifact normalizeTaskArtifact(
        TaskRecord task,
        String sourceUrl,
        String targetFileName,
        String fallbackKind
    ) {
        String resolvedTargetFileName = stringValue(targetFileName);
        if (resolvedTargetFileName.isBlank()) {
            resolvedTargetFileName = switch (fallbackKind) {
                case "storyboard" -> TaskArtifactNaming.storyboardFileName(task, "bin");
                case "keyframe" -> TaskArtifactNaming.clipFrameFileName(1, "first", "bin");
                default -> TaskArtifactNaming.clipFileName(1, "bin");
            };
        }
        try {
            return localMediaArtifactService.materializeArtifact(
                sourceUrl,
                TaskArtifactNaming.taskRunningRelativeDir(task),
                resolvedTargetFileName
            );
        } catch (Exception ex) {
            throw new IllegalStateException(
                "task artifact materialize failed: taskId=" + stringValue(task == null ? null : task.id)
                    + ", targetFileName=" + resolvedTargetFileName
                    + ", sourceUrl=" + stringValue(sourceUrl),
                ex
            );
        }
    }

    private void normalizeOptionalTaskArtifact(TaskRecord task, String sourceUrl, String targetFileName) {
        if (stringValue(sourceUrl).isBlank() || stringValue(targetFileName).isBlank()) {
            return;
        }
        try {
            localMediaArtifactService.materializeArtifact(sourceUrl, TaskArtifactNaming.taskRunningRelativeDir(task), targetFileName);
        } catch (Exception ex) {
            log.debug(
                "skip optional task artifact normalization: taskId={}, sourceUrl={}, targetFileName={}",
                task == null ? "" : task.id,
                sourceUrl,
                targetFileName,
                ex
            );
        }
    }

    private String fileExtOrDefault(String fileName, String fallback) {
        String resolved = fileExt(fileName);
        return resolved.isBlank() ? fallback : resolved;
    }

    private String extractLastFrameUrl(Object value) {
        String direct = findNestedString(value, "lastFrameUrl", "last_frame_url");
        if (!direct.isBlank()) {
            return direct;
        }
        return findNestedRoleUrl(value, "last_frame");
    }

    @SuppressWarnings("unchecked")
    private String findNestedString(Object value, String... keys) {
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> map = (Map<String, Object>) rawMap;
            for (String key : keys) {
                Object candidate = map.get(key);
                if (candidate instanceof String text && !text.isBlank()) {
                    return text.trim();
                }
                if (candidate instanceof Map<?, ?> nestedMap) {
                    String nested = findNestedString(nestedMap, "url", "href", "uri");
                    if (!nested.isBlank()) {
                        return nested;
                    }
                }
            }
            for (Object nested : map.values()) {
                String resolved = findNestedString(nested, keys);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String resolved = findNestedString(item, keys);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private String findNestedRoleUrl(Object value, String role) {
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> map = (Map<String, Object>) rawMap;
            String currentRole = stringValue(map.get("role")).toLowerCase();
            if (role.equals(currentRole)) {
                Object imageUrl = map.get("image_url");
                if (imageUrl == null) {
                    imageUrl = map.get("imageUrl");
                }
                String resolved = findNestedString(imageUrl, "url", "href", "uri");
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
            for (Object nested : map.values()) {
                String resolved = findNestedRoleUrl(nested, role);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String resolved = findNestedRoleUrl(item, role);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        return "";
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private void failTask(TaskRecord task, Exception ex) {
        try {
            taskQueuePort.remove(task.id);
            task.isQueued = false;
            task.queuePosition = null;
            String previousStatus = task.status;
            task.status = "FAILED";
            task.errorMessage = ex.getMessage() == null ? "Spring worker 执行失败" : ex.getMessage();
            task.finishedAt = nowIso();
            executionCoordinator.markActiveAttemptFinished(task, "FAILED", task.errorMessage);
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("lastTaskId", task.id, "lastTaskStatus", "FAILED"));
            executionCoordinator.recordTrace(task, "pipeline", "task.failed", "Spring worker 执行失败。", "ERROR", Map.of("error", task.errorMessage));
            executionCoordinator.recordStatusHistory(task, previousStatus, "FAILED", "pipeline", "task.failed", task.errorMessage);
            taskRepository.save(task);
        } catch (Exception ignored) {
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "FAILED", Map.of("executionMode", executionMode));
        }
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    private static final class TaskExecutionAbortedException extends RuntimeException {

        private final String taskStatus;

        private TaskExecutionAbortedException(String taskStatus, String message) {
            super(message);
            this.taskStatus = taskStatus == null ? "" : taskStatus;
        }

        private String taskStatus() {
            return taskStatus;
        }
    }

    private Map<String, Object> activeAttempt(TaskRecord task) {
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

    private int[] resolveDimensions(TaskRecord task) {
        Object rawVideoSize = task.requestSnapshot.get("videoSize");
        if (rawVideoSize != null) {
            String normalized = String.valueOf(rawVideoSize).trim().toLowerCase().replace("x", "*");
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

    private int resolveDurationSeconds(TaskRecord task) {
        Object raw = task.requestSnapshot.get("videoDurationSeconds");
        if (raw instanceof Number number) {
            return Math.max(1, number.intValue());
        }
        if (raw != null) {
            String value = String.valueOf(raw).trim();
            if (!value.isEmpty() && !"auto".equalsIgnoreCase(value)) {
                try {
                    return Math.max(1, (int) Math.round(Double.parseDouble(value)));
                } catch (NumberFormatException ignored) {
                }
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

    private void assertTaskStillActive(TaskRecord task) {
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

    private boolean isTaskExecutionActive(String status) {
        return "PENDING".equals(status)
            || "ANALYZING".equals(status)
            || "PLANNING".equals(status)
            || "RENDERING".equals(status);
    }

    private Map<String, Object> buildScriptRunRequest(TaskRecord task) {
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

    private Map<String, Object> buildImageRunRequest(TaskRecord task, int clipIndex, String prompt, int width, int height, String referenceImageUrl) {
        return buildImageRunRequest(task, clipIndex, prompt, width, height, referenceImageUrl, 0, "first");
    }

    private Map<String, Object> buildImageRunRequest(
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
                "visionModel", visionModel(task),
                "providerModel", imageModel(task)
            ),
            "options", Map.of("stylePreset", stylePreset(task)),
            "storage", Map.of(
                "relativeDir", TaskArtifactNaming.taskRunningRelativeDir(task),
                "fileStem", "clip" + Math.max(1, clipIndex) + "-" + normalizedFrameRole
            )
        );
    }

    private Map<String, Object> buildVideoRunRequest(
        TaskRecord task,
        int clipIndex,
        String prompt,
        String videoSize,
        int durationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds,
        String firstFrameUrl
    ) {
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", buildVideoClipExecutionPrompt(prompt, clipIndex, durationSeconds, minDurationSeconds, maxDurationSeconds));
        input.put("videoSize", videoSize);
        input.put("durationSeconds", durationSeconds);
        input.put("minDurationSeconds", minDurationSeconds);
        input.put("maxDurationSeconds", maxDurationSeconds);
        input.put("firstFrameUrl", firstFrameUrl);
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

    private List<String> buildSequentialClipPrompts(TaskRecord task, String storyboardMarkdown) {
        String base = !task.creativePrompt.isBlank() ? task.creativePrompt : (!task.transcriptText.isBlank() ? task.transcriptText : task.title);
        List<String> shotPrompts = extractStoryboardShotPrompts(storyboardMarkdown);
        if (shotPrompts.isEmpty()) {
            return List.of(buildVisualPrompt(task, storyboardMarkdown));
        }
        List<String> prompts = new ArrayList<>();
        int total = shotPrompts.size();
        for (int index = 0; index < total; index++) {
            String continuityHint = index == 0 ? "建立场景与人物关系。" : "承接上一镜动作与情绪，衔接自然。";
            String composed = truncateText(
                """
                全片主题与上下文：
                %s

                当前任务：
                按剧情顺序仅生成第 %d/%d 镜，禁止跨镜头合并，禁止补写未给出的剧情。

                当前镜头拆解：
                %s

                执行要求：
                1. 画面描述必须具体到人物造型、动作过程、表情变化、视线方向、主体与环境关系、前景中景后景、道具、光线、氛围颗粒。
                2. 不要做长时间空镜、站桩、发呆、纯环境展示；镜头内必须有持续可见的动作或情绪推进。
                3. 如果镜头较长，必须让动作、调度、表情或构图产生阶段性变化，不能只有一个静止状态。
                4. 严格保留对白归属与剧情语义，不得把一句台词分配给错误角色。
                5. %s
                6. 音频要求：保留人物对白与环境音，禁止旁白、画外音、解说配音。
                """.formatted(base, index + 1, total, shotPrompts.get(index), continuityHint),
                1800
            );
            prompts.add(composed);
        }
        return prompts;
    }

    private int resolveRequestedOutputCount(TaskRecord task, int storyboardClipCount) {
        int availableClipCount = Math.max(1, storyboardClipCount);
        Object raw = task.requestSnapshot == null ? null : task.requestSnapshot.get("outputCount");
        if (raw == null) {
            return availableClipCount;
        }
        String normalized = String.valueOf(raw).trim();
        if (normalized.isBlank() || "auto".equalsIgnoreCase(normalized)) {
            return availableClipCount;
        }
        try {
            int requested = Integer.parseInt(normalized);
            return Math.max(1, Math.min(requested, availableClipCount));
        } catch (NumberFormatException ignored) {
            return availableClipCount;
        }
    }

    private Object requestSnapshotOutputCount(TaskRecord task) {
        if (task.requestSnapshot == null) {
            return "auto";
        }
        Object value = task.requestSnapshot.get("outputCount");
        return value == null ? "auto" : value;
    }

    private List<String> extractStoryboardShotPrompts(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<String> shotPrompts = new ArrayList<>();

        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.size() < 4 || isDividerRow(cells) || schema.isHeaderRow(cells)) {
                continue;
            }
            String first = schema.cell(cells, schema.shotNoIndex(), 0);
            if (first.isBlank() || first.contains("镜号") || first.toLowerCase().contains("shot")) {
                continue;
            }
            String shotIndex = first.replaceAll("[^0-9一二三四五六七八九十百千两]", "");
            if (shotIndex.isBlank()) {
                shotIndex = String.valueOf(shotPrompts.size() + 1);
            }
            String scene = schema.cell(cells, schema.sceneIndex(), 1);
            String shotSpec = schema.cell(cells, schema.shotSpecIndex(), 2);
            String movement = schema.cell(cells, schema.movementIndex(), 2);
            String camera = joinNonBlank(" / ", shotSpec, movement);
            String visual = schema.cell(cells, schema.visualIndex(), 3);
            String dialogue = stripNarrationVoiceoverText(schema.cell(cells, schema.dialogueIndex(), 4));
            String audio = schema.cell(cells, schema.audioIndex(), cells.size() > 5 ? 5 : 4);
            String durationHint = schema.cell(cells, schema.durationIndex(), cells.size() - 1);
            List<String> parts = new ArrayList<>();
            parts.add("镜头编号：" + shotIndex);
            if (!scene.isBlank()) {
                parts.add("剧情节点：" + scene);
            }
            if (!camera.isBlank()) {
                parts.add("镜头语言：" + camera);
            }
            if (!visual.isBlank()) {
                parts.add("画面描述：" + visual);
            }
            if (!dialogue.isBlank()) {
                parts.add("人物对白：" + dialogue);
            }
            if (!audio.isBlank()) {
                parts.add("声音设计：" + audio);
            }
            if (!durationHint.isBlank()) {
                parts.add("建议时长：" + durationHint);
            }
            shotPrompts.add(truncateText(String.join("\n", parts), 900));
        }
        if (!shotPrompts.isEmpty()) {
            return shotPrompts;
        }

        String currentTitle = "";
        List<String> currentLines = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            Matcher matcher = SHOT_HEADING_PATTERN.matcher(stripped);
            if (matcher.matches()) {
                flushHeadingShot(shotPrompts, currentTitle, currentLines);
                currentTitle = stringValue(matcher.group("title"));
                currentLines = new ArrayList<>();
                continue;
            }
            if (!currentTitle.isBlank()) {
                currentLines.add(rawLine);
            }
        }
        flushHeadingShot(shotPrompts, currentTitle, currentLines);
        return shotPrompts.isEmpty() ? List.of() : shotPrompts;
    }

    private void flushHeadingShot(List<String> shotPrompts, String currentTitle, List<String> currentLines) {
        String title = stringValue(currentTitle);
        String body = stripNarrationVoiceoverText(String.join(" ", currentLines).replaceAll("\\s+", " ").trim());
        String merged;
        if (!title.isBlank() && !body.isBlank()) {
            merged = "剧情节点：" + title + "；画面描述：" + body;
        } else if (!title.isBlank()) {
            merged = "剧情节点：" + title;
        } else {
            merged = body;
        }
        if (!merged.isBlank()) {
            shotPrompts.add(truncateText(merged, 900));
        }
    }

    private String buildVideoClipExecutionPrompt(
        String prompt,
        int clipIndex,
        int targetDurationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds
    ) {
        return truncateText(
            """
            当前生成第 %d 镜视频片段。
            目标时长：%d 秒。
            可接受时长范围：%d-%d 秒。

            内容密度要求：
            %s

            强约束：
            1. 严格执行下方镜头信息，不得偷换场景、人物、动作、服装、道具、情绪和对白归属。
            2. 画面必须尽量具体，明确人物外观、服装、发型、姿态、表情、动作起止、镜头运动、空间层次、环境细节、光影方向与质感。
            3. 禁止长时间空镜、静止镜、无意义停顿、只有背景没有主体动作、只有情绪没有可见动作。
            4. 时长越长，内容必须越充实；若时长超过 8 秒，画面中至少要有两段以上连续动作或情绪变化；若时长超过 12 秒，必须形成起势、推进、落点三段节奏。
            5. 动作和情绪必须连续推进，不能像 PPT 一样只给一个定格状态。

            镜头信息：
            %s
            """.formatted(
                clipIndex,
                targetDurationSeconds,
                minDurationSeconds,
                maxDurationSeconds,
                durationContentDensityGuide(targetDurationSeconds),
                prompt
            ),
            2200
        );
    }

    private String durationContentDensityGuide(int durationSeconds) {
        if (durationSeconds <= 6) {
            return "短时镜头也必须完整呈现一个明确动作事件，至少包含起势和结果，不允许用空镜填时长。";
        }
        if (durationSeconds <= 10) {
            return "中等时长镜头必须包含 2-3 个连续动作节拍或一次明显的情绪递进，主体行为不能单薄。";
        }
        return "长时镜头必须包含起势、推进、落点三段可见变化，动作、调度、表情或构图至少有两次明确变化。";
    }

    private List<int[]> buildClipDurationPlan(TaskRecord task, int defaultDurationSeconds, int clipCount, String storyboardMarkdown) {
        int normalizedClipCount = Math.max(1, clipCount);
        int totalMin = Math.max(1, task.minDurationSeconds > 0 ? task.minDurationSeconds : defaultDurationSeconds);
        int totalMax = Math.max(totalMin, task.maxDurationSeconds > 0 ? task.maxDurationSeconds : defaultDurationSeconds);
        int globalMin = Math.max(1, Math.round((float) totalMin / normalizedClipCount));
        int globalMax = Math.max(globalMin, Math.round((float) totalMax / normalizedClipCount));
        List<int[]> ranges = extractStoryboardShotDurationRanges(storyboardMarkdown);
        List<int[]> plan = new ArrayList<>();
        for (int index = 0; index < normalizedClipCount; index++) {
            int clipMin = index < ranges.size() ? ranges.get(index)[0] : globalMin;
            int clipMax = index < ranges.size() ? ranges.get(index)[1] : globalMax;
            clipMin = Math.max(globalMin, Math.min(globalMax, clipMin));
            clipMax = Math.max(clipMin, Math.min(globalMax, clipMax));
            int clipTarget = Math.max(clipMin, Math.min(clipMax, Math.round((clipMin + clipMax) / 2.0f)));
            plan.add(new int[] {clipTarget, clipMin, clipMax});
        }
        return plan;
    }

    private List<int[]> extractStoryboardShotDurationRanges(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<int[]> ranges = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.size() < 2 || isDividerRow(cells) || schema.isHeaderRow(cells)) {
                continue;
            }
            String first = schema.cell(cells, schema.shotNoIndex(), 0);
            if (first.isBlank() || first.contains("镜号") || first.toLowerCase().contains("shot")) {
                continue;
            }
            String durationCell = schema.cell(cells, schema.durationIndex(), cells.size() - 1);
            int[] parsed = parseDurationRangeHint(durationCell);
            if (parsed != null) {
                ranges.add(parsed);
            }
        }
        if (!ranges.isEmpty()) {
            return ranges;
        }
        Matcher matcher = SCRIPT_DURATION_RANGE_PATTERN.matcher(normalized);
        while (matcher.find()) {
            int[] parsed = parseDurationRangeHint(matcher.group());
            if (parsed != null) {
                ranges.add(parsed);
            }
        }
        return ranges;
    }

    private int[] parseDurationRangeHint(String text) {
        String normalized = stringValue(text);
        if (normalized.isBlank()) {
            return null;
        }
        Matcher rangeMatcher = SCRIPT_DURATION_RANGE_PATTERN.matcher(normalized);
        if (rangeMatcher.find()) {
            int left = safeRoundedSeconds(rangeMatcher.group("left"));
            int right = safeRoundedSeconds(rangeMatcher.group("right"));
            int low = Math.max(1, Math.min(left, right));
            int high = Math.max(low, Math.max(left, right));
            return new int[] {low, high};
        }
        Matcher valueMatcher = SCRIPT_DURATION_VALUE_PATTERN.matcher(normalized);
        if (valueMatcher.find()) {
            int value = safeRoundedSeconds(valueMatcher.group("value"));
            return new int[] {value, value};
        }
        return null;
    }

    private int safeRoundedSeconds(String value) {
        try {
            return Math.max(1, Math.min(120, (int) Math.round(Double.parseDouble(stringValue(value)))));
        } catch (NumberFormatException ex) {
            return 1;
        }
    }

    private List<String> splitTableRow(String row) {
        String trimmed = row.trim();
        if (!trimmed.startsWith("|")) {
            return List.of();
        }
        String[] parts = trimmed.substring(1, trimmed.endsWith("|") ? trimmed.length() - 1 : trimmed.length()).split("\\|");
        List<String> cells = new ArrayList<>();
        for (String part : parts) {
            cells.add(part.trim());
        }
        return cells;
    }

    private StoryboardTableSchema detectStoryboardTableSchema(List<String> lines) {
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.isEmpty() || isDividerRow(cells)) {
                continue;
            }
            if (looksLikeHeaderRow(cells)) {
                return StoryboardTableSchema.fromHeader(cells);
            }
        }
        return StoryboardTableSchema.empty();
    }

    private boolean looksLikeHeaderRow(List<String> cells) {
        for (String cell : cells) {
            String normalized = normalizeStoryboardHeader(cell);
            if (normalized.contains("shot") || normalized.contains("镜号") || normalized.contains("景别")
                || normalized.contains("运镜") || normalized.contains("画面") || normalized.contains("visual")
                || normalized.contains("audio") || normalized.contains("duration") || normalized.contains("时长")) {
                return true;
            }
        }
        return false;
    }

    private String normalizeStoryboardHeader(String text) {
        return stringValue(text)
            .trim()
            .toLowerCase()
            .replaceAll("[\\s_\\-()（）/\\\\+:：·,.，]", "");
    }

    private Integer resolveStoryboardColumnIndex(List<String> headers, String... aliases) {
        for (int index = 0; index < headers.size(); index++) {
            String header = normalizeStoryboardHeader(headers.get(index));
            for (String alias : aliases) {
                if (header.contains(alias)) {
                    return index;
                }
            }
        }
        return null;
    }

    private String joinNonBlank(String delimiter, String... values) {
        List<String> parts = new ArrayList<>();
        for (String value : values) {
            String normalized = stringValue(value);
            if (!normalized.isBlank()) {
                parts.add(normalized);
            }
        }
        return String.join(delimiter, parts);
    }

    private record StoryboardTableSchema(
        List<String> headerCells,
        Integer shotNoIndex,
        Integer sceneIndex,
        Integer shotSpecIndex,
        Integer movementIndex,
        Integer visualIndex,
        Integer dialogueIndex,
        Integer audioIndex,
        Integer durationIndex
    ) {
        static StoryboardTableSchema empty() {
            return new StoryboardTableSchema(List.of(), null, null, null, null, null, null, null, null);
        }

        static StoryboardTableSchema fromHeader(List<String> headers) {
            return new StoryboardTableSchema(
                List.copyOf(headers),
                resolve(headers, "shotno", "shot", "镜号"),
                resolve(headers, "剧情节点", "场景", "scene"),
                resolve(headers, "shotspec", "景别角度", "景别", "镜头语言", "shotsize", "angle"),
                resolve(headers, "movement", "运镜"),
                resolve(headers, "visualcontent", "视觉描述", "画面细节描述", "画面描述", "visualprompt", "visual"),
                resolve(headers, "dialogue", "对白", "台词", "字幕"),
                resolve(headers, "audio", "音效", "bgm", "sfx", "旁白", "画外音"),
                resolve(headers, "duration", "时长", "秒")
            );
        }

        private static Integer resolve(List<String> headers, String... aliases) {
            for (int index = 0; index < headers.size(); index++) {
                String header = headers.get(index)
                    .trim()
                    .toLowerCase()
                    .replaceAll("[\\s_\\-()（）/\\\\+:：·,.，]", "");
                for (String alias : aliases) {
                    if (header.contains(alias)) {
                        return index;
                    }
                }
            }
            return null;
        }

        boolean isHeaderRow(List<String> cells) {
            if (headerCells.isEmpty() || cells.size() != headerCells.size()) {
                return false;
            }
            for (int index = 0; index < cells.size(); index++) {
                String left = cells.get(index).trim();
                String right = headerCells.get(index).trim();
                if (!left.equalsIgnoreCase(right)) {
                    return false;
                }
            }
            return true;
        }

        String cell(List<String> cells, Integer index, int fallbackIndex) {
            int resolvedIndex = index != null ? index : fallbackIndex;
            if (resolvedIndex < 0 || resolvedIndex >= cells.size()) {
                return "";
            }
            Object value = cells.get(resolvedIndex);
            return value == null ? "" : String.valueOf(value).trim();
        }
    }

    private boolean isDividerRow(List<String> cells) {
        for (String cell : cells) {
            if (!cell.matches("[:\\-\\s]*")) {
                return false;
            }
        }
        return true;
    }

    private String stripNarrationVoiceoverText(String text) {
        String normalized = stringValue(text);
        String lowered = normalized.toLowerCase();
        if (!(normalized.contains("旁白") || normalized.contains("画外音") || normalized.contains("解说")
            || lowered.contains("narration") || lowered.contains("voiceover") || lowered.contains("voice over"))) {
            return normalized;
        }
        String cleaned = normalized.replaceAll("[（(]\\s*(?:旁白|画外音|解说|narration|voice\\s*over|voiceover)\\s*[)）]\\s*[:：]?\\s*", "");
        String[] segments = cleaned.split("[；;。!！?？\\n]+");
        List<String> kept = new ArrayList<>();
        for (String segment : segments) {
            String candidate = segment.trim();
            String loweredCandidate = candidate.toLowerCase();
            if (candidate.isBlank()) {
                continue;
            }
            if (candidate.contains("旁白") || candidate.contains("画外音") || candidate.contains("解说")
                || loweredCandidate.contains("narration") || loweredCandidate.contains("voiceover") || loweredCandidate.contains("voice over")) {
                continue;
            }
            kept.add(candidate);
        }
        return String.join("；", kept).replaceAll("^[，,；;。\\s]+|[，,；;。\\s]+$", "");
    }

    private String buildVisualPrompt(TaskRecord task, String storyboardMarkdown) {
        String base = !task.creativePrompt.isBlank() ? task.creativePrompt : (!task.transcriptText.isBlank() ? task.transcriptText : task.title);
        String storyboardSnippet = truncateText(storyboardMarkdown, 280);
        return truncateText(base + "\n\n参考分镜语义：" + storyboardSnippet, 640);
    }

    private String buildFallbackStoryboard(TaskRecord task, int durationSeconds, int width, int height) {
        return String.join("\n",
            "# 分镜脚本",
            "",
            "- 任务标题: " + task.title,
            "- 画幅: " + task.aspectRatio + " (" + width + "x" + height + ")",
            "- 时长: " + durationSeconds + " 秒",
            "",
            "## 场景摘要",
            truncateText(!task.creativePrompt.isBlank() ? task.creativePrompt : task.transcriptText, 360)
        );
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
        String configured = stringValue(task.requestSnapshot.get("stylePreset"));
        return configured.isBlank() ? "cinematic" : configured;
    }

    private Integer taskSeed(TaskRecord task) {
        Integer configured = integerValue(task.requestSnapshot.get("seed"));
        if (configured != null) {
            return configured;
        }
        return task == null ? null : task.taskSeed;
    }

    private long fileSize(String absolutePath) {
        if (absolutePath == null || absolutePath.isBlank()) {
            return 0L;
        }
        try {
            Path path = Path.of(absolutePath);
            return Files.exists(path) ? Files.size(path) : 0L;
        } catch (IOException ex) {
            return 0L;
        }
    }

    private String fileNameFromUrl(String url) {
        String normalized = stringValue(url);
        int index = normalized.lastIndexOf('/');
        return index >= 0 ? normalized.substring(index + 1) : normalized;
    }

    private String fileExt(String fileName) {
        int index = fileName.lastIndexOf('.');
        if (index < 0 || index == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(index + 1).toLowerCase();
    }

    private String requiredSnapshotModel(TaskRecord task, String fieldName, String label) {
        String configured = stringValue(task.requestSnapshot.get(fieldName));
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

    private double doubleValue(Object value, double defaultValue) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value != null) {
            try {
                return Double.parseDouble(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
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

    private String stableId(String prefix, String... parts) {
        String seed = prefix + ":" + String.join(":", parts);
        return prefix + "_" + UUID.nameUUIDFromBytes(seed.getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
    }

    private String normalizeFrameRole(String frameRole) {
        return "last".equalsIgnoreCase(stringValue(frameRole)) ? "last" : "first";
    }

    private String twoDigit(int value) {
        return value < 10 ? "0" + value : String.valueOf(value);
    }

    private int maxVideoClipIndex(TaskRecord task) {
        int max = 0;
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            max = Math.max(max, intValue(output.get("clipIndex"), 0));
        }
        return max;
    }

    private List<Integer> existingVideoClipIndices(TaskRecord task) {
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

    private int lastContiguousCompletedClipIndex(List<Integer> clipIndices) {
        int expected = 1;
        for (Integer clipIndex : clipIndices) {
            if (clipIndex == null) {
                continue;
            }
            if (clipIndex != expected) {
                break;
            }
            expected += 1;
        }
        return expected - 1;
    }

    private String resolveResumeLastFrameUrl(TaskRecord task, int completedClipCount) {
        String stored = stringValue(task.executionContext.get("lastFrameUrl"));
        if (!stored.isBlank()) {
            return stored;
        }
        if (completedClipCount <= 0) {
            return "";
        }
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            if (intValue(output.get("clipIndex"), 0) != completedClipCount) {
                continue;
            }
            Map<String, Object> extra = mapValue(output.get("extra"));
            return firstNonBlank(stringValue(extra.get("lastFrameUrl")), stringValue(extra.get("firstFrameUrl")));
        }
        return "";
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
}
