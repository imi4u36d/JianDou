package com.jiandou.api.generation.runtime;

import java.net.URI;
import java.util.List;

/**
 * 媒体 provider 解析结果。
 * @param config provider 配置值
 * @param capabilities provider 能力值
 */
public record MediaProviderProfile(
    MediaProviderConfig config,
    MediaProviderCapabilities capabilities
) {

    /**
     * 为兼容旧调用点保留的便捷构造。
     * @param provider provider值
     * @param modelName 模型Name值
     * @param apiKey APIKey值
     * @param baseUrl 基础 URL
     * @param taskBaseUrl 任务BaseURL值
     * @param timeoutSeconds timeoutSeconds值
     * @param pollIntervalSeconds pollIntervalSeconds值
     * @param pollTimeoutSeconds pollTimeoutSeconds值
     * @param promptExtend 提示词Extend值
     * @param cameraFixed cameraFixed值
     * @param watermark watermark值
     * @param source 来源值
     */
    public MediaProviderProfile(
        String provider,
        String modelName,
        String apiKey,
        String baseUrl,
        String taskBaseUrl,
        int timeoutSeconds,
        int pollIntervalSeconds,
        int pollTimeoutSeconds,
        boolean promptExtend,
        boolean cameraFixed,
        boolean watermark,
        String source
    ) {
        this(
            new MediaProviderConfig("", modelName, provider, modelName, apiKey, baseUrl, taskBaseUrl, timeoutSeconds, source),
            new MediaProviderCapabilities(false, promptExtend, cameraFixed, watermark, pollIntervalSeconds, pollTimeoutSeconds, "", List.of(), List.of())
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

    public String requestedModel() {
        return config == null ? "" : blankTo(config.requestedModel());
    }

    public String provider() {
        return config == null ? "" : blankTo(config.provider());
    }

    public String modelName() {
        return config == null ? "" : blankTo(config.providerModel());
    }

    public String apiKey() {
        return config == null ? "" : blankTo(config.apiKey());
    }

    public String baseUrl() {
        return config == null ? "" : blankTo(config.baseUrl());
    }

    public String taskBaseUrl() {
        return config == null ? "" : blankTo(config.taskBaseUrl());
    }

    public int timeoutSeconds() {
        return config == null ? 0 : Math.max(0, config.timeoutSeconds());
    }

    public String source() {
        return config == null ? "" : blankTo(config.source());
    }

    public boolean supportsSeed() {
        return capabilities != null && capabilities.supportsSeed();
    }

    public boolean promptExtend() {
        return capabilities != null && capabilities.promptExtend();
    }

    public boolean cameraFixed() {
        return capabilities != null && capabilities.cameraFixed();
    }

    public boolean watermark() {
        return capabilities != null && capabilities.watermark();
    }

    public int pollIntervalSeconds() {
        return capabilities == null ? 0 : Math.max(0, capabilities.pollIntervalSeconds());
    }

    public int pollTimeoutSeconds() {
        return capabilities == null ? 0 : Math.max(0, capabilities.pollTimeoutSeconds());
    }

    public String generationMode() {
        return capabilities == null ? "" : blankTo(capabilities.generationMode());
    }

    public List<String> supportedSizes() {
        return capabilities == null ? List.of() : capabilities.supportedSizes();
    }

    public List<Integer> supportedDurations() {
        return capabilities == null ? List.of() : capabilities.supportedDurations();
    }

    /**
     * 处理endpointHost。
     * @return 处理结果
     */
    public String endpointHost() {
        return hostOf(baseUrl());
    }

    /**
     * 处理任务EndpointHost。
     * @return 处理结果
     */
    public String taskEndpointHost() {
        return hostOf(taskBaseUrl());
    }

    /**
     * 处理host。
     * @param raw 原始值
     * @return 处理结果
     */
    private String hostOf(String raw) {
        try {
            return URI.create(raw).getHost();
        } catch (Exception ignored) {
            return "";
        }
    }

    private String blankTo(String value) {
        return value == null ? "" : value;
    }
}
