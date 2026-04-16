package com.jiandou.api.task.domain;

import java.util.Locale;

/**
 * 任务尝试触发类型枚举。
 */
public enum AttemptTriggerType {
    CREATE,
    RETRY,
    CONTINUE;

    public String value() {
        return name().toLowerCase(Locale.ROOT);
    }

    public boolean matches(String rawValue) {
        return this == from(rawValue);
    }

    public static AttemptTriggerType from(String rawValue) {
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
        AttemptTriggerType triggerType = from(rawValue);
        return triggerType == null ? "" : triggerType.value();
    }
}
