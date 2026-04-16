package com.jiandou.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 任务查询和 worker 运行参数配置。
 */
@ConfigurationProperties(prefix = "jiandou.task.ops")
public class JiandouTaskOpsProperties {

    private int traceLimit = 500;
    private int logLimit = 500;
    private int statusHistoryLimit = 500;
    private int modelCallLimit = 500;
    private int adminTraceLimit = 200;
    private int adminWorkerLimit = 100;
    private int adminQueueLimit = 200;
    private int adminOverviewQueuePreviewLimit = 50;
    private int adminOverviewWorkerPreviewLimit = 20;
    private int workerInstanceScanLimit = 200;
    private int recentTraceScanLimit = 1000;
    private int generationRunListLimit = 100;
    private int workerStaleTimeoutSeconds = 30;
    private long workerPollInitialDelayMillis = 500L;
    private long workerPollIntervalMillis = 1000L;
    private long workerMaintenanceInitialDelayMillis = 500L;
    private long workerMaintenanceIntervalMillis = 2000L;

    public int getTraceLimit() {
        return traceLimit;
    }

    public void setTraceLimit(int traceLimit) {
        this.traceLimit = Math.max(1, traceLimit);
    }

    public int getLogLimit() {
        return logLimit;
    }

    public void setLogLimit(int logLimit) {
        this.logLimit = Math.max(1, logLimit);
    }

    public int getStatusHistoryLimit() {
        return statusHistoryLimit;
    }

    public void setStatusHistoryLimit(int statusHistoryLimit) {
        this.statusHistoryLimit = Math.max(1, statusHistoryLimit);
    }

    public int getModelCallLimit() {
        return modelCallLimit;
    }

    public void setModelCallLimit(int modelCallLimit) {
        this.modelCallLimit = Math.max(1, modelCallLimit);
    }

    public int getAdminTraceLimit() {
        return adminTraceLimit;
    }

    public void setAdminTraceLimit(int adminTraceLimit) {
        this.adminTraceLimit = Math.max(1, adminTraceLimit);
    }

    public int getAdminWorkerLimit() {
        return adminWorkerLimit;
    }

    public void setAdminWorkerLimit(int adminWorkerLimit) {
        this.adminWorkerLimit = Math.max(1, adminWorkerLimit);
    }

    public int getAdminQueueLimit() {
        return adminQueueLimit;
    }

    public void setAdminQueueLimit(int adminQueueLimit) {
        this.adminQueueLimit = Math.max(1, adminQueueLimit);
    }

    public int getAdminOverviewQueuePreviewLimit() {
        return adminOverviewQueuePreviewLimit;
    }

    public void setAdminOverviewQueuePreviewLimit(int adminOverviewQueuePreviewLimit) {
        this.adminOverviewQueuePreviewLimit = Math.max(1, adminOverviewQueuePreviewLimit);
    }

    public int getAdminOverviewWorkerPreviewLimit() {
        return adminOverviewWorkerPreviewLimit;
    }

    public void setAdminOverviewWorkerPreviewLimit(int adminOverviewWorkerPreviewLimit) {
        this.adminOverviewWorkerPreviewLimit = Math.max(1, adminOverviewWorkerPreviewLimit);
    }

    public int getWorkerInstanceScanLimit() {
        return workerInstanceScanLimit;
    }

    public void setWorkerInstanceScanLimit(int workerInstanceScanLimit) {
        this.workerInstanceScanLimit = Math.max(1, workerInstanceScanLimit);
    }

    public int getRecentTraceScanLimit() {
        return recentTraceScanLimit;
    }

    public void setRecentTraceScanLimit(int recentTraceScanLimit) {
        this.recentTraceScanLimit = Math.max(1, recentTraceScanLimit);
    }

    public int getGenerationRunListLimit() {
        return generationRunListLimit;
    }

    public void setGenerationRunListLimit(int generationRunListLimit) {
        this.generationRunListLimit = Math.max(1, generationRunListLimit);
    }

    public int getWorkerStaleTimeoutSeconds() {
        return workerStaleTimeoutSeconds;
    }

    public void setWorkerStaleTimeoutSeconds(int workerStaleTimeoutSeconds) {
        this.workerStaleTimeoutSeconds = Math.max(10, workerStaleTimeoutSeconds);
    }

    public long getWorkerPollInitialDelayMillis() {
        return workerPollInitialDelayMillis;
    }

    public void setWorkerPollInitialDelayMillis(long workerPollInitialDelayMillis) {
        this.workerPollInitialDelayMillis = Math.max(0L, workerPollInitialDelayMillis);
    }

    public long getWorkerPollIntervalMillis() {
        return workerPollIntervalMillis;
    }

    public void setWorkerPollIntervalMillis(long workerPollIntervalMillis) {
        this.workerPollIntervalMillis = Math.max(1L, workerPollIntervalMillis);
    }

    public long getWorkerMaintenanceInitialDelayMillis() {
        return workerMaintenanceInitialDelayMillis;
    }

    public void setWorkerMaintenanceInitialDelayMillis(long workerMaintenanceInitialDelayMillis) {
        this.workerMaintenanceInitialDelayMillis = Math.max(0L, workerMaintenanceInitialDelayMillis);
    }

    public long getWorkerMaintenanceIntervalMillis() {
        return workerMaintenanceIntervalMillis;
    }

    public void setWorkerMaintenanceIntervalMillis(long workerMaintenanceIntervalMillis) {
        this.workerMaintenanceIntervalMillis = Math.max(1L, workerMaintenanceIntervalMillis);
    }
}
