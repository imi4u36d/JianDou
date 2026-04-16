package com.jiandou.api.config;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * WebMvc配置。
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final JiandouAppProperties appProperties;
    private final JiandouStorageProperties storageProperties;

    /**
     * 创建新的WebMvc配置。
     */
    public WebMvcConfig(JiandouAppProperties appProperties, JiandouStorageProperties storageProperties) {
        this.appProperties = appProperties;
        this.storageProperties = storageProperties;
    }

    /**
     * 处理addCorsMappings。
     * @param registry registry值
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping(ApiPathConstants.API_V2_PATTERN)
            .allowedOrigins(resolveAllowedOrigins().toArray(String[]::new))
            .allowedMethods("*")
            .allowedHeaders("*")
            .allowCredentials(true);
        registry.addMapping(ApiPathConstants.STORAGE_PATTERN)
            .allowedOrigins(resolveAllowedOrigins().toArray(String[]::new))
            .allowedMethods("*")
            .allowedHeaders("*")
            .allowCredentials(true);
    }

    /**
     * 处理addResourceHandlers。
     * @param registry registry值
     */
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path root = storageProperties.resolveRootDir();
        try {
            Files.createDirectories(root);
        } catch (Exception ignored) {
        }
        registry.addResourceHandler(ApiPathConstants.STORAGE_PATTERN)
            .addResourceLocations(root.toUri().toString() + "/");
    }

    /**
     * 处理解析AllowedOrigins。
     * @return 处理结果
     */
    private List<String> resolveAllowedOrigins() {
        String[] rawValues = appProperties.getWebOrigin().split(",");
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
