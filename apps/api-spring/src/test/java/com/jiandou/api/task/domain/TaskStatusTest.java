package com.jiandou.api.task.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TaskStatusTest {

    @Test
    void normalizeAndAliasChecksHandleCommonInputs() {
        assertEquals(TaskStatus.PENDING, TaskStatus.from(" pending "));
        assertNull(TaskStatus.from("missing"));
        assertEquals("RENDERING", TaskStatus.normalize("rendering"));
        assertEquals("", TaskStatus.normalize("missing"));
        assertTrue(TaskStatus.RENDERING.matches("rendering"));
        assertTrue(TaskStatus.isRunningAlias("running"));
        assertTrue(TaskStatus.isQueuedAlias("queued"));
        assertTrue(TaskStatus.isExecutionActive("planning"));
        assertTrue(TaskStatus.isRunningLike("joining"));
        assertTrue(TaskStatus.isTerminal("failed"));
        assertFalse(TaskStatus.isTerminal("planning"));
    }

    @Test
    void matchesFilterRespectsRunningAndQueuedAliases() {
        assertTrue(TaskStatus.matchesFilter("ANALYZING", false, "running"));
        assertTrue(TaskStatus.matchesFilter("PENDING", true, "queued"));
        assertTrue(TaskStatus.matchesFilter("COMPLETED", false, "completed"));
        assertFalse(TaskStatus.matchesFilter("COMPLETED", false, "queued"));
        assertFalse(TaskStatus.matchesFilter("FAILED", false, "running"));
        assertTrue(TaskStatus.matchesFilter("FAILED", false, ""));
    }
}
