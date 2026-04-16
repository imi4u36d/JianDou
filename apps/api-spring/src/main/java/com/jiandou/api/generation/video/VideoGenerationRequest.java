package com.jiandou.api.generation.video;

/**
 * 统一描述视频模型调用请求，避免编排层直接依赖具体 provider 的参数布局。
 * @param requestedModel 请求模型值
 * @param prompt 提示词值
 * @param width width值
 * @param height height值
 * @param durationSeconds 时长Seconds值
 * @param firstFrameUrl 首帧URL值
 * @param lastFrameUrl 末帧URL值
 * @param seed 种子值
 * @param cameraFixed cameraFixed值
 * @param watermark watermark值
 * @param returnLastFrame returnLastFrame值
 * @param generateAudio generateAudio值
 */
public record VideoGenerationRequest(
    String requestedModel,
    String prompt,
    int width,
    int height,
    int durationSeconds,
    String firstFrameUrl,
    String lastFrameUrl,
    Integer seed,
    boolean cameraFixed,
    boolean watermark,
    boolean returnLastFrame,
    boolean generateAudio
) {
}
