package com.jiandou.api.task.runtime;

import com.jiandou.api.config.JiandouAppProperties;
import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.application.TaskExecutionCoordinator;
import com.jiandou.api.task.domain.ExecutionMode;
import com.jiandou.api.task.domain.WorkerStatus;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.SmartLifecycle;
import org.springframework.context.annotation.DependsOn;
import org.springframework.stereotype.Component;

/**
 * 任务工作节点运行器。
 */
@Component
@DependsOn("databaseSchemaReady")
public class TaskWorkerRunner implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(TaskWorkerRunner.class);

    private final TaskQueuePort taskQueuePort;
    private final TaskExecutionCoordinator executionCoordinator;
    private final TaskWorkerPipelineHandler pipelineHandler;
    private final JiandouTaskOpsProperties taskOpsProperties;
    private final String executionMode;
    private final int staleWorkerTimeoutSeconds;
    private final String workerInstanceId = "spring_worker_" + UUID.randomUUID().toString().replace("-", "");
    private final String workerType = "spring_queue_worker";
    private ScheduledExecutorService pollExecutor;
    private ScheduledExecutorService maintenanceExecutor;
    private volatile boolean running;

    /**
     * 创建新的任务工作节点Runner。
     */
    public TaskWorkerRunner(
        TaskQueuePort taskQueuePort,
        TaskExecutionCoordinator executionCoordinator,
        TaskWorkerPipelineHandler pipelineHandler,
        JiandouAppProperties appProperties,
        JiandouTaskOpsProperties taskOpsProperties
    ) {
        this.taskQueuePort = taskQueuePort;
        this.executionCoordinator = executionCoordinator;
        this.pipelineHandler = pipelineHandler;
        this.taskOpsProperties = taskOpsProperties;
        this.executionMode = ExecutionMode.normalize(appProperties.getExecutionMode());
        this.staleWorkerTimeoutSeconds = taskOpsProperties.getWorkerStaleTimeoutSeconds();
    }

    /**
     * 启动进度流程。
     */
    @Override
    public void start() {
        if (running || !ExecutionMode.QUEUE.matches(executionMode)) {
            return;
        }
        running = true;
        executionCoordinator.upsertWorkerInstance(workerInstanceId, workerType, WorkerStatus.RUNNING.value(), Map.of("executionMode", executionMode));
        pollExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "jiandou-spring-worker");
            thread.setDaemon(true);
            return thread;
        });
        maintenanceExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "jiandou-spring-worker-maintenance");
            thread.setDaemon(true);
            return thread;
        });
        pollExecutor.scheduleWithFixedDelay(
            this::pollOnce,
            taskOpsProperties.getWorkerPollInitialDelayMillis(),
            taskOpsProperties.getWorkerPollIntervalMillis(),
            TimeUnit.MILLISECONDS
        );
        maintenanceExecutor.scheduleWithFixedDelay(
            this::maintenanceTick,
            taskOpsProperties.getWorkerMaintenanceInitialDelayMillis(),
            taskOpsProperties.getWorkerMaintenanceIntervalMillis(),
            TimeUnit.MILLISECONDS
        );
    }

    /**
     * 停止stop。
     */
    @Override
    public void stop() {
        running = false;
        executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, WorkerStatus.STOPPED.value(), Map.of("executionMode", executionMode));
        if (pollExecutor != null) {
            pollExecutor.shutdownNow();
            pollExecutor = null;
        }
        if (maintenanceExecutor != null) {
            maintenanceExecutor.shutdownNow();
            maintenanceExecutor = null;
        }
    }

    /**
     * 检查是否Running。
     * @return 是否满足条件
     */
    @Override
    public boolean isRunning() {
        return running;
    }

    /**
     * 检查是否AutoStartup。
     * @return 是否满足条件
     */
    @Override
    public boolean isAutoStartup() {
        return true;
    }

    /**
     * 返回Phase。
     * @return 处理结果
     */
    @Override
    public int getPhase() {
        return Integer.MAX_VALUE;
    }

    /**
     * 处理pollOnce。
     */
    private void pollOnce() {
        try {
            String claimedTaskId = taskQueuePort.claimNext(workerInstanceId);
            if (claimedTaskId == null || claimedTaskId.isBlank()) {
                return;
            }
            pipelineHandler.processTask(claimedTaskId, workerInstanceId, workerType, executionMode);
        } catch (Exception ex) {
            log.warn("worker poll failed: workerInstanceId={}", workerInstanceId, ex);
        }
    }

    /**
     * 处理maintenanceTick。
     */
    private void maintenanceTick() {
        try {
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, WorkerStatus.RUNNING.value(), Map.of("executionMode", executionMode));
            executionCoordinator.recoverStaleClaims(java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC).minusSeconds(staleWorkerTimeoutSeconds), 20);
        } catch (Exception ex) {
            log.warn("worker maintenance failed: workerInstanceId={}", workerInstanceId, ex);
        }
    }
}
