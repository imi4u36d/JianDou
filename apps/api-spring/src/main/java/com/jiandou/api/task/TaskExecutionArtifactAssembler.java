package com.jiandou.api.task;

import com.jiandou.api.media.LocalMediaArtifactService;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
final class TaskExecutionArtifactAssembler {

    private static final Logger log = LoggerFactory.getLogger(TaskExecutionArtifactAssembler.class);

    private final LocalMediaArtifactService localMediaArtifactService;

    TaskExecutionArtifactAssembler(LocalMediaArtifactService localMediaArtifactService) {
        this.localMediaArtifactService = localMediaArtifactService;
    }

    Map<String, Object> createTextMaterial(TaskRecord task, Map<String, Object> run, Map<String, Object> result) {
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

    Map<String, Object> createImageMaterial(TaskRecord task, Map<String, Object> run, Map<String, Object> result, int clipIndex, String frameRole) {
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

    Map<String, Object> createReferenceFrameMaterial(TaskRecord task, int clipIndex, String sourceUrl, String frameRole) {
        String normalizedFrameRole = normalizeFrameRole(frameRole);
        String targetFileName = TaskArtifactNaming.clipFrameFileName(
            clipIndex,
            normalizedFrameRole,
            fileExtOrDefault(fileNameFromUrl(sourceUrl), "png")
        );
        String fileUrl = stringValue(sourceUrl);
        try {
            LocalMediaArtifactService.StoredArtifact artifact = normalizeTaskArtifact(task, sourceUrl, targetFileName, "keyframe");
            fileUrl = artifact.publicUrl();
        } catch (Exception ex) {
            log.debug(
                "reuse frame artifact materialize failed: taskId={}, clipIndex={}, sourceUrl={}",
                task == null ? "" : task.id,
                clipIndex,
                sourceUrl,
                ex
            );
        }
        return createMaterial(
            task,
            Map.of(),
            "image",
            task.title + ("last".equals(normalizedFrameRole) ? " 尾帧关键画面" : " 首帧关键画面"),
            fileUrl,
            fileUrl,
            imageMimeType(targetFileName),
            0.0,
            0,
            0,
            false,
            clipIndex,
            "keyframe-" + normalizedFrameRole,
            Map.of(),
            Map.of(
                "taskArtifact", fileUrl.startsWith("/storage/"),
                "clipIndex", clipIndex,
                "frameRole", normalizedFrameRole,
                "remoteSourceUrl", stringValue(sourceUrl),
                "reusedFromPreviousClip", true
            ),
            stringValue(sourceUrl)
        );
    }

    Map<String, Object> createVideoMaterial(
        TaskRecord task,
        Map<String, Object> run,
        Map<String, Object> result,
        int clipIndex,
        int fallbackDurationSeconds
    ) {
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String outputUrl = firstNonBlank(
            stringValue(result.get("outputUrl")),
            stringValue(metadata.get("outputUrl")),
            stringValue(metadata.get("fileUrl")),
            stringValue(metadata.get("remoteSourceUrl"))
        );
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
            doubleValue(result.get("durationSeconds"), (double) fallbackDurationSeconds),
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

    Map<String, Object> createResult(
        TaskRecord task,
        Map<String, Object> videoRun,
        Map<String, Object> videoResult,
        Map<String, Object> videoMaterial,
        Map<String, Object> imageMaterial,
        Map<String, Object> videoModelCall,
        String resolvedLastFrameUrl,
        int clipIndex,
        int fallbackDurationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds
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
        row.put("endSeconds", doubleValue(videoResult.get("durationSeconds"), (double) fallbackDurationSeconds));
        row.put("durationSeconds", doubleValue(videoResult.get("durationSeconds"), (double) fallbackDurationSeconds));
        row.put("previewUrl", stringValue(videoMaterial.get("previewUrl")));
        row.put("downloadUrl", stringValue(videoMaterial.get("fileUrl")));
        row.put("mimeType", stringValue(videoResult.getOrDefault("mimeType", "video/mp4")));
        row.put("width", intValue(videoResult.get("width"), 0));
        row.put("height", intValue(videoResult.get("height"), 0));
        row.put("sizeBytes", fileSize(localMediaArtifactService.resolveAbsolutePath(stringValue(videoMaterial.get("fileUrl")))));
        row.put("remoteUrl", stringValue(videoMetadata.get("remoteSourceUrl")));
        Map<String, Object> extra = new LinkedHashMap<>();
        extra.put("runId", stringValue(videoRun.get("id")));
        extra.put("posterUrl", stringValue(imageMaterial.get("fileUrl")));
        extra.put("thumbnailUrl", stringValue(videoResult.get("thumbnailUrl")));
        extra.put("hasAudio", boolValue(videoResult.get("hasAudio")));
        extra.put("clipIndex", clipIndex);
        extra.put("targetDurationSeconds", fallbackDurationSeconds);
        extra.put("minDurationSeconds", minDurationSeconds);
        extra.put("maxDurationSeconds", maxDurationSeconds);
        extra.put("requestedDurationSeconds", fallbackDurationSeconds);
        extra.put("appliedDurationSeconds", doubleValue(videoResult.get("durationSeconds"), (double) fallbackDurationSeconds));
        extra.put("remoteTaskId", stringValue(videoMetadata.get("taskId")));
        extra.put("firstFrameUrl", firstNonBlank(stringValue(videoMetadata.get("firstFrameUrl")), stringValue(imageMaterial.get("remoteUrl"))));
        extra.put("lastFrameUrl", resolvedLastFrameUrl);
        extra.put("requestedLastFrameUrl", stringValue(videoMetadata.get("requestedLastFrameUrl")));
        row.put("extra", extra);
        row.put("createdAt", nowIso());
        return row;
    }

    void normalizeOptionalTaskArtifact(TaskRecord task, String sourceUrl, String targetFileName) {
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

    String extractLastFrameUrl(Object value) {
        String direct = findNestedString(value, "lastFrameUrl", "last_frame_url");
        if (!direct.isBlank()) {
            return direct;
        }
        return findNestedRoleUrl(value, "last_frame");
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

    private String fileExtOrDefault(String fileName, String fallback) {
        String resolved = fileExt(fileName);
        return resolved.isBlank() ? fallback : resolved;
    }

    private String imageMimeType(String fileName) {
        String ext = fileExt(fileName);
        return switch (ext) {
            case "jpg", "jpeg" -> "image/jpeg";
            case "webp" -> "image/webp";
            default -> "image/png";
        };
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

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
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
        String normalized = stringValue(url)
            .replaceAll("[?#].*$", "")
            .replaceAll("/+$", "");
        int index = normalized.lastIndexOf('/');
        return index >= 0 ? normalized.substring(index + 1) : normalized;
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

    private String normalizeFrameRole(String frameRole) {
        return "last".equalsIgnoreCase(stringValue(frameRole)) ? "last" : "first";
    }

    private String stableId(String prefix, String... parts) {
        String seed = prefix + ":" + String.join(":", parts);
        return prefix + "_" + UUID.nameUUIDFromBytes(seed.getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
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
}
