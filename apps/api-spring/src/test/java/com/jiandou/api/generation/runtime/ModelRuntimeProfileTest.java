package com.jiandou.api.generation.runtime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ModelRuntimeProfileTest {

    @Test
    void accessorsNormalizeValuesAndExposeCapabilities() {
        ModelRuntimeProfile profile = new ModelRuntimeProfile(
            new TextProviderConfig("text", "gpt-4.1", "openai", "gpt-4.1", null, "key", "https://api.example.com/v1", -3, 0.35, -10, "cfg"),
            new TextProviderCapabilities(true, true, true)
        );

        assertTrue(profile.ready());
        assertEquals("text", profile.kind());
        assertEquals("openai", profile.provider());
        assertEquals("gpt-4.1", profile.modelName());
        assertEquals("", profile.fallbackModel());
        assertEquals("key", profile.apiKey());
        assertEquals("https://api.example.com/v1", profile.baseUrl());
        assertEquals(0, profile.timeoutSeconds());
        assertEquals(0.35, profile.temperature());
        assertEquals(0, profile.maxTokens());
        assertEquals("cfg", profile.source());
        assertTrue(profile.supportsSeed());
        assertTrue(profile.supportsResponsesApi());
        assertTrue(profile.prefersChatCompletionsForVision());
        assertEquals("api.example.com", profile.endpointHost());
    }

    @Test
    void nullProfilePartsFallBackToSafeDefaults() {
        ModelRuntimeProfile profile = new ModelRuntimeProfile(null, null);

        assertFalse(profile.ready());
        assertEquals("", profile.kind());
        assertEquals("", profile.provider());
        assertEquals("", profile.modelName());
        assertEquals("", profile.fallbackModel());
        assertEquals("", profile.apiKey());
        assertEquals("", profile.baseUrl());
        assertEquals(0, profile.timeoutSeconds());
        assertEquals(0.0, profile.temperature());
        assertEquals(0, profile.maxTokens());
        assertEquals("", profile.source());
        assertFalse(profile.supportsSeed());
        assertFalse(profile.supportsResponsesApi());
        assertFalse(profile.prefersChatCompletionsForVision());
        assertNull(profile.endpointHost());
    }
}
