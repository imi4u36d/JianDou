package com.jiandou.api.admin.dto;

import java.util.List;

/**
 * 管理端模型密钥更新请求体。
 * @param providers 模型接入密钥输入列表值
 * @return 处理结果
 */
public record AdminModelConfigKeyUpdateRequest(
    List<ProviderKeyInput> providers
) {

    /**
     * 模型接入密钥输入。
     * @param key 模型接入标识值
     * @param apiKey 新输入的 API Key 值
     * @return 处理结果
     */
    public record ProviderKeyInput(
        String key,
        String apiKey
    ) {
    }
}
