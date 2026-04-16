package com.jiandou.api.generation.config;

import java.net.http.HttpClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 生成 provider 共用的 HTTP 客户端配置。
 */
@Configuration
public class GenerationHttpClientConfig {

    /**
     * 提供生成 provider 共用的 HTTP client。
     * @return HTTP client
     */
    @Bean
    public HttpClient generationProviderHttpClient() {
        return HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
    }
}
