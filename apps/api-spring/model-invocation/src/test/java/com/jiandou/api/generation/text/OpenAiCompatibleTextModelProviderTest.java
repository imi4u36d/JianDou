package com.jiandou.api.generation.text;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.TextModelResponse;
import com.jiandou.api.generation.runtime.TextProviderCapabilities;
import com.jiandou.api.generation.runtime.TextProviderConfig;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class OpenAiCompatibleTextModelProviderTest {

    @Test
    void generateTextUsesResponsesApiWhenProfileSupportsIt() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        @SuppressWarnings("unchecked")
        HttpResponse<String> response = (HttpResponse<String>) mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"id\":\"resp_1\",\"output_text\":\"OK\"}");
        ArgumentCaptor<HttpRequest> requestCaptor = ArgumentCaptor.forClass(HttpRequest.class);
        when(httpClient.send(requestCaptor.capture(), any(HttpResponse.BodyHandler.class))).thenReturn(response);
        OpenAiCompatibleTextModelProvider provider = new OpenAiCompatibleTextModelProvider(
            new TextProviderTransport(new ObjectMapper(), httpClient),
            List.of(new ResponsesApiInvocationStrategy(), new ChatCompletionsInvocationStrategy())
        );

        TextModelResponse result = provider.generate(
            responsesProfile(),
            new TextCompletionInvocation("system", "user", 0.2, 128)
        );

        HttpRequest request = requestCaptor.getValue();
        assertEquals(URI.create("https://api.example.com/v1/responses"), request.uri());
        assertEquals("POST", request.method());
        assertEquals("OK", result.text());
        assertEquals(true, result.responsesApi());
        assertEquals(200, result.httpStatus());
        assertEquals("https://api.example.com/v1/responses", result.providerRequest().get("endpoint"));
        assertEquals("resp_1", result.providerResponse().get("id"));
        assertTrue(String.valueOf(result.providerRequest().get("body")).contains("gpt-text"));
    }

    private ModelRuntimeProfile responsesProfile() {
        return new ModelRuntimeProfile(
            new TextProviderConfig(
                "text",
                "gpt-text",
                "openai",
                "gpt-text",
                "k",
                "https://api.example.com/v1",
                60,
                0.2,
                2048,
                "test"
            ),
            new TextProviderCapabilities(false, true)
        );
    }

}
