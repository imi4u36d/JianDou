package com.jiandou.api.task.infrastructure.mybatis;

public record QueueCandidateRow(
    String taskAttemptId,
    String taskId
) {
}
