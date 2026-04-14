package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class RemoteMediaGenerationClientTest {

    private final RemoteMediaGenerationClient client = new RemoteMediaGenerationClient(new ObjectMapper());

    @Test
    void seedream45Uses2kPreset() {
        assertEquals("2K", client.seedreamSize("Doubao-Seedream-4.5", 720, 1280));
    }

    @Test
    void seedream50Keeps1kPreset() {
        assertEquals("1K", client.seedreamSize("seedream-5.0", 720, 1280));
    }

    @Test
    void seedreamRequestIncludesSeedAndDisablesWatermark() {
        Map<String, Object> body = client.buildSeedreamImageRequestBody(
            "doubao-seedream-5-0-260128",
            "a prompt",
            "1K",
            42
        );

        assertEquals(42, body.get("seed"));
        assertFalse((Boolean) body.get("watermark"));
    }

    @Test
    void seedreamRequestOmitsSeedWhenNotProvided() {
        Map<String, Object> body = client.buildSeedreamImageRequestBody(
            "doubao-seedream-5-0-260128",
            "a prompt",
            "1K",
            null
        );

        assertFalse(body.containsKey("seed"));
        assertNull(body.get("seed"));
        assertFalse((Boolean) body.get("watermark"));
    }

    @Test
    void dashscopeVideoRequestBuildsExpectedParameters() {
        Map<String, Object> body = client.buildDashscopeVideoRequestBody(
            "wan2.2-i2v-plus",
            "video prompt",
            720,
            1280,
            8,
            true,
            7
        );

        assertEquals("wan2.2-i2v-plus", body.get("model"));
        @SuppressWarnings("unchecked")
        Map<String, Object> input = (Map<String, Object>) body.get("input");
        assertEquals("video prompt", input.get("prompt"));
        @SuppressWarnings("unchecked")
        Map<String, Object> parameters = (Map<String, Object>) body.get("parameters");
        assertEquals("720*1280", parameters.get("size"));
        assertEquals(8, parameters.get("duration"));
        assertEquals(7, parameters.get("seed"));
    }

    @Test
    void seedanceVideoRequestAddsLastFrameOnlyWhenProvided() {
        Map<String, Object> body = client.buildSeedanceVideoRequestBody(
            "doubao-seedance-1-5-pro-251215",
            "animate this",
            720,
            1280,
            6,
            "https://example.com/first.png",
            "https://example.com/last.png",
            null,
            true,
            false,
            true,
            true
        );

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> content = (List<Map<String, Object>>) body.get("content");
        assertEquals(3, content.size());
        assertEquals("image_url", content.get(1).get("type"));
        assertEquals("first_frame", content.get(1).get("role"));
        assertEquals("last_frame", content.get(2).get("role"));
        assertFalse((Boolean) body.get("watermark"));
    }
}
