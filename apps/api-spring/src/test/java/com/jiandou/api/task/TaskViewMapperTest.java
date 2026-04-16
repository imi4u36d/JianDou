package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.jiandou.api.task.view.TaskViewMapper;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import com.jiandou.api.config.JiandouStorageProperties;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * 任务视图相关测试。
 */
class TaskViewMapperTest {

    /**
     * 处理转为详情UsesPending时长DiagnosticsWhen规划HasNo已渲染输出。
     */
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

        TaskViewMapper mapper = new TaskViewMapper(storageProperties("../../storage"));
        Map<String, Object> detail = mapper.toDetail(task);

        Object diagnosticsValue = detail.get("durationDiagnostics");
        List<?> diagnostics = assertInstanceOf(List.class, diagnosticsValue);
        Map<?, ?> firstRow = assertInstanceOf(Map.class, diagnostics.get(0));
        assertEquals("pending", firstRow.get("status"));
        assertEquals(null, firstRow.get("actualDurationSeconds"));
        assertEquals(6, firstRow.get("plannedTargetDurationSeconds"));
    }

    /**
     * 处理转为详情Uses时长兜底From已渲染输出When规划Missing。
     */
    @Test
    void toDetailUsesDurationFallbackFromRenderedOutputWhenPlanMissing() {
        TaskRecord task = new TaskRecord();
        task.id = "task_2";
        task.title = "demo";
        task.status = "RENDERING";
        task.outputs.add(Map.of(
            "resultType", "video",
            "clipIndex", 2,
            "durationSeconds", 7.8,
            "extra", Map.of(
                "targetDurationSeconds", 8,
                "minDurationSeconds", 6,
                "maxDurationSeconds", 10,
                "requestedDuration", 7.5,
                "resolvedDurationSeconds", 8
            )
        ));

        TaskViewMapper mapper = new TaskViewMapper(storageProperties("../../storage"));
        Map<String, Object> detail = mapper.toDetail(task);

        List<?> diagnostics = assertInstanceOf(List.class, detail.get("durationDiagnostics"));
        Map<?, ?> firstRow = assertInstanceOf(Map.class, diagnostics.get(0));
        assertEquals(2, firstRow.get("clipIndex"));
        assertEquals(8, firstRow.get("plannedTargetDurationSeconds"));
        assertEquals(6, firstRow.get("plannedMinDurationSeconds"));
        assertEquals(10, firstRow.get("plannedMaxDurationSeconds"));
        assertEquals(7.5d, firstRow.get("requestedDurationSeconds"));
        assertEquals(8.0d, firstRow.get("appliedDurationSeconds"));
        assertEquals("rendered", firstRow.get("status"));
    }

    /**
     * 处理转为列表ItemFallsBack转为执行Context工作节点And阶段ForRunning状态。
     */
    @Test
    void toListItemFallsBackToExecutionContextWorkerAndStageForRunningStatus() {
        TaskRecord task = new TaskRecord();
        task.id = "task_3";
        task.title = "demo";
        task.status = "RUNNING";
        task.executionContext.put("workerInstanceId", "worker_1");
        task.executionContext.put("currentStage", "render");

        TaskViewMapper mapper = new TaskViewMapper(storageProperties("../../storage"));
        Map<String, Object> row = mapper.toListItem(task);

        assertEquals("worker_1", row.get("activeWorkerInstanceId"));
        assertEquals("render", row.get("currentStage"));
    }

    private JiandouStorageProperties storageProperties(String rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir);
        return properties;
    }
}
