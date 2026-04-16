package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * Worker 状态枚举。
 */
public enum WorkerStatus {
    RUNNING,
    STOPPED,
    FAILED,
    STALE;

    public String value() {
        return name();
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static WorkerStatus from(String rawValue) {
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
