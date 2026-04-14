package com.jiandou.api.task;

final class TaskExecutionAbortedException extends RuntimeException {

    private final String taskStatus;

    TaskExecutionAbortedException(String taskStatus, String message) {
        super(message);
        this.taskStatus = taskStatus == null ? "" : taskStatus;
    }

    String taskStatus() {
        return taskStatus;
    }
}
