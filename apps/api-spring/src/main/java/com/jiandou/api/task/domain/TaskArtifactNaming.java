package com.jiandou.api.task.domain;

import com.jiandou.api.task.TaskRecord;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

/**
 * 任务产物Naming。
 */
public final class TaskArtifactNaming {

    /**
     * 创建新的任务产物Naming。
     */
    private TaskArtifactNaming() {
    }

    /**
     * 处理任务产物RelativeDir。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public static String taskArtifactRelativeDir(TaskRecord task) {
        return taskBaseRelativeDir(task);
    }

    /**
     * 处理任务BaseRelativeDir。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public static String taskBaseRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task);
    }

    /**
     * 处理任务RunningRelativeDir。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public static String taskRunningRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task) + "/running";
    }

    /**
     * 处理任务JoinedRelativeDir。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public static String taskJoinedRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task) + "/joined";
    }

    /**
     * 处理任务产物BaseRelativeDir。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private static String taskArtifactBaseRelativeDir(TaskRecord task) {
        LocalDate date = resolveTaskDate(task);
        return "gen/"
            + date.getYear() + "-" + twoDigit(date.getMonthValue()) + "-" + twoDigit(date.getDayOfMonth())
            + "/"
            + safeTaskDirectory(task == null ? null : task.id());
    }

    /**
     * 处理分镜文件Name。
     * @param task 要处理的任务对象
     * @param extension extension值
     * @return 处理结果
     */
    public static String storyboardFileName(TaskRecord task, String extension) {
        return "storyboard." + normalizeExtension(extension);
    }

    /**
     * 处理keyframe文件Name。
     * @param task 要处理的任务对象
     * @param clipIndex 片段索引值
     * @param extension extension值
     * @return 处理结果
     */
    public static String keyframeFileName(TaskRecord task, int clipIndex, String extension) {
        return clipFrameFileName(clipIndex, "first", extension);
    }

    /**
     * 处理lastFrame文件Name。
     * @param clipIndex 片段索引值
     * @param extension extension值
     * @return 处理结果
     */
    public static String lastFrameFileName(int clipIndex, String extension) {
        return clipFrameFileName(clipIndex, "last", extension);
    }

    /**
     * 处理片段Frame文件Name。
     * @param clipIndex 片段索引值
     * @param frameRole frameRole值
     * @param extension extension值
     * @return 处理结果
     */
    public static String clipFrameFileName(int clipIndex, String frameRole, String extension) {
        String resolvedRole = normalizeFrameRole(frameRole);
        String resolvedExtension = normalizeExtension(extension);
        return "clip" + normalizedClipIndex(clipIndex) + "-" + resolvedRole + "." + resolvedExtension;
    }

    /**
     * 处理片段文件Name。
     * @param task 要处理的任务对象
     * @param clipIndex 片段索引值
     * @param extension extension值
     * @return 处理结果
     */
    public static String clipFileName(TaskRecord task, int clipIndex, String extension) {
        return clipFileName(clipIndex, extension);
    }

    /**
     * 处理片段文件Name。
     * @param clipIndex 片段索引值
     * @param extension extension值
     * @return 处理结果
     */
    public static String clipFileName(int clipIndex, String extension) {
        String resolvedExtension = normalizeExtension(extension);
        return "clip" + normalizedClipIndex(clipIndex) + "." + resolvedExtension;
    }

    /**
     * 拼接文件Name。
     * @param task 要处理的任务对象
     * @param endClipIndex end片段索引值
     * @param extension extension值
     * @return 处理结果
     */
    public static String joinFileName(TaskRecord task, int endClipIndex, String extension) {
        return joinName(endClipIndex) + "." + normalizeExtension(extension);
    }

    /**
     * 拼接Name。
     * @param endClipIndex end片段索引值
     * @return 处理结果
     */
    public static String joinName(int endClipIndex) {
        List<String> parts = new ArrayList<>();
        parts.add("join");
        for (int index = 1; index <= Math.max(2, endClipIndex); index++) {
            parts.add(String.valueOf(index));
        }
        return String.join("-", parts);
    }

    /**
     * 处理解析任务日期。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private static LocalDate resolveTaskDate(TaskRecord task) {
        String createdAt = task == null ? "" : stringValue(task.createdAt());
        if (!createdAt.isBlank()) {
            try {
                return OffsetDateTime.parse(createdAt).toLocalDate();
            } catch (Exception ignored) {
            }
        }
        return OffsetDateTime.now(ZoneOffset.UTC).toLocalDate();
    }

    /**
     * 处理safe任务Directory。
     * @param taskId 任务标识
     * @return 处理结果
     */
    private static String safeTaskDirectory(String taskId) {
        String normalized = stringValue(taskId).replace('\\', '_').replace('/', '_').trim();
        return normalized.isBlank() ? "task-unknown" : normalized;
    }

    /**
     * 规范化Segment。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private static String normalizeSegment(String value, String fallback) {
        String normalized = stringValue(value)
            .replaceAll("[\\s\\p{Punct}]+", "_")
            .replaceAll("[^\\p{IsAlphabetic}\\p{IsDigit}_-]+", "_")
            .replaceAll("_+", "_")
            .replaceAll("-+", "-")
            .replaceAll("^[_-]+", "")
            .replaceAll("[_-]+$", "");
        return normalized.isBlank() ? fallback : normalized;
    }

    /**
     * 规范化Extension。
     * @param extension extension值
     * @return 处理结果
     */
    private static String normalizeExtension(String extension) {
        String normalized = stringValue(extension).replace(".", "").trim().toLowerCase();
        return normalized.isBlank() ? "bin" : normalized;
    }

    /**
     * 规范化FrameRole。
     * @param frameRole frameRole值
     * @return 处理结果
     */
    private static String normalizeFrameRole(String frameRole) {
        String normalized = normalizeSegment(frameRole, "first").toLowerCase();
        return "last".equals(normalized) ? "last" : "first";
    }

    /**
     * 处理normalized片段索引。
     * @param clipIndex 片段索引值
     * @return 处理结果
     */
    private static int normalizedClipIndex(int clipIndex) {
        return Math.max(1, clipIndex);
    }

    /**
     * 处理twoDigit。
     * @param value 待处理的值
     * @return 处理结果
     */
    private static String twoDigit(int value) {
        return value < 10 ? "0" + value : String.valueOf(value);
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
