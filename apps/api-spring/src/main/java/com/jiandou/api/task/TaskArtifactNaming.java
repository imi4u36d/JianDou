package com.jiandou.api.task;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

final class TaskArtifactNaming {

    private TaskArtifactNaming() {
    }

    static String taskArtifactRelativeDir(TaskRecord task) {
        return taskBaseRelativeDir(task);
    }

    static String taskBaseRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task);
    }

    static String taskRunningRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task) + "/running";
    }

    static String taskJoinedRelativeDir(TaskRecord task) {
        return taskArtifactBaseRelativeDir(task) + "/joined";
    }

    private static String taskArtifactBaseRelativeDir(TaskRecord task) {
        LocalDate date = resolveTaskDate(task);
        return "gen/"
            + date.getYear()
            + "/"
            + twoDigit(date.getMonthValue())
            + "/"
            + twoDigit(date.getDayOfMonth())
            + "/"
            + safeTaskDirectory(task == null ? null : task.id);
    }

    static String storyboardFileName(TaskRecord task, String extension) {
        return "storyboard." + normalizeExtension(extension);
    }

    static String keyframeFileName(TaskRecord task, int clipIndex, String extension) {
        return clipFrameFileName(clipIndex, "first", extension);
    }

    static String lastFrameFileName(int clipIndex, String extension) {
        return clipFrameFileName(clipIndex, "last", extension);
    }

    static String clipFrameFileName(int clipIndex, String frameRole, String extension) {
        String resolvedRole = normalizeFrameRole(frameRole);
        String resolvedExtension = normalizeExtension(extension);
        return "clip" + normalizedClipIndex(clipIndex) + "-" + resolvedRole + "." + resolvedExtension;
    }

    static String clipFileName(TaskRecord task, int clipIndex, String extension) {
        return clipFileName(clipIndex, extension);
    }

    static String clipFileName(int clipIndex, String extension) {
        String resolvedExtension = normalizeExtension(extension);
        return "clip" + normalizedClipIndex(clipIndex) + "." + resolvedExtension;
    }

    static String joinFileName(TaskRecord task, int endClipIndex, String extension) {
        return joinName(endClipIndex) + "." + normalizeExtension(extension);
    }

    static String joinName(int endClipIndex) {
        List<String> parts = new ArrayList<>();
        parts.add("join");
        for (int index = 1; index <= Math.max(2, endClipIndex); index++) {
            parts.add(String.valueOf(index));
        }
        return String.join("-", parts);
    }

    private static LocalDate resolveTaskDate(TaskRecord task) {
        String createdAt = task == null ? "" : stringValue(task.createdAt);
        if (!createdAt.isBlank()) {
            try {
                return OffsetDateTime.parse(createdAt).toLocalDate();
            } catch (Exception ignored) {
            }
        }
        return OffsetDateTime.now(ZoneOffset.UTC).toLocalDate();
    }

    private static String safeTaskDirectory(String taskId) {
        String normalized = stringValue(taskId).replace('\\', '_').replace('/', '_').trim();
        return normalized.isBlank() ? "task-unknown" : normalized;
    }

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

    private static String normalizeExtension(String extension) {
        String normalized = stringValue(extension).replace(".", "").trim().toLowerCase();
        return normalized.isBlank() ? "bin" : normalized;
    }

    private static String normalizeFrameRole(String frameRole) {
        String normalized = normalizeSegment(frameRole, "first").toLowerCase();
        return "last".equals(normalized) ? "last" : "first";
    }

    private static int normalizedClipIndex(int clipIndex) {
        return Math.max(1, clipIndex);
    }

    private static String twoDigit(int value) {
        return value < 10 ? "0" + value : String.valueOf(value);
    }

    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
