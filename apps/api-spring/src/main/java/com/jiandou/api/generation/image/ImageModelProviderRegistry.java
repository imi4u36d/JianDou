package com.jiandou.api.generation.image;

import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 图片模型 provider 注册表。
 */
@Component
public class ImageModelProviderRegistry {

    private final List<ImageModelProvider> providers;

    public ImageModelProviderRegistry(List<ImageModelProvider> providers) {
        this.providers = providers;
    }

    /**
     * 解析可用 provider。
     * @param profile 媒体配置值
     * @return 处理结果
     */
    public ImageModelProvider resolve(MediaProviderProfile profile) {
        for (ImageModelProvider provider : providers) {
            if (provider.supports(profile)) {
                return provider;
            }
        }
        throw new GenerationProviderException("unsupported image provider: " + (profile == null ? "" : profile.provider()));
    }
}
