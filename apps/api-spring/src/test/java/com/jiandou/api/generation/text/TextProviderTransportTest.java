package com.jiandou.api.generation.text;

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
import org.mockito.ArgumentCaptor;

class TextProviderTransportTest {

    @Test
    void sendJsonBuildsRequestAndReturnsResponse() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"ok\":true}");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        TextProviderTransport transport = new TextProviderTransport(new ObjectMapper(), httpClient);

        HttpResponse<String> result = transport.sendJson("https://api.example.com/v1/chat", "secret", Map.of("a", 1), 5, "text failed");

        assertEquals(response, result);
    }

    @Test
    void sendWrapsHttpFailures() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(502);
        when(response.body()).thenReturn("bad gateway");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        TextProviderTransport transport = new TextProviderTransport(new ObjectMapper(), httpClient);
        HttpRequest request = HttpRequest.newBuilder().uri(java.net.URI.create("https://api.example.com")).build();

        GenerationProviderException ex = assertThrows(GenerationProviderException.class, () -> transport.send(request, "boom"));

        assertTrue(ex.getMessage().contains("http 502"));
    }

    @Test
    void decodeExtractTextAndHelpersWorkForCommonPayloads() {
        TextProviderTransport transport = new TextProviderTransport(new ObjectMapper());

        Map<String, Object> payload = transport.decode("{\"output\":[{\"content\":[{\"type\":\"output_text\",\"text\":\"hello\"}]}]}");
        assertEquals("hello", transport.extractText(payload));
        assertEquals("api.example.com", transport.endpointHost("https://api.example.com/v1"));
        assertEquals("", transport.endpointHost("::::"));
        assertEquals("1", transport.stringValue(1));
        assertEquals("", transport.stringValue(null));
        assertEquals("hi", transport.extractText(Map.of(
            "choices", List.of(Map.of("message", Map.of("content", List.of(Map.of("type", "text", "text", "hi")))))
        )));
    }

    @Test
    void decodeThrowsOnInvalidJson() {
        TextProviderTransport transport = new TextProviderTransport(new ObjectMapper());

        assertThrows(GenerationProviderException.class, () -> transport.decode("{invalid"));
    }
}
