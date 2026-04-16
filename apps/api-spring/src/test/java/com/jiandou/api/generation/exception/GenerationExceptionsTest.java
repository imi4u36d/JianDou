package com.jiandou.api.generation.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GenerationExceptionsTest {

    @Test
    void constructorsKeepExpectedMessages() {
        assertEquals("bad config", new GenerationConfigurationException("bad config").getMessage());
        assertEquals("todo", new GenerationNotImplementedException("todo").getMessage());
        assertEquals("provider failed", new GenerationProviderException("provider failed").getMessage());
        assertEquals("generation run not found: run_1", new GenerationRunNotFoundException("run_1").getMessage());
        assertEquals("unsupported generation kind: audio", new UnsupportedGenerationKindException("audio").getMessage());
    }
}
