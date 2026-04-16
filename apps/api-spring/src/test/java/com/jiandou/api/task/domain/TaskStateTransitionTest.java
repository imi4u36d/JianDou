package com.jiandou.api.task.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskStateTransitionTest {

    @Test
    void factoriesNormalizeFieldsAndWithAttemptAddsAttemptUpdate() {
        Map<String, Object> payload = new LinkedHashMap<>(Map.of("taskId", "task_1"));

        TaskStateTransition info = TaskStateTransition.info(" COMPLETED ", 100, " render ", " done ", " ok ", payload);
        TaskStateTransition warn = TaskStateTransition.warn("FAILED", 90, "render", "warn", "retry", null);
        TaskStateTransition error = TaskStateTransition.error("FAILED", 80, "render", "error", "boom", null).withAttempt(" FAILED ", " bad ");

        assertEquals("COMPLETED", info.nextStatus());
        assertEquals("render", info.stage());
        assertEquals("done", info.event());
        assertEquals("ok", info.message());
        assertEquals("INFO", info.level());
        assertSame(payload, info.payload());
        assertFalse(info.updatesAttempt());

        assertEquals("WARN", warn.level());
        assertEquals(Map.of(), warn.payload());

        assertEquals("ERROR", error.level());
        assertEquals("FAILED", error.attemptStatus());
        assertEquals("bad", error.attemptErrorMessage());
        assertTrue(error.updatesAttempt());
    }
}
