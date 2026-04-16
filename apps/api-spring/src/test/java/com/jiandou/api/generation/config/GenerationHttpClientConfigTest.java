package com.jiandou.api.generation.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.net.http.HttpClient;
import org.junit.jupiter.api.Test;

class GenerationHttpClientConfigTest {

    @Test
    void generationProviderHttpClientUsesNormalRedirects() {
        HttpClient client = new GenerationHttpClientConfig().generationProviderHttpClient();

        assertNotNull(client);
        assertEquals(HttpClient.Redirect.NORMAL, client.followRedirects());
    }
}
