package com.jiandou.api.task.exception;

/**
 * 任务执行Aborted异常。
 */
public final class TaskExecutionAbortedException extends RuntimeException {

    private final String taskStatus;

    public TaskExecutionAbortedException(String taskStatus, String message) {
        super(message);
        this.taskStatus = taskStatus == null ? "" : taskStatus;
    }

    /**
     * 处理任务状态。
     * @return 处理结果
     */
    public String taskStatus() {
        return taskStatus;
    }
}
