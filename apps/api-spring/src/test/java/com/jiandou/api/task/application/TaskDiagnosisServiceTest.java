package com.jiandou.api.task.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.view.TaskViewMapper;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskDiagnosisServiceTest {

    @Test
    void diagnoseReportsFailedIncompleteTask() {
        TaskViewMapper taskViewMapper = mock(TaskViewMapper.class);
        TaskDiagnosisService service = new TaskDiagnosisService(taskViewMapper);
        TaskRecord task = new TaskRecord();
        task.setId("task_1");
        task.setTitle("任务 1");
        task.setStatus(TaskStatus.FAILED.value());
        task.setQueued(false);
        task.setErrorMessage("render failed");
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 1, "downloadUrl", "/v1.mp4", "extra", Map.of("hasAudio", false)));
        when(taskViewMapper.toDetail(task)).thenReturn(Map.of(
            "monitoring", Map.of(
                "plannedClipCount", 2,
                "contiguousRenderedClipCount", 1,
                "latestRenderedClipIndex", 1,
                "resumeFromStage", "render",
                "resumeFromClipIndex", 2,
                "activeAttemptStatus", "FAILED",
                "activeWorkerInstanceId", "worker-1"
            )
        ));

        Map<String, Object> diagnosis = service.diagnose(task);

        assertEquals("high", diagnosis.get("severity"));
        assertTrue(String.valueOf(diagnosis.get("summary")).contains("高优先级异常"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> findings = (List<Map<String, Object>>) diagnosis.get("findings");
        assertEquals("task_failed", findings.get(0).get("code"));
        assertEquals("执行 retry，按已有分镜从失败镜头继续恢复。", map(diagnosis.get("recovery")).get("recommendedAction"));
        assertEquals(List.of(2), map(diagnosis.get("continuity")).get("missingClipIndices"));
        assertEquals(false, map(diagnosis.get("outputs")).get("hasAudioClip"));
        assertEquals("worker-1", map(diagnosis.get("queue")).get("activeWorkerInstanceId"));
    }

    @Test
    void diagnoseReturnsHealthyFindingForConsistentTask() {
        TaskViewMapper taskViewMapper = mock(TaskViewMapper.class);
        TaskDiagnosisService service = new TaskDiagnosisService(taskViewMapper);
        TaskRecord task = new TaskRecord();
        task.setId("task_2");
        task.setTitle("任务 2");
        task.setStatus(TaskStatus.COMPLETED.value());
        task.setQueued(true);
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 1, "downloadUrl", "/v2.mp4", "extra", Map.of("hasAudio", true)));
        when(taskViewMapper.toDetail(task)).thenReturn(Map.of(
            "monitoring", Map.of(
                "plannedClipCount", 1,
                "contiguousRenderedClipCount", 1,
                "latestRenderedClipIndex", 1,
                "activeAttemptStatus", "COMPLETED",
                "activeWorkerInstanceId", "worker-2"
            )
        ));

        Map<String, Object> diagnosis = service.diagnose(task);

        assertEquals("info", diagnosis.get("severity"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> findings = (List<Map<String, Object>>) diagnosis.get("findings");
        assertEquals(List.of("healthy"), findings.stream().map(item -> String.valueOf(item.get("code"))).toList());
        assertTrue(String.valueOf(diagnosis.get("summary")).contains("整体健康"));
        assertEquals("继续观察最新 trace 与 stage run，如长时间无进展再执行 retry。", map(diagnosis.get("recovery")).get("recommendedAction"));
        assertEquals(true, map(diagnosis.get("outputs")).get("hasAudioClip"));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }
}
