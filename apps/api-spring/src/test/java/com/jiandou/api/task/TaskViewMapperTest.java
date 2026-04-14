package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskViewMapperTest {

    @Test
    void toDetailUsesPendingDurationDiagnosticsWhenPlanHasNoRenderedOutput() {
        TaskRecord task = new TaskRecord();
        task.id = "task_1";
        task.title = "demo";
        task.status = "PENDING";
        task.executionContext.put(
            "clipDurationPlan",
            List.of(
                Map.of(
                    "clipIndex", 1,
                    "durationSource", "script",
                    "scriptMinDurationSeconds", 5,
                    "scriptMaxDurationSeconds", 8,
                    "targetDurationSeconds", 6,
                    "minDurationSeconds", 5,
                    "maxDurationSeconds", 8
                )
            )
        );

        TaskViewMapper mapper = new TaskViewMapper("../../storage");
        Map<String, Object> detail = mapper.toDetail(task);

        Object diagnosticsValue = detail.get("durationDiagnostics");
        List<?> diagnostics = assertInstanceOf(List.class, diagnosticsValue);
        Map<?, ?> firstRow = assertInstanceOf(Map.class, diagnostics.get(0));
        assertEquals("pending", firstRow.get("status"));
        assertEquals(null, firstRow.get("actualDurationSeconds"));
        assertEquals(6, firstRow.get("plannedTargetDurationSeconds"));
    }
}
