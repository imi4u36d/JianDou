package com.jiandou.api.task.infrastructure.mybatis;

public record StaleRunningTaskRow(
    String taskId,
    String workerInstanceId
) {
}
