package com.jiandou.api.generation.video;

import static org.junit.jupiter.api.Assertions.assertEquals;
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

class DashscopeVideoModelProviderTest {

    @Test
    void buildRequestBodyIncludesExpectedParameters() {
        DashscopeVideoModelProvider provider = new DashscopeVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper())
        );
        Map<String, Object> body = provider.buildDashscopeVideoRequestBody(
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
    void submitUsesTransportRequestAndParsesTaskId() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = (HttpResponse<String>) mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"output\":{\"task_id\":\"task_123\"}}");
        ArgumentCaptor<HttpRequest> requestCaptor = ArgumentCaptor.forClass(HttpRequest.class);
        when(httpClient.send(requestCaptor.capture(), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        DashscopeVideoModelProvider provider = new DashscopeVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper(), httpClient)
        );

        RemoteVideoTaskSubmission submission = provider.submit(
            profile(),
            new VideoGenerationRequest("wan2.2-i2v-plus", "video prompt", 720, 1280, 8, "", "", 7, false, false, false, true)
        );

        HttpRequest request = requestCaptor.getValue();
        assertEquals(URI.create("https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"), request.uri());
        assertEquals("POST", request.method());
        assertEquals("enable", request.headers().firstValue("X-DashScope-Async").orElse(""));
        assertEquals("task_123", submission.taskId());
        assertEquals("wan2.2-i2v-plus", submission.providerModel());
    }

    @Test
    void queryUsesInjectedHttpClientAndParsesPayload() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = (HttpResponse<String>) mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"output\":{\"task_status\":\"SUCCEEDED\",\"video_url\":\"https://example.com/video.mp4\"}}");
        ArgumentCaptor<HttpRequest> requestCaptor = ArgumentCaptor.forClass(HttpRequest.class);
        when(httpClient.send(requestCaptor.capture(), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        DashscopeVideoModelProvider provider = new DashscopeVideoModelProvider(
            new VideoProviderTransport(new ObjectMapper(), httpClient)
        );

        RemoteTaskQueryResult result = provider.query(profile(), "task 123");

        HttpRequest request = requestCaptor.getValue();
        assertEquals(URI.create("https://dashscope.aliyuncs.com/api/v1/tasks/task%20123"), request.uri());
        assertEquals("GET", request.method());
        assertEquals("https://example.com/video.mp4", result.videoUrl());
        assertEquals("SUCCEEDED", result.status());
    }

    private MediaProviderProfile profile() {
        return new MediaProviderProfile(
            new MediaProviderConfig(
                "video",
                "wan2.2-i2v-plus",
                "wan",
                "wan2.2-i2v-plus",
                "k",
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
                "https://dashscope.aliyuncs.com/api/v1/tasks",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, true, false, false, 8, 600, "i2v", List.of(), List.of(4, 6, 8))
        );
    }
}
