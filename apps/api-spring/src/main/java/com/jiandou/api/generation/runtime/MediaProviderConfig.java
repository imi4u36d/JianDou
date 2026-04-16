package com.jiandou.api.generation.runtime;

/**
 * 媒体 provider 的连接与鉴权配置。
 * @param kind 媒体类型值
 * @param requestedModel 请求模型值
 * @param provider provider值
 * @param providerModel provider 模型值
 * @param apiKey APIKey值
 * @param baseUrl 基础 URL
 * @param taskBaseUrl 任务 Base URL
 * @param timeoutSeconds timeoutSeconds值
 * @param source 来源值
 */
public record MediaProviderConfig(
    String kind,
    String requestedModel,
    String provider,
    String providerModel,
    String apiKey,
    String baseUrl,
    String taskBaseUrl,
    int timeoutSeconds,
    String source
) {
}
