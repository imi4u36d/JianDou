package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.generation.application.GenerationApplicationService;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskWorkerRenderStageServiceTest {

    @Test
    void awaitCompletedVideoRunPollsUntilSucceeded() {
        GenerationApplicationService generationApplicationService = mock(GenerationApplicationService.class);
        TaskWorkerRenderStageService service = service(generationApplicationService);
        Map<String, Object> runningRun = Map.of("id", "run_1", "status", "running");
        Map<String, Object> completedRun = Map.of(
            "id", "run_1",
            "status", "succeeded",
            "result", Map.of("outputUrl", "/storage/task/clip1.mp4")
        );
        when(generationApplicationService.getRun("run_1")).thenReturn(completedRun);

        Map<String, Object> resolved = service.awaitCompletedVideoRun(runningRun);

        assertEquals("succeeded", resolved.get("status"));
        verify(generationApplicationService, times(1)).getRun("run_1");
    }

    @Test
    void awaitCompletedVideoRunThrowsWhenFailed() {
        GenerationApplicationService generationApplicationService = mock(GenerationApplicationService.class);
        TaskWorkerRenderStageService service = service(generationApplicationService);
        Map<String, Object> runningRun = Map.of("id", "run_2", "status", "running");
        Map<String, Object> failedRun = Map.of(
            "id", "run_2",
            "status", "failed",
            "result", Map.of(
                "error", "remote failed",
                "metadata", Map.of("taskMessage", "provider timeout")
            )
        );
        when(generationApplicationService.getRun("run_2")).thenReturn(failedRun);

        IllegalStateException error = assertThrows(IllegalStateException.class, () -> service.awaitCompletedVideoRun(runningRun));

        assertEquals(true, error.getMessage().contains("run_2"));
        verify(generationApplicationService, times(1)).getRun("run_2");
    }

    private TaskWorkerRenderStageService service(GenerationApplicationService generationApplicationService) {
        return new TaskWorkerRenderStageService(
            mock(TaskRepository.class),
            mock(TaskExecutionCoordinator.class),
            generationApplicationService,
            mock(TaskExecutionRuntimeSupport.class),
            mock(TaskExecutionArtifactAssembler.class),
            mock(TaskWorkerStatusStageService.class),
            mock(TaskWorkerJoinStageService.class),
            0L,
            2
        );
    }
}
