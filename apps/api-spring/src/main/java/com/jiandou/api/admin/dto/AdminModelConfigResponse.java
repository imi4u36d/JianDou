package com.jiandou.api.admin.dto;

import java.util.List;
import java.util.Map;

/**
 * 管理端模型配置快照响应体。
 * @param configSource 配置来源值
 * @param summary 汇总值
 * @param defaults 默认值
 * @param providers provider 列表值
 * @param models 模型列表值
 * @param configErrors 配置错误值
 * @return 处理结果
 */
public record AdminModelConfigResponse(
    String configSource,
    Summary summary,
    Defaults defaults,
    List<ProviderItem> providers,
    List<ModelItem> models,
    List<String> configErrors
) {

    /**
     * 汇总信息。
     * @param providerCount provider 数量值
     * @param vendorCount vendor 数量值
     * @param modelCount 模型数量值
     * @param readyModelCount 就绪模型数量值
     * @param readyTextModelCount 就绪文本模型数量值
     * @param readyVisionModelCount 就绪视觉模型数量值
     * @param readyImageModelCount 就绪图片模型数量值
     * @param readyVideoModelCount 就绪视频模型数量值
     */
    public record Summary(
        int providerCount,
        int vendorCount,
        int modelCount,
        int readyModelCount,
        int readyTextModelCount,
        int readyVisionModelCount,
        int readyImageModelCount,
        int readyVideoModelCount
    ) {
    }

    /**
     * 默认参数信息。
     * @param aspectRatio 默认画幅值
     * @param stylePreset 默认风格值
     * @param imageSize 默认图片尺寸值
     * @param videoSize 默认视频尺寸值
     * @param videoDurationSeconds 默认视频时长值
     * @param timeoutSeconds 默认超时值
     * @param temperature 默认温度值
     * @param maxTokens 默认最大 tokens 值
     */
    public record Defaults(
        String aspectRatio,
        String stylePreset,
        String imageSize,
        String videoSize,
        int videoDurationSeconds,
        int timeoutSeconds,
        double temperature,
        int maxTokens
    ) {
    }

    /**
     * provider 配置项。
     * @param key provider 键值
     * @param provider provider 名称值
     * @param vendor vendor 名称值
     * @param kinds 关联类型值
     * @param baseUrl 基础地址值
     * @param taskBaseUrl 任务基础地址值
     * @param endpointHost endpoint host 值
     * @param taskEndpointHost 任务 endpoint host 值
     * @param apiKeyConfigured 是否已配置 key
     * @param baseUrlConfigured 是否已配置 baseUrl
     * @param taskBaseUrlConfigured 是否已配置 taskBaseUrl
     * @param extras 扩展配置值
     * @param modelNames 关联模型名列表值
     */
    public record ProviderItem(
        String key,
        String provider,
        String vendor,
        List<String> kinds,
        String baseUrl,
        String taskBaseUrl,
        String endpointHost,
        String taskEndpointHost,
        boolean apiKeyConfigured,
        boolean baseUrlConfigured,
        boolean taskBaseUrlConfigured,
        Map<String, String> extras,
        List<String> modelNames
    ) {
    }

    /**
     * 模型配置项。
     * @param name 模型名值
     * @param label 标签值
     * @param kind 类型值
     * @param provider provider 值
     * @param vendor vendor 值
     * @param family family 值
     * @param description 描述值
     * @param fallbackModel 兜底模型值
     * @param supportsSeed 是否支持 seed
     * @param supportsResponsesApi 是否支持 responses api
     * @param prefersChatCompletionsForVision 是否视觉偏好 chat completions
     * @param generationMode 生成模式值
     * @param supportedSizes 支持尺寸值
     * @param supportedDurations 支持时长值
     * @param ready 是否就绪
     * @param configSource 配置来源值
     * @param endpointHost endpoint host 值
     * @param taskEndpointHost 任务 endpoint host 值
     * @param issues 问题列表值
     */
    public record ModelItem(
        String name,
        String label,
        String kind,
        String provider,
        String vendor,
        String family,
        String description,
        String fallbackModel,
        boolean supportsSeed,
        boolean supportsResponsesApi,
        boolean prefersChatCompletionsForVision,
        String generationMode,
        List<String> supportedSizes,
        List<Integer> supportedDurations,
        boolean ready,
        String configSource,
        String endpointHost,
        String taskEndpointHost,
        List<String> issues
    ) {
    }
}
