package com.jiandou.api.generation.image;

/**
 * 统一描述图片模型调用请求。
 * @param requestedModel 请求模型值
 * @param prompt 提示词值
 * @param width width值
 * @param height height值
 * @param seed 种子值
 */
public record ImageGenerationRequest(
    String requestedModel,
    String prompt,
    int width,
    int height,
    Integer seed
) {
}
