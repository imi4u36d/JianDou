package com.jiandou.api.generation.video;

import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 视频模型 provider 注册表。
 */
@Component
public class VideoModelProviderRegistry {

    private final List<VideoModelProvider> providers;

    public VideoModelProviderRegistry(List<VideoModelProvider> providers) {
        this.providers = providers;
    }

    /**
     * 解析可用 provider。
     * @param profile 媒体配置值
     * @return 处理结果
     */
    public VideoModelProvider resolve(MediaProviderProfile profile) {
        for (VideoModelProvider provider : providers) {
            if (provider.supports(profile)) {
                return provider;
            }
        }
        throw new GenerationProviderException("unsupported video provider: " + (profile == null ? "" : profile.provider()));
    }
}
