package com.jiandou.api.task.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.task.TaskRecord;
import org.junit.jupiter.api.Test;

class TaskArtifactNamingTest {

    @Test
    void namingUsesTaskDateAndSafeTaskId() {
        TaskRecord task = new TaskRecord();
        task.setId("task/42");
        task.setCreatedAt("2026-04-16T12:00:00Z");

        assertEquals("gen/2026-04-16/task_42", TaskArtifactNaming.taskArtifactRelativeDir(task));
        assertEquals("gen/2026-04-16/task_42/running", TaskArtifactNaming.taskRunningRelativeDir(task));
        assertEquals("gen/2026-04-16/task_42/joined", TaskArtifactNaming.taskJoinedRelativeDir(task));
    }

    @Test
    void namingNormalizesClipNamesExtensionsAndJoinTargets() {
        assertEquals("storyboard.json", TaskArtifactNaming.storyboardFileName(null, ".json"));
        assertEquals("clip1-first.png", TaskArtifactNaming.keyframeFileName(null, 0, "PNG"));
        assertEquals("clip3-last.jpg", TaskArtifactNaming.lastFrameFileName(3, "jpg"));
        assertEquals("clip1-first.bin", TaskArtifactNaming.clipFrameFileName(0, " weird ", ""));
        assertEquals("clip1.mp4", TaskArtifactNaming.clipFileName(0, ".mp4"));
        assertEquals("join-1-2-3.mov", TaskArtifactNaming.joinFileName(null, 3, "mov"));
        assertEquals("join-1-2", TaskArtifactNaming.joinName(1));
    }

    @Test
    void namingFallsBackWhenTaskDataIsMissing() {
        String baseDir = TaskArtifactNaming.taskBaseRelativeDir(null);

        assertTrue(baseDir.endsWith("/task-unknown"));
    }
}
