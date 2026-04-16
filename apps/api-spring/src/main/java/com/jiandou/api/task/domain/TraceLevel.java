package com.jiandou.api.task.domain;

/**
 * Trace 级别枚举。
 */
public enum TraceLevel {
    INFO,
    WARN,
    ERROR;

    public String value() {
        return name();
    }
}
