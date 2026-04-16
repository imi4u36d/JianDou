package com.jiandou.api.generation.video;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.RemoteVideoTaskSubmission;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class SeedanceVideoModelProviderTest {

    @Test
    void buildRequestBodyAddsFrameInputsAndResolutionMetadata() {
        SeedanceVideoModelProvider provider = new SeedanceVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper())
        );
        Map<String, Object> body = provider.buildSeedanceVideoRequestBody(
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
        assertEquals("9:16", body.get("ratio"));
        assertEquals("720p", body.get("resolution"));
        assertFalse((Boolean) body.get("watermark"));
    }

    @Test
    void submitUsesInjectedHttpClientAndReturnsTaskId() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = (HttpResponse<String>) mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"id\":\"task_seedance_1\"}");
        ArgumentCaptor<HttpRequest> requestCaptor = ArgumentCaptor.forClass(HttpRequest.class);
        when(httpClient.send(requestCaptor.capture(), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        SeedanceVideoModelProvider provider = new SeedanceVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper(), httpClient)
        );

        RemoteVideoTaskSubmission submission = provider.submit(
            profile(),
            new VideoGenerationRequest(
                "seedance-1.5-pro",
                "animate this",
                720,
                1280,
                8,
                "https://example.com/first.png",
                "https://example.com/last.png",
                3,
                true,
                false,
                true,
                true
            )
        );

        HttpRequest request = requestCaptor.getValue();
        assertEquals(URI.create("https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"), request.uri());
        assertEquals("POST", request.method());
        assertEquals("k", request.headers().firstValue("X-Api-Key").orElse(""));
        assertEquals("task_seedance_1", submission.taskId());
        assertEquals("doubao-seedance-1-5-pro-251215", submission.providerModel());
    }

    @Test
    void queryUsesInjectedHttpClientAndParsesPayload() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = (HttpResponse<String>) mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"data\":{\"task_status\":\"SUCCEEDED\",\"video_url\":\"https://example.com/video.mp4\"}}");
        ArgumentCaptor<HttpRequest> requestCaptor = ArgumentCaptor.forClass(HttpRequest.class);
        when(httpClient.send(requestCaptor.capture(), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        SeedanceVideoModelProvider provider = new SeedanceVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper(), httpClient)
        );

        RemoteTaskQueryResult result = provider.query(profile(), "task/123");

        HttpRequest request = requestCaptor.getValue();
        assertEquals(URI.create("https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/task%2F123"), request.uri());
        assertEquals("GET", request.method());
        assertEquals("k", request.headers().firstValue("X-Api-Key").orElse(""));
        assertEquals("https://example.com/video.mp4", result.videoUrl());
        assertEquals("SUCCEEDED", result.status());
    }

    private MediaProviderProfile profile() {
        return new MediaProviderProfile(
            new MediaProviderConfig(
                "video",
                "seedance-1.5-pro",
                "seedance",
                "seedance-1.5-pro",
                "k",
                "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
                "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
                60,
                "test"
            ),
            new MediaProviderCapabilities(true, false, false, false, 8, 600, "i2v", List.of(), List.of(4, 6, 8, 10))
        );
    }
}
