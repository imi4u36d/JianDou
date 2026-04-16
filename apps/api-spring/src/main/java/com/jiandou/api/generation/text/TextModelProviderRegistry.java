package com.jiandou.api.generation.text;

import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 文本模型 provider 注册表。
 */
@Component
public class TextModelProviderRegistry {

    private final List<TextModelProvider> providers;

    public TextModelProviderRegistry(List<TextModelProvider> providers) {
        this.providers = providers;
    }

    /**
     * 解析可用 provider。
     * @param profile 运行时配置值
     * @return 处理结果
     */
    public TextModelProvider resolve(ModelRuntimeProfile profile) {
        for (TextModelProvider provider : providers) {
            if (provider.supports(profile)) {
                return provider;
            }
        }
        throw new GenerationProviderException("unsupported text provider: " + (profile == null ? "" : profile.provider()));
    }
}
