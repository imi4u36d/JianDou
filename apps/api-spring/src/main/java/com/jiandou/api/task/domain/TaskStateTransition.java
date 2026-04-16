package com.jiandou.api.task.domain;

import java.util.Map;

/**
 * Encapsulates one 任务状态 transition so coordinator can persist 任务 rows atomically.
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
        level = level == null || level.isBlank() ? TraceLevel.INFO.value() : level.trim().toUpperCase();
        payload = payload == null ? Map.of() : payload;
        attemptStatus = attemptStatus == null ? "" : attemptStatus.trim();
        attemptErrorMessage = attemptErrorMessage == null ? "" : attemptErrorMessage.trim();
    }

    /**
     * 处理信息。
     * @param nextStatus next状态值
     * @param progress 进度值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     * @param payload 附加负载数据
     * @return 处理结果
     */
    public static TaskStateTransition info(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, TraceLevel.INFO.value(), payload, "", "");
    }

    public static TaskStateTransition info(
        TaskStatus nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return info(nextStatus == null ? "" : nextStatus.value(), progress, stage, event, message, payload);
    }

    /**
     * 处理warn。
     * @param nextStatus next状态值
     * @param progress 进度值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     * @param payload 附加负载数据
     * @return 处理结果
     */
    public static TaskStateTransition warn(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, TraceLevel.WARN.value(), payload, "", "");
    }

    public static TaskStateTransition warn(
        TaskStatus nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return warn(nextStatus == null ? "" : nextStatus.value(), progress, stage, event, message, payload);
    }

    /**
     * 处理error。
     * @param nextStatus next状态值
     * @param progress 进度值
     * @param stage 阶段名称
     * @param event 事件名称
     * @param message 消息文本
     * @param payload 附加负载数据
     * @return 处理结果
     */
    public static TaskStateTransition error(
        String nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return new TaskStateTransition(nextStatus, progress, stage, event, message, TraceLevel.ERROR.value(), payload, "", "");
    }

    public static TaskStateTransition error(
        TaskStatus nextStatus,
        int progress,
        String stage,
        String event,
        String message,
        Map<String, Object> payload
    ) {
        return error(nextStatus == null ? "" : nextStatus.value(), progress, stage, event, message, payload);
    }

    /**
     * 处理with尝试。
     * @param status 状态值
     * @param errorMessage errorMessage值
     * @return 处理结果
     */
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

    public TaskStateTransition withAttempt(AttemptStatus status, String errorMessage) {
        return withAttempt(status == null ? "" : status.value(), errorMessage);
    }

    /**
     * 检查是否updates尝试。
     * @return 是否满足条件
     */
    public boolean updatesAttempt() {
        return !attemptStatus.isBlank();
    }

    public TaskStatus nextStatusEnum() {
        return TaskStatus.from(nextStatus);
    }

    public TraceLevel levelEnum() {
        String normalized = level == null ? "" : level.trim().toUpperCase();
        for (TraceLevel item : TraceLevel.values()) {
            if (item.value().equals(normalized)) {
                return item;
            }
        }
        return TraceLevel.INFO;
    }

    public AttemptStatus attemptStatusEnum() {
        return AttemptStatus.from(attemptStatus);
    }
}
