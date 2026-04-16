package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockServletContext;
import org.springframework.web.context.support.StaticWebApplicationContext;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;

class WebMvcConfigTest {

    @TempDir
    Path tempDir;

    @Test
    void addCorsMappingsUsesDistinctTrimmedOriginsForApiAndStorage() {
        JiandouAppProperties appProperties = new JiandouAppProperties();
        appProperties.setWebOrigin(" https://a.example.com , https://b.example.com, https://a.example.com ");
        WebMvcConfig config = new WebMvcConfig(appProperties, storageProperties());
        TestCorsRegistry registry = new TestCorsRegistry();

        config.addCorsMappings(registry);

        Map<String, CorsConfiguration> configs = registry.configurations();
        assertEquals(2, configs.size());
        assertEquals(
            java.util.List.of("https://a.example.com", "https://b.example.com"),
            configs.get(ApiPathConstants.API_V2_PATTERN).getAllowedOrigins()
        );
        assertEquals(
            java.util.List.of("https://a.example.com", "https://b.example.com"),
            configs.get(ApiPathConstants.STORAGE_PATTERN).getAllowedOrigins()
        );
        assertEquals(java.util.List.of("*"), configs.get(ApiPathConstants.API_V2_PATTERN).getAllowedMethods());
        assertTrue(Boolean.TRUE.equals(configs.get(ApiPathConstants.API_V2_PATTERN).getAllowCredentials()));
    }

    @Test
    void addResourceHandlersCreatesStorageRootAndRegistersStoragePattern() {
        WebMvcConfig config = new WebMvcConfig(new JiandouAppProperties(), storageProperties());
        StaticWebApplicationContext context = new StaticWebApplicationContext();
        context.setServletContext(new MockServletContext());
        ResourceHandlerRegistry registry = new ResourceHandlerRegistry(context, new MockServletContext());

        config.addResourceHandlers(registry);

        assertTrue(Files.isDirectory(tempDir));
        assertTrue(registry.hasMappingForPattern(ApiPathConstants.STORAGE_PATTERN));
    }

    private JiandouStorageProperties storageProperties() {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(tempDir.toString());
        return properties;
    }

    private static final class TestCorsRegistry extends CorsRegistry {
        Map<String, CorsConfiguration> configurations() {
            return super.getCorsConfigurations();
        }
    }
}
