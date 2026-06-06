package com.jiandou.api.admin.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.admin.application.AdminModelConfigService;
import com.jiandou.api.admin.dto.AdminModelConfigKeyUpdateRequest;
import com.jiandou.api.admin.dto.AdminModelConfigResponse;
import com.jiandou.api.admin.dto.AdminModelConfigValidationResponse;
import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import com.jiandou.api.task.web.dto.TaskListItemResponse;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AdminControllerTest {

    @Test
    void adminEndpointsDelegateAndUseDefaultLimits() {
        TaskApplicationService service = mock(TaskApplicationService.class);
        AdminModelConfigService modelConfigService = mock(AdminModelConfigService.class);
        JiandouTaskOpsProperties ops = new JiandouTaskOpsProperties();
        ops.setTraceLimit(11);
        ops.setAdminTraceLimit(12);
        ops.setAdminWorkerLimit(13);
        ops.setAdminQueueLimit(14);
        AdminController controller = new AdminController(service, ops, modelConfigService);
        Map<String, Object> row = Map.of("id", "task_1");
        List<Map<String, Object>> rows = List.of(row);
        List<TaskListItemResponse> taskRows = List.of(new TaskListItemResponse(
            "task_1", null, null, null, 0, null, null, null, null, 0, 0, 0, null, null,
            0, null, null, null, null, false, false, 0, null, false, null, null, null,
            0, 0, null, null, null, null, null, null, null, null, null, null, null, null
        ));
        RateTaskEffectRequest rateRequest = new RateTaskEffectRequest(4, "nice");
        AdminModelConfigResponse configResponse = new AdminModelConfigResponse("cfg", null, null, List.of(), List.of(), List.of());
        AdminModelConfigKeyUpdateRequest draftRequest = new AdminModelConfigKeyUpdateRequest(
            List.of(new AdminModelConfigKeyUpdateRequest.ProviderKeyInput("deepseek", "secret"))
        );
        AdminModelConfigValidationResponse validationResponse = new AdminModelConfigValidationResponse(true, configResponse);
        when(service.adminOverview()).thenReturn(row);
        when(service.adminListTasks("q", "FAILED", "updatedAt")).thenReturn(taskRows);
        when(service.adminGetTask("task_1")).thenReturn(row);
        when(service.getTrace("task_1", 11)).thenReturn(rows);
        when(service.adminTraces("task_1", "render", "WARN", "q", 12)).thenReturn(rows);
        when(service.adminWorkers(13)).thenReturn(rows);
        when(service.adminWorker("worker_1")).thenReturn(row);
        when(service.adminQueueOverview(14)).thenReturn(row);
        when(service.adminQueueEvents("task_1", 14)).thenReturn(rows);
        when(service.adminQueueEvents(null, 14)).thenReturn(rows);
        when(service.adminTaskDiagnosis("task_1")).thenReturn(row);
        when(service.retryTask("task_1")).thenReturn(row);
        when(service.adminTerminateTask("task_1")).thenReturn(row);
        when(service.rateTaskEffect("task_1", rateRequest)).thenReturn(row);
        when(service.deleteTask("task_1")).thenReturn(row);
        when(modelConfigService.read()).thenReturn(configResponse);
        when(modelConfigService.validateKeys(draftRequest)).thenReturn(validationResponse);
        when(modelConfigService.saveKeys(draftRequest)).thenReturn(configResponse);

        assertSame(row, controller.overview());
        assertSame(configResponse, controller.modelConfig());
        assertSame(validationResponse, controller.validateModelConfig(draftRequest));
        assertSame(configResponse, controller.saveModelConfigKeys(draftRequest));
        assertSame(taskRows, controller.listTasks("q", "FAILED", "updatedAt"));
        assertSame(row, controller.getTask("task_1"));
        assertSame(rows, controller.getTaskTrace("task_1", null));
        assertSame(rows, controller.listTraces("task_1", "render", "WARN", "q", null));
        assertSame(rows, controller.listWorkers(null));
        assertSame(row, controller.getWorker("worker_1"));
        assertSame(row, controller.queueOverview(null));
        assertSame(rows, controller.listQueueEvents(null, null));
        assertSame(rows, controller.getTaskQueueEvents("task_1", null));
        assertSame(row, controller.getTaskDiagnosis("task_1"));
        assertSame(row, controller.retry("task_1"));
        assertSame(row, controller.terminate("task_1"));
        assertSame(row, controller.rateEffect("task_1", rateRequest));
        assertSame(row, controller.delete("task_1"));
    }

    @Test
    void bulkOperationsProcessAllRequestedTaskIds() {
        TaskApplicationService service = mock(TaskApplicationService.class);
        AdminController controller = new AdminController(service, new JiandouTaskOpsProperties(), mock(AdminModelConfigService.class));
        AdminController.TaskIdsRequest request = new AdminController.TaskIdsRequest(List.of("task_1", "task_2"));

        Map<String, Object> deleteResult = controller.bulkDelete(request);
        Map<String, Object> retryResult = controller.bulkRetry(request);

        assertEquals("delete", deleteResult.get("action"));
        assertEquals(2, deleteResult.get("requestedCount"));
        assertEquals(List.of("task_1", "task_2"), deleteResult.get("succeededTaskIds"));
        assertEquals("retry", retryResult.get("action"));
        assertEquals(2, retryResult.get("requestedCount"));
        assertEquals(List.of("task_1", "task_2"), retryResult.get("succeededTaskIds"));
        verify(service, times(1)).deleteTask("task_1");
        verify(service, times(1)).deleteTask("task_2");
        verify(service, times(1)).retryTask("task_1");
        verify(service, times(1)).retryTask("task_2");
    }

    @Test
    void bulkTerminateReturnsPerTaskFailures() {
        TaskApplicationService service = mock(TaskApplicationService.class);
        AdminController controller = new AdminController(service, new JiandouTaskOpsProperties(), mock(AdminModelConfigService.class));
        AdminController.TaskIdsRequest request = new AdminController.TaskIdsRequest(List.of("task_1", "task_2"));
        when(service.adminTerminateTask("task_2")).thenThrow(new IllegalArgumentException("只能终止排队或执行中的任务。"));

        Map<String, Object> result = controller.bulkTerminate(request);

        assertEquals("terminate", result.get("action"));
        assertEquals(2, result.get("requestedCount"));
        assertEquals(List.of("task_1"), result.get("succeededTaskIds"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> failed = (List<Map<String, Object>>) result.get("failed");
        assertEquals(1, failed.size());
        assertEquals("task_2", failed.get(0).get("taskId"));
        assertEquals("只能终止排队或执行中的任务。", failed.get(0).get("reason"));
        verify(service).adminTerminateTask("task_1");
        verify(service).adminTerminateTask("task_2");
    }
}
