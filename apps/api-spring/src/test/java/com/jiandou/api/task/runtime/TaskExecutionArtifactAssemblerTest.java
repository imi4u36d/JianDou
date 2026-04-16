package com.jiandou.api.task.runtime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.TaskRecord;
import java.time.OffsetDateTime;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * 任务执行产物Assembler相关测试。
 */
class TaskExecutionArtifactAssemblerTest {

    /**
     * 创建结果FallsBack转为片段时长规划When模型Omits时长。
     */
    @Test
    void createResultFallsBackToClipDurationPlanWhenModelOmitsDuration() {
        LocalMediaArtifactService localMediaArtifactService = mock(LocalMediaArtifactService.class);
        when(localMediaArtifactService.resolveAbsolutePath("/storage/generated/task_demo/running/clip1.mp4"))
            .thenReturn("/tmp/clip1.mp4");
        TaskExecutionArtifactAssembler assembler = new TaskExecutionArtifactAssembler(localMediaArtifactService);
        TaskRecord task = new TaskRecord();
        task.setId("task_demo");
        task.setTitle("demo");

        Map<String, Object> result = assembler.createResult(
            task,
            Map.of("id", "run_video_1"),
            Map.of(
                "mimeType", "video/mp4",
                "metadata", Map.of("taskId", "remote-task-1")
            ),
            Map.of("id", "asset_video_1", "fileUrl", "/storage/generated/task_demo/running/clip1.mp4", "previewUrl", "/storage/generated/task_demo/running/clip1.mp4"),
            Map.of("fileUrl", "/storage/generated/task_demo/running/clip1-first.png", "remoteUrl", "https://example.com/clip1-first.png"),
            Map.of("modelCallId", "model_call_1"),
            "https://example.com/clip1-last.png",
            1,
            6,
            4,
            6
        );

        assertEquals(6.0, result.get("durationSeconds"));
        assertEquals(6.0, result.get("endSeconds"));
        @SuppressWarnings("unchecked")
        Map<String, Object> extra = (Map<String, Object>) result.get("extra");
        assertEquals(6, extra.get("targetDurationSeconds"));
        assertEquals(4, extra.get("minDurationSeconds"));
        assertEquals(6, extra.get("maxDurationSeconds"));
        assertEquals(6.0, extra.get("appliedDurationSeconds"));
    }

    /**
     * 创建ReferenceFrame素材SanitizesSignedURLExtension。
     */
    @Test
    void createReferenceFrameMaterialSanitizesSignedUrlExtension() {
        LocalMediaArtifactService localMediaArtifactService = mock(LocalMediaArtifactService.class);
        when(localMediaArtifactService.materializeArtifact(
            "https://example.com/frame.png?x-oss-process=image/resize,w_720&auth=very-long-token",
            "gen/2026-04-14/task_demo/running",
            "clip2-first.png"
        )).thenReturn(new LocalMediaArtifactService.StoredArtifact(
            "clip2-first.png",
            "/tmp/clip2-first.png",
            "/storage/gen/2026-04-14/task_demo/running/clip2-first.png",
            128L
        ));
        TaskExecutionArtifactAssembler assembler = new TaskExecutionArtifactAssembler(localMediaArtifactService);
        TaskRecord task = new TaskRecord();
        task.setId("task_demo");
        task.setTitle("demo");
        task.setCreatedAt(OffsetDateTime.parse("2026-04-14T12:00:00Z").toString());

        Map<String, Object> material = assembler.createReferenceFrameMaterial(
            task,
            2,
            "https://example.com/frame.png?x-oss-process=image/resize,w_720&auth=very-long-token",
            "first"
        );

        assertEquals("png", material.get("fileExt"));
        assertEquals("clip2-first.png", material.get("originalFileName"));
        assertEquals("clip2-first.png", material.get("storedFileName"));
        assertTrue(String.valueOf(material.get("fileUrl")).endsWith("clip2-first.png"));
    }
}
