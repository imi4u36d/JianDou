package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * 任务队列事件类型枚举。
 */
public enum QueueEventType {
    ENQUEUED,
    REMOVED,
    CLAIMED,
    QUEUED,
    RUNNING,
    COMPLETED,
    FAILED,
    PAUSED,
    TERMINATED,
    RETRY_ENQUEUED,
    FINISHED;

    public String value() {
        return name().toLowerCase(Locale.ROOT);
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static QueueEventType from(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return valueOf(rawValue.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    public static QueueEventType fromAttemptStatus(AttemptStatus status) {
        if (status == null) {
            return FINISHED;
        }
        return switch (status) {
            case QUEUED -> QUEUED;
            case RUNNING -> RUNNING;
            case COMPLETED -> COMPLETED;
            case FAILED -> FAILED;
            case PAUSED -> PAUSED;
            case TERMINATED -> TERMINATED;
            case REMOVED -> REMOVED;
            case PENDING -> FINISHED;
        };
    }
}
