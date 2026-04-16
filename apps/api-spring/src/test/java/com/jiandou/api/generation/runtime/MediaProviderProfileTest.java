package com.jiandou.api.generation.runtime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertIterableEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class MediaProviderProfileTest {

    @Test
    void accessorsNormalizeValuesAndCopyCapabilities() {
        List<String> supportedSizes = new ArrayList<>(List.of("720*1280"));
        List<Integer> supportedDurations = new ArrayList<>(List.of(8));
        MediaProviderProfile profile = new MediaProviderProfile(
            new MediaProviderConfig("video", "seedance-v1", "volcengine", "seedance-v1", "key", "https://video.example.com/api", "https://task.example.com/api", -5, "cfg"),
            new MediaProviderCapabilities(true, true, false, true, -3, 15, null, supportedSizes, supportedDurations)
        );
        supportedSizes.add("1080*1920");
        supportedDurations.add(12);

        assertTrue(profile.ready());
        assertEquals("video", profile.kind());
        assertEquals("seedance-v1", profile.requestedModel());
        assertEquals("volcengine", profile.provider());
        assertEquals("seedance-v1", profile.modelName());
        assertEquals("key", profile.apiKey());
        assertEquals("https://video.example.com/api", profile.baseUrl());
        assertEquals("https://task.example.com/api", profile.taskBaseUrl());
        assertEquals(0, profile.timeoutSeconds());
        assertEquals("cfg", profile.source());
        assertTrue(profile.supportsSeed());
        assertTrue(profile.promptExtend());
        assertFalse(profile.cameraFixed());
        assertTrue(profile.watermark());
        assertEquals(0, profile.pollIntervalSeconds());
        assertEquals(15, profile.pollTimeoutSeconds());
        assertEquals("", profile.generationMode());
        assertIterableEquals(List.of("720*1280"), profile.supportedSizes());
        assertIterableEquals(List.of(8), profile.supportedDurations());
        assertEquals("video.example.com", profile.endpointHost());
        assertEquals("task.example.com", profile.taskEndpointHost());
    }

    @Test
    void nullProfilePartsFallBackToSafeDefaults() {
        MediaProviderProfile profile = new MediaProviderProfile(null, null);

        assertFalse(profile.ready());
        assertEquals("", profile.kind());
        assertEquals("", profile.requestedModel());
        assertEquals("", profile.provider());
        assertEquals("", profile.modelName());
        assertEquals("", profile.apiKey());
        assertEquals("", profile.baseUrl());
        assertEquals("", profile.taskBaseUrl());
        assertEquals(0, profile.timeoutSeconds());
        assertEquals("", profile.source());
        assertFalse(profile.supportsSeed());
        assertFalse(profile.promptExtend());
        assertFalse(profile.cameraFixed());
        assertFalse(profile.watermark());
        assertEquals(0, profile.pollIntervalSeconds());
        assertEquals(0, profile.pollTimeoutSeconds());
        assertEquals("", profile.generationMode());
        assertIterableEquals(List.of(), profile.supportedSizes());
        assertIterableEquals(List.of(), profile.supportedDurations());
        assertNull(profile.endpointHost());
        assertNull(profile.taskEndpointHost());
    }
}
