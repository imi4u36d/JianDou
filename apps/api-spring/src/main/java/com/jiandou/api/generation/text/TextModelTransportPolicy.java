package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;

/**
 * 文本模型传输Policy。
 */
public final class TextModelTransportPolicy {

    /**
     * 创建新的文本模型传输Policy。
     */
    private TextModelTransportPolicy() {}

    /**
     * 检查是否supportsResponsesAPI。
     * @param profile profile值
     * @return 是否满足条件
     */
    public static boolean supportsResponsesApi(ModelRuntimeProfile profile) {
        return profile != null && profile.supportsResponsesApi();
    }

    /**
     * 检查是否prefersChatCompletionsFor视觉。
     * @param profile profile值
     * @return 是否满足条件
     */
    public static boolean prefersChatCompletionsForVision(ModelRuntimeProfile profile) {
        return profile != null && profile.prefersChatCompletionsForVision();
    }

    /**
     * 处理解析Endpoint。
     * @param baseUrl 基础 URL
     * @param responsesApi responsesAPI值
     * @return 处理结果
     */
    public static String resolveEndpoint(String baseUrl, boolean responsesApi) {
        String normalized = baseUrl == null ? "" : baseUrl.replaceAll("/+$", "");
        if (responsesApi) {
            return normalized.endsWith("/responses") ? normalized : normalized + "/responses";
        }
        return normalized.endsWith("/chat/completions") ? normalized : normalized + "/chat/completions";
    }

}
