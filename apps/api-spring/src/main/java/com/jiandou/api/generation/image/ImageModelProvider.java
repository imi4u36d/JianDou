package com.jiandou.api.generation.image;

import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.RemoteImageGenerationResult;

/**
 * 图片模型 provider SPI。
 */
public interface ImageModelProvider {

    /**
     * 检查是否支持当前 profile。
     * @param profile 媒体配置值
     * @return 是否满足条件
     */
    boolean supports(MediaProviderProfile profile);

    /**
     * 生成图片。
     * @param profile 媒体配置值
     * @param request 请求值
     * @return 处理结果
     */
    RemoteImageGenerationResult generate(MediaProviderProfile profile, ImageGenerationRequest request);
}
