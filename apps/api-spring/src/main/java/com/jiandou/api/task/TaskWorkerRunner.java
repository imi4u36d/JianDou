package com.jiandou.api.task;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.SmartLifecycle;
import org.springframework.context.annotation.DependsOn;
import org.springframework.stereotype.Component;

@Component
@DependsOn("databaseSchemaReady")
public class TaskWorkerRunner implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(TaskWorkerRunner.class);

    private final TaskQueuePort taskQueuePort;
    private final TaskExecutionCoordinator executionCoordinator;
    private final TaskWorkerPipelineHandler pipelineHandler;
    private final String executionMode;
    private final int staleWorkerTimeoutSeconds;
    private final String workerInstanceId = "spring_worker_" + UUID.randomUUID().toString().replace("-", "");
    private final String workerType = "spring_queue_worker";
    private ScheduledExecutorService pollExecutor;
    private ScheduledExecutorService maintenanceExecutor;
    private volatile boolean running;

    public TaskWorkerRunner(
        TaskQueuePort taskQueuePort,
        TaskExecutionCoordinator executionCoordinator,
        TaskWorkerPipelineHandler pipelineHandler,
        @Value("${JIANDOU_EXECUTION_MODE:queue}") String executionMode,
        @Value("${JIANDOU_WORKER_STALE_TIMEOUT_SECONDS:30}") int staleWorkerTimeoutSeconds
    ) {
        this.taskQueuePort = taskQueuePort;
        this.executionCoordinator = executionCoordinator;
        this.pipelineHandler = pipelineHandler;
        this.executionMode = executionMode == null ? "queue" : executionMode.trim().toLowerCase();
        this.staleWorkerTimeoutSeconds = Math.max(10, staleWorkerTimeoutSeconds);
    }

    @Override
    public void start() {
        if (running || !"queue".equals(executionMode)) {
            return;
        }
        running = true;
        executionCoordinator.upsertWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("executionMode", executionMode));
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
        pollExecutor.scheduleWithFixedDelay(this::pollOnce, 500, 1000, TimeUnit.MILLISECONDS);
        maintenanceExecutor.scheduleWithFixedDelay(this::maintenanceTick, 500, 2000, TimeUnit.MILLISECONDS);
    }

    @Override
    public void stop() {
        running = false;
        executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "STOPPED", Map.of("executionMode", executionMode));
        if (pollExecutor != null) {
            pollExecutor.shutdownNow();
            pollExecutor = null;
        }
        if (maintenanceExecutor != null) {
            maintenanceExecutor.shutdownNow();
            maintenanceExecutor = null;
        }
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public boolean isAutoStartup() {
        return true;
    }

    @Override
    public int getPhase() {
        return Integer.MAX_VALUE;
    }

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

    private void maintenanceTick() {
        try {
            executionCoordinator.touchWorkerInstance(workerInstanceId, workerType, "RUNNING", Map.of("executionMode", executionMode));
            executionCoordinator.recoverStaleClaims(java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC).minusSeconds(staleWorkerTimeoutSeconds), 20);
        } catch (Exception ex) {
            log.warn("worker maintenance failed: workerInstanceId={}", workerInstanceId, ex);
        }
    }
}
