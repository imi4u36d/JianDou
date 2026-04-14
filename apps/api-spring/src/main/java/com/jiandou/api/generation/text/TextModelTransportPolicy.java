package com.jiandou.api.generation.text;

import com.jiandou.api.generation.ModelRuntimeProfile;

public final class TextModelTransportPolicy {

    private TextModelTransportPolicy() {}

    public static boolean supportsResponsesApi(ModelRuntimeProfile profile) {
        String provider = normalized(profile.provider());
        String baseUrl = normalized(profile.baseUrl());
        return "openai".equals(provider)
            || "qwen".equals(provider)
            || provider.contains("ark")
            || provider.contains("volc")
            || baseUrl.contains("openai.com")
            || baseUrl.contains("dashscope.aliyuncs.com")
            || baseUrl.contains("volces.com/api/v3");
    }

    public static boolean prefersChatCompletionsForVision(ModelRuntimeProfile profile) {
        String provider = normalized(profile.provider());
        String modelName = normalized(profile.modelName());
        String baseUrl = normalized(profile.baseUrl());
        return "qwen".equals(provider)
            || modelName.contains("-vl-")
            || baseUrl.contains("dashscope.aliyuncs.com");
    }

    public static String resolveEndpoint(String baseUrl, boolean responsesApi) {
        String normalized = baseUrl == null ? "" : baseUrl.replaceAll("/+$", "");
        if (responsesApi) {
            return normalized.endsWith("/responses") ? normalized : normalized + "/responses";
        }
        return normalized.endsWith("/chat/completions") ? normalized : normalized + "/chat/completions";
    }

    private static String normalized(String value) {
        return value == null ? "" : value.trim().toLowerCase();
    }
}
