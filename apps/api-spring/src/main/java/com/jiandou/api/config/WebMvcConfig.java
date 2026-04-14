package com.jiandou.api.config;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final String webOrigin;
    private final String storageRoot;

    public WebMvcConfig(
        @Value("${JIANDOU_WEB_ORIGIN:http://127.0.0.1:5173,http://localhost:5173}") String webOrigin,
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot
    ) {
        this.webOrigin = webOrigin;
        this.storageRoot = storageRoot;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/v2/**")
            .allowedOrigins(resolveAllowedOrigins().toArray(String[]::new))
            .allowedMethods("*")
            .allowedHeaders("*")
            .allowCredentials(true);
        registry.addMapping("/storage/**")
            .allowedOrigins(resolveAllowedOrigins().toArray(String[]::new))
            .allowedMethods("*")
            .allowedHeaders("*")
            .allowCredentials(true);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path root = Paths.get(storageRoot).toAbsolutePath().normalize();
        try {
            Files.createDirectories(root);
        } catch (Exception ignored) {
        }
        registry.addResourceHandler("/storage/**")
            .addResourceLocations(root.toUri().toString() + "/");
    }

    private List<String> resolveAllowedOrigins() {
        String[] rawValues = webOrigin.split(",");
        List<String> values = new ArrayList<>();
        for (String rawValue : rawValues) {
            String value = rawValue == null ? "" : rawValue.trim();
            if (!value.isEmpty() && !values.contains(value)) {
                values.add(value);
            }
        }
        return values;
    }
}
