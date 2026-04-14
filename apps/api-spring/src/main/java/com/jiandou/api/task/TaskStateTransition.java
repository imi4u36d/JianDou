package com.jiandou.api.task;

import java.util.Map;

/**
 * Encapsulates one task status transition so coordinator can persist task rows atomically.
 */
public record TaskStateTransition(
    String nextStatus,
    int progress,
    String stage,
    String event,
    String message,
    String level,
    Map<String, Object> payload,
    String attemptStatus,
    String attemptErrorMessage
) {

    public TaskStateTransition {
        nextStatus = nextStatus == null ? "" : nextStatus.trim();
        stage = stage == null ? "" : stage.trim();
        event = event == null ? "" : event.trim();
        message = message == null ? "" : message.trim();
        level = level == null || level.isBlank() ? "INFO" : level.trim().toUpperCase();
        payload = payload == null ? Map.of() : payload;
        attemptStatus = attemptStatus == null ? "" : attemptStatus.trim();
        attemptErrorMessage = attemptErrorMessage == null ? "" : attemptErrorMessage.trim();
    }

    public static TaskStateTransition info(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, "INFO", payload, "", "");
    }

    public static TaskStateTransition warn(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, "WARN", payload, "", "");
    }

    public static TaskStateTransition error(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, "ERROR", payload, "", "");
    }

    public TaskStateTransition withAttempt(String status, String errorMessage) {
        return new TaskStateTransition(
            nextStatus,
            progress,
            stage,
            event,
            message,
            level,
            payload,
            status,
            errorMessage
        );
    }

    public boolean updatesAttempt() {
        return !attemptStatus.isBlank();
    }
}
