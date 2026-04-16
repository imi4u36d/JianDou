package com.jiandou.api.generation.image;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.exception.GenerationProviderException;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ImageProviderTransportTest {

    @Test
    void sendJsonAndDownloadBinaryUseHttpClient() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> jsonResponse = mock(HttpResponse.class);
        @SuppressWarnings("unchecked")
        HttpResponse<byte[]> binaryResponse = mock(HttpResponse.class);
        when(jsonResponse.statusCode()).thenReturn(200);
        when(jsonResponse.body()).thenReturn("{\"url\":\"https://img\"}");
        when(binaryResponse.statusCode()).thenReturn(200);
        when(binaryResponse.body()).thenReturn(new byte[] {1, 2});
        when(binaryResponse.headers()).thenReturn(HttpHeaders.of(Map.of("content-type", List.of("image/png")), (a, b) -> true));
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn((HttpResponse) jsonResponse)
            .thenReturn((HttpResponse) binaryResponse);
        ImageProviderTransport transport = new ImageProviderTransport(new ObjectMapper(), httpClient);

        assertEquals(jsonResponse, transport.sendJson("https://api.example.com/image", "k", Map.of("prompt", "x"), 5, Map.of("X-Test", "1")));
        ImageProviderTransport.DownloadedBinary binary = transport.downloadBinary("https://cdn.example.com/a.png", 5);
        assertArrayEquals(new byte[] {1, 2}, binary.data());
        assertEquals("image/png", binary.mimeType());
    }

    @Test
    void sendAndDecodeAndExtractFirstStringHandleErrorsAndNestedStructures() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(500);
        when(response.body()).thenReturn("server error");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        ImageProviderTransport transport = new ImageProviderTransport(new ObjectMapper(), httpClient);

        GenerationProviderException ex = assertThrows(
            GenerationProviderException.class,
            () -> transport.send(HttpRequest.newBuilder().uri(java.net.URI.create("https://api.example.com")).build(), "img failed")
        );
        assertTrue(ex.getMessage().contains("http 500"));

        Map<String, Object> decoded = new ImageProviderTransport(new ObjectMapper()).decode("{\"data\":{\"fileUrl\":\"https://img\"}}");
        assertEquals("https://img", new ImageProviderTransport(new ObjectMapper()).extractFirstString(decoded, "fileUrl", "url"));
        assertEquals("", new ImageProviderTransport(new ObjectMapper()).extractFirstString(List.of(Map.of("none", "x")), "url"));
    }

    @Test
    void downloadBinaryRejectsHttpErrors() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<byte[]> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(404);
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn((HttpResponse) response);
        ImageProviderTransport transport = new ImageProviderTransport(new ObjectMapper(), httpClient);

        assertThrows(GenerationProviderException.class, () -> transport.downloadBinary("https://cdn.example.com/missing.png", 5));
    }
}
