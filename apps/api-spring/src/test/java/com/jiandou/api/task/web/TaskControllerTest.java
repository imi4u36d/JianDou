package com.jiandou.api.task.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.task.application.TaskApplicationService;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskControllerTest {

    @Test
    void endpointsDelegateToTaskServiceAndUseConfiguredDefaultLimits() {
        TaskApplicationService service = mock(TaskApplicationService.class);
        JiandouTaskOpsProperties ops = new JiandouTaskOpsProperties();
        ops.setTraceLimit(123);
        ops.setLogLimit(124);
        ops.setStatusHistoryLimit(125);
        ops.setModelCallLimit(126);
        TaskController controller = new TaskController(service, ops);

        CreateGenerationTaskRequest createRequest = new CreateGenerationTaskRequest("title", null, null, null, null, null, null, null, null, null, null, null, null, null, null);
        GenerateCreativePromptRequest promptRequest = new GenerateCreativePromptRequest("title", "9:16", 4, 8, "intro", "outro", "tx");
        RateTaskEffectRequest rateRequest = new RateTaskEffectRequest(5, "good");
        Map<String, Object> row = Map.of("id", "task_1");
        List<Map<String, Object>> rows = List.of(row);
        when(service.createGenerationTask(createRequest)).thenReturn(row);
        when(service.generateCreativePrompt(promptRequest)).thenReturn(row);
        when(service.listTasks("q", "PENDING", "updatedAt")).thenReturn(rows);
        when(service.getTask("task_1")).thenReturn(row);
        when(service.getTrace("task_1", 123)).thenReturn(rows);
        when(service.getLogs("task_1", 124)).thenReturn(rows);
        when(service.getStatusHistory("task_1", 125)).thenReturn(rows);
        when(service.getModelCalls("task_1", 126)).thenReturn(rows);
        when(service.getResults("task_1")).thenReturn(rows);
        when(service.getMaterials("task_1")).thenReturn(rows);
        when(service.getSeedanceTaskResult("remote_1")).thenReturn(row);
        when(service.retryTask("task_1")).thenReturn(row);
        when(service.pauseTask("task_1")).thenReturn(row);
        when(service.continueTask("task_1")).thenReturn(row);
        when(service.terminateTask("task_1")).thenReturn(row);
        when(service.rateTaskEffect("task_1", rateRequest)).thenReturn(row);
        when(service.deleteTask("task_1")).thenReturn(row);

        assertSame(row, controller.createGenerationTask(createRequest));
        assertSame(row, controller.generateCreativePrompt(promptRequest));
        assertSame(rows, controller.listTasks("q", "PENDING", "updatedAt"));
        assertSame(row, controller.getTask("task_1"));
        assertSame(rows, controller.getTrace("task_1", null));
        assertSame(rows, controller.getLogs("task_1", null));
        assertSame(rows, controller.getStatusHistory("task_1", null));
        assertSame(rows, controller.getModelCalls("task_1", null));
        assertSame(rows, controller.getResults("task_1"));
        assertSame(rows, controller.getMaterials("task_1"));
        assertSame(row, controller.getSeedanceTaskResult("remote_1"));
        assertSame(row, controller.retry("task_1"));
        assertSame(row, controller.pause("task_1"));
        assertSame(row, controller.resume("task_1"));
        assertSame(row, controller.terminate("task_1"));
        assertSame(row, controller.rateEffect("task_1", rateRequest));
        assertSame(row, controller.delete("task_1"));

        verify(service).getTrace("task_1", 123);
        verify(service).getLogs("task_1", 124);
        verify(service).getStatusHistory("task_1", 125);
        verify(service).getModelCalls("task_1", 126);
    }

    @Test
    void explicitLimitsOverrideDefaults() {
        TaskApplicationService service = mock(TaskApplicationService.class);
        TaskController controller = new TaskController(service, new JiandouTaskOpsProperties());
        List<Map<String, Object>> rows = List.of(Map.of("id", "task_1"));
        when(service.getTrace("task_1", 5)).thenReturn(rows);
        when(service.getLogs("task_1", 6)).thenReturn(rows);
        when(service.getStatusHistory("task_1", 7)).thenReturn(rows);
        when(service.getModelCalls("task_1", 8)).thenReturn(rows);

        assertEquals(rows, controller.getTrace("task_1", 5));
        assertEquals(rows, controller.getLogs("task_1", 6));
        assertEquals(rows, controller.getStatusHistory("task_1", 7));
        assertEquals(rows, controller.getModelCalls("task_1", 8));
    }
}
