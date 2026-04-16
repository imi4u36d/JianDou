package com.jiandou.api.task.runtime;

import com.jiandou.api.task.domain.ExecutionMode;

/**
 * 任务工作节点执行记录结构。
 * @param workerInstanceId 工作节点实例标识
 * @param workerType 工作节点类型值
 * @param executionMode 执行模式值
 */
record TaskWorkerExecutionContext(
    String workerInstanceId,
    String workerType,
    String executionMode
) {
    TaskWorkerExecutionContext {
        workerInstanceId = workerInstanceId == null ? "" : workerInstanceId;
        workerType = workerType == null ? "" : workerType;
        executionMode = ExecutionMode.normalize(executionMode);
    }

    TaskWorkerExecutionContext(String workerInstanceId, String workerType, ExecutionMode executionMode) {
        this(workerInstanceId, workerType, executionMode == null ? null : executionMode.value());
    }

    ExecutionMode executionModeEnum() {
        return ExecutionMode.from(executionMode);
    }
}
