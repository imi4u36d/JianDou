package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.generation.application.GenerationApplicationService;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class TaskWorkerRenderStageServiceTest {

    private TaskRepository taskRepository;
    private TaskExecutionCoordinator executionCoordinator;
    private GenerationApplicationService generationApplicationService;
    private TaskExecutionRuntimeSupport runtimeSupport;
    private TaskExecutionArtifactAssembler artifactAssembler;
    private TaskWorkerStatusStageService statusStageService;
    private TaskWorkerJoinStageService joinStageService;

    @BeforeEach
    void setUp() {
        taskRepository = mock(TaskRepository.class);
        executionCoordinator = mock(TaskExecutionCoordinator.class);
        generationApplicationService = mock(GenerationApplicationService.class);
        runtimeSupport = mock(TaskExecutionRuntimeSupport.class);
        artifactAssembler = mock(TaskExecutionArtifactAssembler.class);
        statusStageService = mock(TaskWorkerStatusStageService.class);
        joinStageService = mock(TaskWorkerJoinStageService.class);
    }

    @Test
    void awaitCompletedVideoRunPollsUntilSucceeded() {
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

    @Test
    void renderReusesPreviousClipLastFrameForNextClip() {
        TaskWorkerRenderStageService service = service(generationApplicationService);
        TaskRecord task = new TaskRecord();
        task.id = "task_1";
        task.title = "demo";
        task.aspectRatio = "9:16";
        task.executionContext = new LinkedHashMap<>();
        TaskWorkerExecutionContext runContext = new TaskWorkerExecutionContext("worker_1", "spring", "queue");

        Map<String, Object> imageRun1 = Map.of(
            "id", "image_run_1",
            "status", "succeeded",
            "result", Map.of(
                "outputUrl", "/storage/gen/_runs/task_1/clip1-first.png",
                "metadata", Map.of("remoteSourceUrl", "https://example.com/clip1-first.png")
            )
        );
        Map<String, Object> videoRun1 = Map.of(
            "id", "video_run_1",
            "status", "succeeded",
            "result", Map.of(
                "outputUrl", "/storage/gen/_runs/task_1/clip1.mp4",
                "thumbnailUrl", "/storage/gen/_runs/task_1/clip1-first.png",
                "hasAudio", true,
                "metadata", Map.of(
                    "remoteSourceUrl", "https://example.com/clip1.mp4",
                    "firstFrameUrl", "https://example.com/clip1-first.png",
                    "taskId", "remote_task_1"
                )
            )
        );
        Map<String, Object> videoRun2 = Map.of(
            "id", "video_run_2",
            "status", "succeeded",
            "result", Map.of(
                "outputUrl", "/storage/gen/_runs/task_1/clip2.mp4",
                "thumbnailUrl", "/storage/gen/_runs/task_1/clip2-first.png",
                "hasAudio", true,
                "metadata", Map.of(
                    "remoteSourceUrl", "https://example.com/clip2.mp4",
                    "firstFrameUrl", "https://example.com/clip1-last.png",
                    "taskId", "remote_task_2"
                )
            )
        );
        when(generationApplicationService.createRun(anyMap())).thenReturn(imageRun1, videoRun1, videoRun2);
        when(runtimeSupport.buildImageRunRequest(any(), anyInt(), anyString(), anyInt(), anyInt(), anyString(), anyInt(), anyString()))
            .thenAnswer(invocation -> Map.of(
                "kind", "image",
                "input", Map.of(
                    "clipIndex", invocation.getArgument(1),
                    "prompt", invocation.getArgument(2),
                    "referenceImageUrl", invocation.getArgument(5),
                    "frameRole", invocation.getArgument(7)
                )
            ));
        when(runtimeSupport.buildVideoRunRequest(any(), anyInt(), anyString(), anyString(), anyInt(), anyInt(), anyInt(), anyString(), anyString()))
            .thenAnswer(invocation -> Map.of(
                "kind", "video",
                "input", Map.of(
                    "clipIndex", invocation.getArgument(1),
                    "prompt", invocation.getArgument(2),
                    "firstFrameUrl", invocation.getArgument(7),
                    "lastFrameUrl", invocation.getArgument(8)
                )
            ));
        when(statusStageService.createModelCall(any(), anyString(), anyString(), anyMap(), anyMap(), anyMap(), anyInt(), anyString()))
            .thenReturn(Map.of("modelCallId", "model_call"));
        when(artifactAssembler.createImageMaterial(any(), anyMap(), anyMap(), anyInt(), anyString()))
            .thenReturn(Map.of(
                "id", "asset_image_1",
                "fileUrl", "/storage/gen/_runs/task_1/clip1-first.png",
                "remoteUrl", "https://example.com/clip1-first.png"
            ));
        when(artifactAssembler.createReferenceFrameMaterial(any(), anyInt(), anyString(), anyString()))
            .thenReturn(Map.of(
                "id", "asset_image_2",
                "fileUrl", "/storage/gen/_runs/task_1/clip2-first.png",
                "remoteUrl", "https://example.com/clip1-last.png"
            ));
        when(artifactAssembler.extractLastFrameUrl(any())).thenReturn("https://example.com/clip1-last.png", "");
        when(artifactAssembler.createVideoMaterial(any(), anyMap(), anyMap(), anyInt(), anyInt()))
            .thenReturn(
                Map.of("id", "asset_video_1", "fileUrl", "/storage/gen/_runs/task_1/clip1.mp4", "previewUrl", "/storage/gen/_runs/task_1/clip1.mp4"),
                Map.of("id", "asset_video_2", "fileUrl", "/storage/gen/_runs/task_1/clip2.mp4", "previewUrl", "/storage/gen/_runs/task_1/clip2.mp4")
            );
        when(artifactAssembler.createResult(any(), anyMap(), anyMap(), anyMap(), anyMap(), anyMap(), anyString(), anyInt(), anyInt(), anyInt(), anyInt()))
            .thenReturn(Map.of("id", "result"));

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = List.of(
            new TaskStoryboardPlanner.StoryboardShotPlan(
                1,
                "01",
                "scene-1",
                "first-frame-1",
                "clip-1-last",
                "raises head",
                "slow push in",
                "6",
                "first-frame-1",
                "clip-1-last；动作延展：raises head；运镜：slow push in"
            ),
            new TaskStoryboardPlanner.StoryboardShotPlan(
                2,
                "02",
                "scene-1",
                "",
                "clip-2-last",
                "turns around",
                "slow pan",
                "6",
                "",
                "clip-2-last；动作延展：turns around；运镜：slow pan"
            )
        );

        service.render(
            task,
            runContext,
            new TaskWorkerRenderStageService.RenderStageRequest(
                false,
                1,
                0,
                "",
                1,
                List.of(),
                shotPlans,
                List.of(new int[] {6, 6, 6}, new int[] {6, 6, 6}),
                720,
                1280,
                12,
                "720*1280",
                ""
            )
        );

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(3)).createRun(requestCaptor.capture());
        List<Map<String, Object>> capturedRequests = requestCaptor.getAllValues();
        @SuppressWarnings("unchecked")
        Map<String, Object> firstImageInput = (Map<String, Object>) capturedRequests.get(0).get("input");
        @SuppressWarnings("unchecked")
        Map<String, Object> firstVideoInput = (Map<String, Object>) capturedRequests.get(1).get("input");
        @SuppressWarnings("unchecked")
        Map<String, Object> secondVideoInput = (Map<String, Object>) capturedRequests.get(2).get("input");
        assertEquals("first-frame-1", firstImageInput.get("prompt"));
        assertEquals("", firstVideoInput.get("lastFrameUrl"));
        assertEquals("https://example.com/clip1-last.png", secondVideoInput.get("firstFrameUrl"));
        assertEquals("", secondVideoInput.get("lastFrameUrl"));
        verify(artifactAssembler, times(1)).createImageMaterial(any(), anyMap(), anyMap(), anyInt(), anyString());
        verify(artifactAssembler, times(1)).createReferenceFrameMaterial(task, 2, "https://example.com/clip1-last.png", "first");
        verifyNoMoreInteractions(generationApplicationService);
    }

    private TaskWorkerRenderStageService service(GenerationApplicationService generationApplicationService) {
        return new TaskWorkerRenderStageService(
            taskRepository,
            executionCoordinator,
            generationApplicationService,
            runtimeSupport,
            artifactAssembler,
            statusStageService,
            joinStageService,
            0L,
            2
        );
    }
}
