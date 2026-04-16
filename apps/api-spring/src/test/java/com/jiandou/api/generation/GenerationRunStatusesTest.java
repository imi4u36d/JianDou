package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class GenerationRunStatusesTest {

    @Test
    void activeStatusesAreRecognized() {
        assertTrue(GenerationRunStatuses.isActive(" queued "));
        assertTrue(GenerationRunStatuses.isActive("RUNNING"));
        assertFalse(GenerationRunStatuses.isActive("completed"));
    }

    @Test
    void successfulStatusesAreRecognized() {
        assertTrue(GenerationRunStatuses.isSuccessful("succeeded"));
        assertTrue(GenerationRunStatuses.isSuccessful(" SUCCESS "));
        assertFalse(GenerationRunStatuses.isSuccessful("failed"));
    }

    @Test
    void normalizeHandlesNullAndWhitespace() {
        assertEquals("", GenerationRunStatuses.normalize(null));
        assertEquals("running", GenerationRunStatuses.normalize(" Running "));
    }
}
