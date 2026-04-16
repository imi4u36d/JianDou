package com.jiandou.api.generation.runtime;

import java.net.URI;

/**
 * 文本模型运行时解析结果。
 * @param config provider 配置值
 * @param capabilities provider 能力值
 */
public record ModelRuntimeProfile(
    TextProviderConfig config,
    TextProviderCapabilities capabilities
) {

    /**
     * 为兼容旧调用点保留的便捷构造。
     * @param provider provider值
     * @param modelName 模型Name值
     * @param fallbackModel 兜底模型值
     * @param apiKey APIKey值
     * @param baseUrl 基础 URL
     * @param timeoutSeconds timeoutSeconds值
     * @param temperature temperature值
     * @param maxTokens 最大Tokens值
     * @param source 来源值
     */
    public ModelRuntimeProfile(
        String provider,
        String modelName,
        String fallbackModel,
        String apiKey,
        String baseUrl,
        int timeoutSeconds,
        double temperature,
        int maxTokens,
        String source
    ) {
        this(
            new TextProviderConfig("", modelName, provider, modelName, fallbackModel, apiKey, baseUrl, timeoutSeconds, temperature, maxTokens, source),
            new TextProviderCapabilities(false, false, false)
        );
    }

    /**
     * 检查是否ready。
     * @return 是否满足条件
     */
    public boolean ready() {
        return !apiKey().isBlank() && !baseUrl().isBlank();
    }

    public String kind() {
        return config == null ? "" : blankTo(config.kind());
    }

    public String provider() {
        return config == null ? "" : blankTo(config.provider());
    }

    public String modelName() {
        return config == null ? "" : blankTo(config.providerModel());
    }

    public String fallbackModel() {
        return config == null ? "" : blankTo(config.fallbackModel());
    }

    public String apiKey() {
        return config == null ? "" : blankTo(config.apiKey());
    }

    public String baseUrl() {
        return config == null ? "" : blankTo(config.baseUrl());
    }

    public int timeoutSeconds() {
        return config == null ? 0 : Math.max(0, config.timeoutSeconds());
    }

    public double temperature() {
        return config == null ? 0.0 : config.temperature();
    }

    public int maxTokens() {
        return config == null ? 0 : Math.max(0, config.maxTokens());
    }

    public String source() {
        return config == null ? "" : blankTo(config.source());
    }

    public boolean supportsSeed() {
        return capabilities != null && capabilities.supportsSeed();
    }

    public boolean supportsResponsesApi() {
        return capabilities != null && capabilities.supportsResponsesApi();
    }

    public boolean prefersChatCompletionsForVision() {
        return capabilities != null && capabilities.prefersChatCompletionsForVision();
    }

    /**
     * 处理endpointHost。
     * @return 处理结果
     */
    public String endpointHost() {
        try {
            return URI.create(baseUrl()).getHost();
        } catch (Exception ignored) {
            return "";
        }
    }

    private String blankTo(String value) {
        return value == null ? "" : value;
    }
}
