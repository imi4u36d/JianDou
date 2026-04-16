package com.jiandou.api.generation.runtime;

/**
 * 文本 provider 的连接与运行配置。
 * @param kind 模型类型值
 * @param requestedModel 请求模型值
 * @param provider provider值
 * @param providerModel provider 模型值
 * @param fallbackModel 兜底模型值
 * @param apiKey APIKey值
 * @param baseUrl 基础 URL
 * @param timeoutSeconds timeoutSeconds值
 * @param temperature temperature值
 * @param maxTokens 最大Tokens值
 * @param source 来源值
 */
public record TextProviderConfig(
    String kind,
    String requestedModel,
    String provider,
    String providerModel,
    String fallbackModel,
    String apiKey,
    String baseUrl,
    int timeoutSeconds,
    double temperature,
    int maxTokens,
    String source
) {
}
