package com.jiandou.api.task.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TaskResultTypesTest {

    @Test
    void predicatesNormalizeAndClassifyVideoKinds() {
        assertEquals("video_join", TaskResultTypes.normalize(" VIDEO_JOIN "));
        assertTrue(TaskResultTypes.isVideo("video"));
        assertTrue(TaskResultTypes.isVideo("video_clip"));
        assertTrue(TaskResultTypes.isJoin("joined_video"));
        assertTrue(TaskResultTypes.isPrimaryVideo("video"));
        assertFalse(TaskResultTypes.isPrimaryVideo("video_clip"));
        assertFalse(TaskResultTypes.isJoin("image"));
    }
}
