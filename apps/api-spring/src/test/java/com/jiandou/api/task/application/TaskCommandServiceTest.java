package com.jiandou.api.task.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.config.JiandouTaskDefaultsProperties;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.AttemptTriggerType;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import com.jiandou.api.task.domain.TaskArtifactNaming;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.persistence.TaskRepository;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.RateTaskEffectRequest;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;

class TaskCommandServiceTest {

    @TempDir
    Path tempDir;

    private TaskRepository taskRepository;
    private TaskExecutionCoordinator executionCoordinator;
    private ModelRuntimePropertiesResolver modelResolver;
    private TaskRequestSnapshotFactory requestSnapshotFactory;
    private TaskCommandService service;

    @BeforeEach
    void setUp() {
        taskRepository = mock(TaskRepository.class);
        executionCoordinator = mock(TaskExecutionCoordinator.class);
        modelResolver = mock(ModelRuntimePropertiesResolver.class);
        requestSnapshotFactory = mock(TaskRequestSnapshotFactory.class);

        JiandouTaskDefaultsProperties defaults = new JiandouTaskDefaultsProperties();
        defaults.setSourceFileName("source.md");
        defaults.setDefaultAspectRatio("4:3");
        defaults.setDefaultDurationSeconds(6);
        defaults.setEditingMode("standard");
        defaults.setIntroTemplate("intro");
        defaults.setOutroTemplate("outro");

        JiandouStorageProperties storageProperties = new JiandouStorageProperties();
        storageProperties.setRootDir(tempDir.toString());

        service = new TaskCommandService(
            taskRepository,
            executionCoordinator,
            modelResolver,
            requestSnapshotFactory,
            defaults,
            storageProperties
        );

        when(taskRepository.findAll()).thenReturn(List.of());
        when(modelResolver.intValue("catalog.defaults", "video_duration_seconds", 6)).thenReturn(8);
        when(modelResolver.value("pipeline", "default_aspect_ratio", "4:3")).thenReturn("9:16");
        when(requestSnapshotFactory.create(any(), any())).thenReturn(GenerationRequestSnapshot.empty());
    }

    @Test
    void createGenerationTaskPopulatesTaskPersistsDirectoriesAndCoordinates() throws Exception {
        CreateGenerationTaskRequest request = validRequest();
        ArgumentCaptor<TaskRecord> taskCaptor = ArgumentCaptor.forClass(TaskRecord.class);
        ArgumentCaptor<Map<String, Object>> attemptPayload = ArgumentCaptor.forClass(Map.class);

        TaskRecord task = service.createGenerationTask(request);

        verify(taskRepository).save(taskCaptor.capture());
        verify(executionCoordinator).createAttempt(eq(task), eq(AttemptTriggerType.CREATE), attemptPayload.capture());
        verify(executionCoordinator).enqueue(eq(task), eq("dispatch"), eq("task.enqueued"), any());
        verify(executionCoordinator).recordTrace(eq(task), eq("api"), eq("task.created"), any(), eq("INFO"), any());
        verify(executionCoordinator).recomputeQueuePositions(List.of());

        TaskRecord savedTask = taskCaptor.getValue();
        assertSame(task, savedTask);
        assertTrue(task.id().startsWith("task_"));
        assertEquals("Task Title", task.title());
        assertEquals("PENDING", task.status());
        assertEquals(0, task.progress());
        assertEquals("source.md", task.sourceFileName());
        assertEquals("16:9", task.aspectRatio());
        assertEquals(8, task.minDurationSeconds());
        assertEquals(8, task.maxDurationSeconds());
        assertEquals("standard", task.editingMode());
        assertEquals("intro", task.introTemplate());
        assertEquals("outro", task.outroTemplate());
        assertEquals("creative", task.creativePrompt());
        assertEquals(12, task.taskSeed());
        assertEquals("transcript", task.transcriptText());
        assertEquals(GenerationRequestSnapshot.empty(), task.requestSnapshot());
        assertEquals("12", String.valueOf(task.executionContext().get("taskSeed")));
        assertNotNull(task.executionContext().get("artifactBaseRelativeDir"));
        assertTrue(Files.isDirectory(tempDir.resolve(TaskArtifactNaming.taskBaseRelativeDir(task))));
        assertTrue(Files.isDirectory(tempDir.resolve(TaskArtifactNaming.taskRunningRelativeDir(task))));
        assertTrue(Files.isDirectory(tempDir.resolve(TaskArtifactNaming.taskJoinedRelativeDir(task))));

        Map<String, Object> payload = attemptPayload.getValue();
        assertEquals("txt-model", payload.get("textAnalysisModel"));
        assertEquals("vision-model", payload.get("visionModel"));
        assertEquals("image-model", payload.get("imageModel"));
        assertEquals("video-model", payload.get("videoModel"));
    }

    @Test
    void createGenerationTaskRejectsInvalidModelSelection() {
        CreateGenerationTaskRequest request = new CreateGenerationTaskRequest(
            "Task",
            "",
            "",
            "",
            "vision-model",
            "image-model",
            "video-model",
            "720*1280",
            null,
            "auto",
            "auto",
            null,
            null,
            "",
            false
        );

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () -> service.createGenerationTask(request));

        assertTrue(ex.getMessage().contains("textAnalysisModel"));
    }

    @Test
    void retryBuildsResumePayloadFromStoryboardAndExistingOutputs() {
        TaskRecord task = new TaskRecord();
        task.setRetryCount(1);
        task.setStoryboardScript("storyboard");
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 1));
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 2));
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 4));

        ArgumentCaptor<Map<String, Object>> payloadCaptor = ArgumentCaptor.forClass(Map.class);

        TaskRecord returned = service.retry(task);

        assertSame(task, returned);
        assertEquals(2, task.retryCount());
        assertEquals("", task.errorMessage());
        verify(executionCoordinator).createAttempt(eq(task), eq(AttemptTriggerType.RETRY), payloadCaptor.capture());
        verify(executionCoordinator).enqueue(eq(task), eq("dispatch"), eq("task.retry_requested"), any());
        Map<String, Object> payload = payloadCaptor.getValue();
        assertEquals("retry", payload.get("triggerType"));
        assertEquals(2, payload.get("retryCount"));
        assertEquals("render", payload.get("resumeFromStage"));
        assertEquals(3, payload.get("resumeFromClipIndex"));
        assertEquals(List.of(1, 2, 4), payload.get("existingClipIndices"));
        assertEquals(true, payload.get("reuseStoryboard"));
    }

    @Test
    void pauseClearsQueueFlagsAndTransitionsTask() {
        TaskRecord task = new TaskRecord();
        task.setQueued(true);
        task.setQueuePosition(3);
        task.setProgress(44);

        TaskRecord returned = service.pause(task);

        assertSame(task, returned);
        assertEquals(false, task.isQueued());
        assertNull(task.queuePosition());
        verify(executionCoordinator).dequeue(task);
        verify(executionCoordinator).transitionTask(eq(task), argThat(transition ->
            "PAUSED".equals(transition.nextStatus())
                && transition.progress() == 44
                && "task.paused".equals(transition.event())
        ));
    }

    @Test
    void resumeCreatesContinueAttempt() {
        TaskRecord task = new TaskRecord();
        task.setRetryCount(3);
        ArgumentCaptor<Map<String, Object>> payloadCaptor = ArgumentCaptor.forClass(Map.class);

        TaskRecord returned = service.resume(task);

        assertSame(task, returned);
        verify(executionCoordinator).createAttempt(eq(task), eq(AttemptTriggerType.CONTINUE), payloadCaptor.capture());
        verify(executionCoordinator).enqueue(eq(task), eq("dispatch"), eq("task.continue_requested"), any());
        assertEquals(Map.of("triggerType", "continue", "retryCount", 3), payloadCaptor.getValue());
    }

    @Test
    void terminateAppliesMutatorAndTransitionsTask() {
        doAnswer(invocation -> {
            TaskRecord task = invocation.getArgument(0);
            @SuppressWarnings("unchecked")
            Consumer<TaskRecord> mutator = invocation.getArgument(2);
            mutator.accept(task);
            return null;
        }).when(executionCoordinator).transitionTask(any(TaskRecord.class), any(), any());

        TaskRecord task = new TaskRecord();
        task.setQueued(true);
        task.setQueuePosition(2);
        task.setProgress(50);

        TaskRecord returned = service.terminate(task);

        assertSame(task, returned);
        assertEquals(false, task.isQueued());
        assertNull(task.queuePosition());
        assertEquals("任务已手动终止。", task.errorMessage());
        assertNotNull(task.finishedAt());
        verify(executionCoordinator).transitionTask(eq(task), argThat(transition ->
            "FAILED".equals(transition.nextStatus())
                && "TERMINATED".equals(transition.attemptStatus())
                && "task.terminated".equals(transition.event())
        ), any());
    }

    @Test
    void rateEffectPersistsTaskAndRecordsTrace() {
        TaskRecord task = new TaskRecord();
        task.setTaskSeed(99);

        TaskRecord returned = service.rateEffect(task, new RateTaskEffectRequest(5, " nice "));

        assertSame(task, returned);
        assertEquals(5, task.effectRating());
        assertEquals("nice", task.effectRatingNote());
        assertNotNull(task.ratedAt());
        assertEquals(5, task.executionContext().get("effectRating"));
        assertEquals("nice", task.executionContext().get("effectRatingNote"));
        verify(taskRepository).save(task);
        verify(executionCoordinator).recordTrace(eq(task), eq("feedback"), eq("task.effect_rated"), any(), eq("INFO"), any());
    }

    @Test
    void rateEffectRejectsInvalidInput() {
        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> service.rateEffect(new TaskRecord(), new RateTaskEffectRequest(6, "bad"))
        );

        assertTrue(ex.getMessage().contains("effectRating"));
    }

    @Test
    void deleteDequeuesTaskAndDeletesRepositoryRow() {
        TaskRecord task = new TaskRecord();
        task.setId("task_delete");

        Map<String, Object> payload = service.delete(task);

        assertEquals(Map.of("taskId", "task_delete", "deleted", true), payload);
        verify(executionCoordinator).dequeue(task);
        verify(executionCoordinator).recomputeQueuePositions(List.of());
        verify(taskRepository).delete("task_delete");
    }

    private CreateGenerationTaskRequest validRequest() {
        return new CreateGenerationTaskRequest(
            " Task Title ",
            " creative ",
            " 16:9 ",
            " txt-model ",
            " vision-model ",
            " image-model ",
            " video-model ",
            "720*1280",
            12,
            "auto",
            "auto",
            null,
            null,
            " transcript ",
            false
        );
    }
}
