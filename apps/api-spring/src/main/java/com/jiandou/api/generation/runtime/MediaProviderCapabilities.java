package com.jiandou.api.generation.runtime;

import java.util.List;

/**
 * 媒体 provider 的能力与默认行为描述。
 * @param supportsSeed 是否支持 seed
 * @param promptExtend 是否启用 prompt_extend
 * @param cameraFixed 默认是否固定镜头
 * @param watermark 默认是否加水印
 * @param pollIntervalSeconds 轮询间隔Seconds值
 * @param pollTimeoutSeconds 轮询超时Seconds值
 * @param generationMode 生成模式值
 * @param supportedSizes 支持的尺寸列表
 * @param supportedDurations 支持的时长列表
 */
public record MediaProviderCapabilities(
    boolean supportsSeed,
    boolean promptExtend,
    boolean cameraFixed,
    boolean watermark,
    int pollIntervalSeconds,
    int pollTimeoutSeconds,
    String generationMode,
    List<String> supportedSizes,
    List<Integer> supportedDurations
) {

    public MediaProviderCapabilities {
        supportedSizes = supportedSizes == null ? List.of() : List.copyOf(supportedSizes);
        supportedDurations = supportedDurations == null ? List.of() : List.copyOf(supportedDurations);
        generationMode = generationMode == null ? "" : generationMode;
    }
}
