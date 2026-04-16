package com.jiandou.api.task.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import org.junit.jupiter.api.Test;

class TaskRequestSnapshotFactoryTest {

    @Test
    void createBuildsSnapshotWithDefaultsAndTrimmedValues() {
        ModelRuntimePropertiesResolver resolver = mock(ModelRuntimePropertiesResolver.class);
        when(resolver.value("catalog.defaults", "style_preset", "cinematic")).thenReturn(" noir ");
        when(resolver.value("catalog.defaults", "video_size", "720*1280")).thenReturn(" 1080*1920 ");
        TaskRequestSnapshotFactory factory = new TaskRequestSnapshotFactory(resolver);
        TaskRecord task = new TaskRecord();
        task.setTitle("任务标题");
        task.setCreativePrompt("创意提示");
        task.setAspectRatio("9:16");
        task.setTaskSeed(7);
        task.setMinDurationSeconds(4);
        task.setMaxDurationSeconds(12);
        task.setTranscriptText("字幕");
        CreateGenerationTaskRequest request = new CreateGenerationTaskRequest(
            "ignored",
            null,
            null,
            " text-model ",
            "",
            " image-model ",
            " video-model ",
            " ",
            123,
            "8",
            "auto",
            4,
            12,
            "body",
            true
        );

        GenerationRequestSnapshot snapshot = factory.create(request, task);

        assertEquals("generation", snapshot.taskType());
        assertEquals("任务标题", snapshot.title());
        assertEquals("创意提示", snapshot.creativePrompt());
        assertEquals("9:16", snapshot.aspectRatio());
        assertEquals("noir", snapshot.stylePreset());
        assertEquals("text-model", snapshot.textAnalysisModel());
        assertEquals("", snapshot.visionModel());
        assertEquals("image-model", snapshot.imageModel());
        assertEquals("video-model", snapshot.videoModel());
        assertEquals("1080*1920", snapshot.videoSize());
        assertEquals(7, snapshot.seed());
        assertEquals(false, snapshot.videoDuration().auto());
        assertEquals(8, snapshot.videoDuration().seconds());
        assertEquals(true, snapshot.outputCount().auto());
        assertEquals(4, snapshot.minDurationSeconds());
        assertEquals(12, snapshot.maxDurationSeconds());
        assertEquals("字幕", snapshot.transcriptText());
        assertEquals(true, snapshot.stopBeforeVideoGeneration());
    }

    @Test
    void createRejectsInvalidOutputCount() {
        TaskRequestSnapshotFactory factory = new TaskRequestSnapshotFactory(mock(ModelRuntimePropertiesResolver.class));
        TaskRecord task = new TaskRecord();
        CreateGenerationTaskRequest request = new CreateGenerationTaskRequest(
            "title",
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            "zero",
            null,
            null,
            null,
            null
        );

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () -> factory.create(request, task));

        assertEquals("outputCount 必须为正整数或 auto", ex.getMessage());
    }
}
