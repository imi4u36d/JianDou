package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * 任务执行模式枚举。
 */
public enum ExecutionMode {
    QUEUE,
    WORKER,
    SYNC;

    public String value() {
        return name().toLowerCase(Locale.ROOT);
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static ExecutionMode from(String rawValue) {
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
        ExecutionMode mode = from(rawValue);
        if (mode != null) {
            return mode.value();
        }
        return rawValue == null ? QUEUE.value() : rawValue.trim().toLowerCase(Locale.ROOT);
    }
}
