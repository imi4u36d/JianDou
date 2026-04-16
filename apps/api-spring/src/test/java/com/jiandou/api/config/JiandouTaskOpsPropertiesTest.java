package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class JiandouTaskOpsPropertiesTest {

    @Test
    void settersClampConfiguredLimitsAndIntervals() {
        JiandouTaskOpsProperties properties = new JiandouTaskOpsProperties();
        properties.setTraceLimit(0);
        properties.setLogLimit(0);
        properties.setStatusHistoryLimit(0);
        properties.setModelCallLimit(0);
        properties.setAdminTraceLimit(0);
        properties.setAdminWorkerLimit(0);
        properties.setAdminQueueLimit(0);
        properties.setAdminOverviewQueuePreviewLimit(0);
        properties.setAdminOverviewWorkerPreviewLimit(0);
        properties.setWorkerInstanceScanLimit(0);
        properties.setRecentTraceScanLimit(0);
        properties.setGenerationRunListLimit(0);
        properties.setWorkerStaleTimeoutSeconds(1);
        properties.setWorkerPollInitialDelayMillis(-1L);
        properties.setWorkerPollIntervalMillis(0L);
        properties.setWorkerMaintenanceInitialDelayMillis(-1L);
        properties.setWorkerMaintenanceIntervalMillis(0L);

        assertEquals(1, properties.getTraceLimit());
        assertEquals(1, properties.getLogLimit());
        assertEquals(1, properties.getStatusHistoryLimit());
        assertEquals(1, properties.getModelCallLimit());
        assertEquals(1, properties.getAdminTraceLimit());
        assertEquals(1, properties.getAdminWorkerLimit());
        assertEquals(1, properties.getAdminQueueLimit());
        assertEquals(1, properties.getAdminOverviewQueuePreviewLimit());
        assertEquals(1, properties.getAdminOverviewWorkerPreviewLimit());
        assertEquals(1, properties.getWorkerInstanceScanLimit());
        assertEquals(1, properties.getRecentTraceScanLimit());
        assertEquals(1, properties.getGenerationRunListLimit());
        assertEquals(10, properties.getWorkerStaleTimeoutSeconds());
        assertEquals(0L, properties.getWorkerPollInitialDelayMillis());
        assertEquals(1L, properties.getWorkerPollIntervalMillis());
        assertEquals(0L, properties.getWorkerMaintenanceInitialDelayMillis());
        assertEquals(1L, properties.getWorkerMaintenanceIntervalMillis());
    }
}
