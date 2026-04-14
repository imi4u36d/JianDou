package com.jiandou.api.task;

record TaskWorkerExecutionContext(
    String workerInstanceId,
    String workerType,
    String executionMode
) {
}
