package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * 任务状态枚举。
 */
public enum TaskStatus {
    PENDING,
    PAUSED,
    ANALYZING,
    PLANNING,
    RENDERING,
    COMPLETED,
    FAILED

    ;

    public String value() {
        return name();
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static TaskStatus from(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return valueOf(rawValue.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    public static String normalize(String rawValue) {
        TaskStatus status = from(rawValue);
        return status == null ? "" : status.name();
    }

    public static boolean isRunningAlias(String rawValue) {
        return "RUNNING".equals(normalizeAlias(rawValue));
    }

    public static boolean isQueuedAlias(String rawValue) {
        return "QUEUED".equals(normalizeAlias(rawValue));
    }

    public static boolean matchesFilter(String taskStatus, boolean queued, String filterValue) {
        String normalizedFilter = normalizeAlias(filterValue);
        if (normalizedFilter.isBlank()) {
            return true;
        }
        if (isRunningAlias(normalizedFilter)) {
            return isRunningLike(taskStatus);
        }
        if (isQueuedAlias(normalizedFilter)) {
            return queued;
        }
        String normalizedTaskStatus = normalize(taskStatus);
        return !normalizedTaskStatus.isBlank() && normalizedTaskStatus.equals(normalizedFilter);
    }

    public static boolean isExecutionActive(String rawValue) {
        TaskStatus status = from(rawValue);
        return status == PENDING || status == ANALYZING || status == PLANNING || status == RENDERING;
    }

    public static boolean isRunningLike(String rawValue) {
        String normalized = normalizeAlias(rawValue);
        return switch (normalized) {
            case "ANALYZING", "PLANNING", "RENDERING", "RUNNING", "DISPATCHING", "PROCESSING", "JOINING" -> true;
            default -> false;
        };
    }

    public static boolean isTerminal(String rawValue) {
        TaskStatus status = from(rawValue);
        return status == COMPLETED || status == FAILED;
    }

    private static String normalizeAlias(String rawValue) {
        String normalized = normalize(rawValue);
        if (!normalized.isBlank()) {
            return normalized;
        }
        return rawValue == null ? "" : rawValue.trim().toUpperCase(Locale.ROOT);
    }
}
