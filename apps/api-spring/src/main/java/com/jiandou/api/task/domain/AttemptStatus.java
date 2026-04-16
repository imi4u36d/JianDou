package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * 任务尝试状态枚举。
 */
public enum AttemptStatus {
    PENDING,
    PAUSED,
    QUEUED,
    RUNNING,
    COMPLETED,
    FAILED,
    REMOVED,
    TERMINATED;

    public String value() {
        return name();
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static AttemptStatus from(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return valueOf(rawValue.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }
}
