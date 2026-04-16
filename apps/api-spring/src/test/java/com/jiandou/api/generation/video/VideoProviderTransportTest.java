package com.jiandou.api.generation.video;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.exception.GenerationProviderException;
import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class VideoProviderTransportTest {

    @Test
    void sendJsonAndDecodeWork() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"task_id\":\"task_1\"}");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        VideoProviderTransport transport = new VideoProviderTransport(new ObjectMapper(), httpClient);

        assertEquals(response, transport.sendJson("https://api.example.com/video", "k", Map.of("prompt", "x"), 5, Map.of("X-Test", "1")));
        assertEquals("task_1", transport.decode("{\"task_id\":\"task_1\"}").get("task_id"));
    }

    @Test
    void sendWrapsTransportErrors() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenThrow(new IOException("network"));
        VideoProviderTransport transport = new VideoProviderTransport(new ObjectMapper(), httpClient);

        GenerationProviderException ex = assertThrows(
            GenerationProviderException.class,
            () -> transport.send(HttpRequest.newBuilder().uri(java.net.URI.create("https://api.example.com")).build(), "video failed")
        );

        assertTrue(ex.getMessage().contains("network"));
    }

    @Test
    void extractionHelpersHandleNestedPayloads() {
        VideoProviderTransport transport = new VideoProviderTransport(new ObjectMapper());
        Map<String, Object> payload = Map.of(
            "output", Map.of("taskId", "task_nested", "status", "running", "message", "processing"),
            "data", Map.of("mediaUrl", "https://cdn/video.mp4")
        );

        assertEquals("task_nested", transport.extractTaskId(payload));
        assertEquals("https://cdn/video.mp4", transport.extractVideoUrl(payload));
        assertEquals("RUNNING", transport.extractTaskStatus(payload));
        assertEquals("processing", transport.extractTaskMessage(payload));
        assertEquals("a%20b", transport.encodePathSegment("a b"));
        assertEquals("https://cdn/video.mp4", transport.extractFirstString(List.of(payload), "mediaUrl"));
        assertEquals(Map.of(), transport.mapValue("not-a-map"));
    }

    @Test
    void decodeThrowsOnInvalidJson() {
        VideoProviderTransport transport = new VideoProviderTransport(new ObjectMapper());

        assertThrows(GenerationProviderException.class, () -> transport.decode("{bad"));
    }
}
