package com.jiandou.api.task.infrastructure.mybatis;

import java.time.OffsetDateTime;

final class TaskMybatisValueSupport {

    private TaskMybatisValueSupport() {
    }

    static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    static int intValue(Object value, int fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Integer.parseInt(text);
    }

    static int defaultInt(Integer value) {
        return value == null ? 0 : value;
    }

    static String format(OffsetDateTime value) {
        return value == null ? null : value.toString();
    }

    static long defaultLong(Long value) {
        return value == null ? 0L : value;
    }

    static double defaultDouble(Double value) {
        return value == null ? 0.0 : value;
    }

    static OffsetDateTime offsetValue(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return null;
        }
        return OffsetDateTime.parse(text);
    }

    static boolean boolValue(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        String text = String.valueOf(value).trim();
        return "true".equalsIgnoreCase(text) || "1".equals(text) || "yes".equalsIgnoreCase(text);
    }

    static long longValue(Object value, long fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.longValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Long.parseLong(text);
    }

    static double doubleValue(Object value, double fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return fallback;
        }
        return Double.parseDouble(text);
    }
}
