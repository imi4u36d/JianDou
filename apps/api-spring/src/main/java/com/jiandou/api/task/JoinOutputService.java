package com.jiandou.api.task;

import com.jiandou.api.media.LocalMediaArtifactService;
import jakarta.annotation.PreDestroy;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class JoinOutputService {

    private static final Logger log = LoggerFactory.getLogger(JoinOutputService.class);
    private static final int JOIN_OUTPUT_CLIP_INDEX_BASE = 10000;

    private final TaskRepository taskRepository;
    private final TaskExecutionCoordinator executionCoordinator;
    private final LocalMediaArtifactService localMediaArtifactService;
    private final ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
        Thread thread = new Thread(r, "jiandou-join-worker");
        thread.setDaemon(true);
        return thread;
    });
    private final Map<String, Integer> pendingTargets = new ConcurrentHashMap<>();
    private final Set<String> runningTasks = ConcurrentHashMap.newKeySet();
    private final String joinWorkerInstanceId = "spring_join_worker_" + UUID.randomUUID().toString().replace("-", "");

    public JoinOutputService(
        TaskRepository taskRepository,
        TaskExecutionCoordinator executionCoordinator,
        LocalMediaArtifactService localMediaArtifactService
    ) {
        this.taskRepository = taskRepository;
        this.executionCoordinator = executionCoordinator;
        this.localMediaArtifactService = localMediaArtifactService;
    }

    public void scheduleJoin(String taskId, int endClipIndex) {
        if (taskId == null || taskId.isBlank() || endClipIndex < 2) {
            return;
        }
        pendingTargets.merge(taskId, endClipIndex, Math::max);
        if (runningTasks.add(taskId)) {
            executor.submit(() -> processTask(taskId));
        }
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdownNow();
    }

    private void processTask(String taskId) {
        try {
            while (true) {
                Integer target = pendingTargets.remove(taskId);
                if (target == null || target < 2) {
                    return;
                }
                try {
                    buildJoinOutput(taskId, target);
                } catch (Exception ex) {
                    log.warn("join output build failed: taskId={}, target={}", taskId, target, ex);
                    TaskRecord task = taskRepository.findById(taskId);
                    if (task != null) {
                        executionCoordinator.recordTrace(
                            task,
                            "render",
                            "render.join_failed",
                            "Spring join worker 拼接输出失败。",
                            "WARN",
                            Map.of(
                                "targetClipIndex", target,
                                "joinName", joinOutputName(target),
                                "error", ex.getMessage() == null ? "" : ex.getMessage()
                            )
                        );
                    }
                }
            }
        } finally {
            runningTasks.remove(taskId);
            if (pendingTargets.containsKey(taskId) && runningTasks.add(taskId)) {
                executor.submit(() -> processTask(taskId));
            }
        }
    }

    private void buildJoinOutput(String taskId, int endClipIndex) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null || endClipIndex < 2) {
            return;
        }
        if (!shouldProcessJoin(task)) {
            return;
        }
        List<Map<String, Object>> clipResults = collectClipResults(task, endClipIndex);
        if (clipResults.size() < endClipIndex) {
            return;
        }
        String joinName = joinOutputName(endClipIndex);
        String outputFileName = TaskArtifactNaming.joinFileName(task, endClipIndex, "mp4");
        List<Integer> clipIndices = uniqueClipIndices(clipResults);
        List<String> segmentUrls = clipResults.stream()
            .map(this::resultOutputUrl)
            .filter(url -> !url.isBlank())
            .toList();
        if (segmentUrls.size() < endClipIndex) {
            return;
        }
        LocalMediaArtifactService.StoredArtifact artifact = localMediaArtifactService.concatVideos(
            TaskArtifactNaming.taskJoinedRelativeDir(task),
            outputFileName,
            segmentUrls
        );
        int joinClipIndex = JOIN_OUTPUT_CLIP_INDEX_BASE + endClipIndex;
        double durationSeconds = clipResults.stream().mapToDouble(item -> doubleValue(item.get("durationSeconds"), 0.0)).sum();
        int width = intValue(clipResults.get(0).get("width"), 0);
        int height = intValue(clipResults.get(0).get("height"), 0);
        boolean hasAudio = clipResults.stream().anyMatch(item -> boolValue(mapValue(item.get("extra")).get("hasAudio")));

        Map<String, Object> modelCall = createJoinModelCall(task, joinName, endClipIndex, clipIndices, segmentUrls, artifact.publicUrl());
        executionCoordinator.recordModelCall(task, modelCall);

        Map<String, Object> material = createJoinMaterial(task, joinName, clipIndices, artifact, segmentUrls, durationSeconds, width, height, hasAudio);
        executionCoordinator.recordMaterial(task, material);

        Map<String, Object> result = createJoinResult(task, joinName, joinClipIndex, modelCall, material, artifact, clipIndices, segmentUrls, durationSeconds, width, height, hasAudio);
        executionCoordinator.recordResult(task, result);

        executionCoordinator.recordStageRun(task, createJoinStageRun(task, joinName, joinClipIndex, clipIndices, segmentUrls, artifact.publicUrl(), material, result));
        executionCoordinator.recordTrace(task, "render", "render.join_completed", "Spring join worker 已完成拼接输出。", "INFO", Map.of(
            "joinName", joinName,
            "clipIndex", joinClipIndex,
            "targetClipIndex", endClipIndex,
            "clipIndices", clipIndices,
            "durationSeconds", durationSeconds,
            "hasAudio", hasAudio,
            "outputUrl", artifact.publicUrl()
        ));
        if (task.executionContext == null) {
            task.executionContext = new LinkedHashMap<>();
        }
        task.executionContext.put("latestJoinName", joinName);
        task.executionContext.put("latestJoinOutputUrl", artifact.publicUrl());
        task.executionContext.put("latestJoinClipIndex", joinClipIndex);
        task.executionContext.put("latestJoinClipIndices", clipIndices);
        taskRepository.save(task);
    }

    private boolean shouldProcessJoin(TaskRecord task) {
        if (task == null) {
            return false;
        }
        return "RENDERING".equals(task.status) || "COMPLETED".equals(task.status);
    }

    private List<Map<String, Object>> collectClipResults(TaskRecord task, int endClipIndex) {
        Map<Integer, Map<String, Object>> clipResults = new LinkedHashMap<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            int clipIndex = intValue(output.get("clipIndex"), 0);
            if (clipIndex < 1 || clipIndex > endClipIndex) {
                continue;
            }
            clipResults.put(clipIndex, output);
        }
        List<Map<String, Object>> ordered = new ArrayList<>(clipResults.values());
        ordered.sort(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)));
        if (ordered.size() != endClipIndex) {
            return List.of();
        }
        for (int index = 0; index < ordered.size(); index++) {
            if (intValue(ordered.get(index).get("clipIndex"), 0) != index + 1) {
                return List.of();
            }
        }
        return ordered;
    }

    private String resultOutputUrl(Map<String, Object> result) {
        String downloadUrl = stringValue(result.get("downloadUrl"));
        if (!downloadUrl.isBlank()) {
            return downloadUrl;
        }
        return stringValue(result.get("previewUrl"));
    }

    private Map<String, Object> createJoinModelCall(
        TaskRecord task,
        String joinName,
        int endClipIndex,
        List<Integer> clipIndices,
        List<String> segmentUrls,
        String outputUrl
    ) {
        String suffix = stableJoinSuffix(task.id, endClipIndex);
        String now = nowIso();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", "mdlcall_join_" + suffix);
        row.put("callKind", "render");
        row.put("stage", "render");
        row.put("operation", "media.concat");
        row.put("provider", "local");
        row.put("providerModel", "ffmpeg");
        row.put("requestedModel", "ffmpeg");
        row.put("resolvedModel", "ffmpeg");
        row.put("modelName", "ffmpeg");
        row.put("modelAlias", "ffmpeg");
        row.put("endpointHost", "localhost");
        row.put("requestId", "join:" + joinName);
        row.put("requestPayload", Map.of("joinName", joinName, "targetClipIndex", endClipIndex, "clipIndices", clipIndices, "segmentUrls", segmentUrls));
        row.put("responsePayload", Map.of("outputUrl", outputUrl, "segmentCount", segmentUrls.size(), "clipIndices", clipIndices));
        row.put("httpStatus", 200);
        row.put("responseCode", 200);
        row.put("success", true);
        row.put("errorCode", "");
        row.put("errorMessage", "");
        row.put("latencyMs", 0);
        row.put("inputTokens", 0);
        row.put("outputTokens", 0);
        row.put("startedAt", now);
        row.put("finishedAt", now);
        return row;
    }

    private Map<String, Object> createJoinMaterial(
        TaskRecord task,
        String joinName,
        List<Integer> clipIndices,
        LocalMediaArtifactService.StoredArtifact artifact,
        List<String> segmentUrls,
        double durationSeconds,
        int width,
        int height,
        boolean hasAudio
    ) {
        String suffix = stableJoinSuffix(task.id, joinClipEnd(joinName));
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "asset_join_" + suffix);
        row.put("kind", "join");
        row.put("mediaType", "video");
        row.put("title", task.title + " " + joinName);
        row.put("originProvider", "local");
        row.put("originModel", "ffmpeg");
        row.put("remoteTaskId", "");
        row.put("remoteAssetId", "");
        row.put("originalFileName", artifact.fileName());
        row.put("storedFileName", artifact.fileName());
        row.put("fileExt", fileExt(artifact.fileName()));
        row.put("storageProvider", "local");
        row.put("mimeType", "video/mp4");
        row.put("sizeBytes", artifact.sizeBytes());
        row.put("durationSeconds", durationSeconds);
        row.put("width", width);
        row.put("height", height);
        row.put("hasAudio", hasAudio);
        row.put("storagePath", artifact.absolutePath());
        row.put("localFilePath", artifact.absolutePath());
        row.put("fileUrl", artifact.publicUrl());
        row.put("previewUrl", artifact.publicUrl());
        row.put("remoteUrl", "");
        row.put("metadata", Map.of(
            "joinName", joinName,
            "taskId", task.id,
            "sourceTaskTitle", task.title,
            "engine", "ffmpeg",
            "clipIndices", clipIndices,
            "segmentUrls", segmentUrls,
            "taskArtifact", true
        ));
        row.put("createdAt", nowIso());
        return row;
    }

    private Map<String, Object> createJoinResult(
        TaskRecord task,
        String joinName,
        int joinClipIndex,
        Map<String, Object> modelCall,
        Map<String, Object> material,
        LocalMediaArtifactService.StoredArtifact artifact,
        List<Integer> clipIndices,
        List<String> segmentUrls,
        double durationSeconds,
        int width,
        int height,
        boolean hasAudio
    ) {
        String suffix = stableJoinSuffix(task.id, joinClipIndex - JOIN_OUTPUT_CLIP_INDEX_BASE);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "result_join_" + suffix);
        row.put("resultType", "video_join");
        row.put("clipIndex", joinClipIndex);
        row.put("title", joinName);
        row.put("reason", "Spring join worker 已按顺序拼接已有片段输出。");
        row.put("sourceModelCallId", stringValue(modelCall.get("modelCallId")));
        row.put("materialAssetId", material.get("id"));
        row.put("startSeconds", 0.0);
        row.put("endSeconds", durationSeconds);
        row.put("durationSeconds", durationSeconds);
        row.put("previewUrl", artifact.publicUrl());
        row.put("downloadUrl", artifact.publicUrl());
        row.put("mimeType", "video/mp4");
        row.put("width", width);
        row.put("height", height);
        row.put("sizeBytes", artifact.sizeBytes());
        row.put("remoteUrl", "");
        row.put("extra", Map.of(
            "joinName", joinName,
            "sourceTaskTitle", task.title,
            "clipIndices", clipIndices,
            "segmentCount", segmentUrls.size(),
            "segmentUrls", segmentUrls,
            "hasAudio", hasAudio,
            "taskArtifact", true
        ));
        row.put("createdAt", nowIso());
        return row;
    }

    private Map<String, Object> createJoinStageRun(
        TaskRecord task,
        String joinName,
        int joinClipIndex,
        List<Integer> clipIndices,
        List<String> segmentUrls,
        String outputUrl,
        Map<String, Object> material,
        Map<String, Object> result
    ) {
        String suffix = stableJoinSuffix(task.id, joinClipIndex - JOIN_OUTPUT_CLIP_INDEX_BASE);
        String now = nowIso();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("stageRunId", "stgrun_join_" + suffix);
        row.put("attemptId", task.activeAttemptId);
        row.put("stageName", "render_join");
        row.put("stageSeq", joinClipIndex);
        row.put("clipIndex", joinClipIndex);
        row.put("status", "COMPLETED");
        row.put("workerInstanceId", joinWorkerInstanceId);
        row.put("startedAt", now);
        row.put("finishedAt", now);
        row.put("durationMs", 0);
        row.put("inputSummary", Map.of("joinName", joinName, "clipIndices", clipIndices, "segmentUrls", segmentUrls));
        row.put("outputSummary", Map.of(
            "outputUrl", outputUrl,
            "materialAssetId", stringValue(material.get("id")),
            "resultId", stringValue(result.get("id"))
        ));
        row.put("errorCode", "");
        row.put("errorMessage", "");
        return row;
    }

    private String joinOutputName(int endClipIndex) {
        return TaskArtifactNaming.joinName(endClipIndex);
    }

    private int joinClipEnd(String joinName) {
        String[] parts = stringValue(joinName).split("-");
        if (parts.length < 2) {
            return 0;
        }
        return intValue(parts[parts.length - 1], 0);
    }

    private String stableJoinSuffix(String taskId, int endClipIndex) {
        String shortTaskId = taskId == null ? "" : taskId.substring(Math.max(0, taskId.length() - 12));
        return shortTaskId + "_" + Math.max(2, endClipIndex);
    }

    private List<Integer> uniqueClipIndices(List<Map<String, Object>> clipResults) {
        LinkedHashSet<Integer> indices = new LinkedHashSet<>();
        for (Map<String, Object> clipResult : clipResults) {
            int clipIndex = intValue(clipResult.get("clipIndex"), 0);
            if (clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        return new ArrayList<>(indices);
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

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
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

    private double doubleValue(Object value, double fallback) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value != null) {
            try {
                return Double.parseDouble(String.valueOf(value).trim());
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

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }
}
