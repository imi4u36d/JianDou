package com.jiandou.api.generation.text;

import com.jiandou.api.generation.ModelRuntimeProfile;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * 为支持 Responses API 的模型构建请求体。
 */
@Component
public class ResponsesApiInvocationStrategy implements TextModelInvocationStrategy {

    @Override
    public boolean supports(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        return TextModelTransportPolicy.supportsResponsesApi(profile)
            && !(invocation.vision() && TextModelTransportPolicy.prefersChatCompletionsForVision(profile));
    }

    @Override
    public PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        Map<String, Object> body = invocation.vision()
            ? buildVisionRequest(profile.modelName(), invocation)
            : buildTextRequest(profile.modelName(), invocation);
        return new PreparedTextModelRequest(
            TextModelTransportPolicy.resolveEndpoint(profile.baseUrl(), true),
            body,
            true
        );
    }

    private Map<String, Object> buildTextRequest(String modelName, TextModelInvocation invocation) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", List.of(
            Map.of(
                "role", "system",
                "content", List.of(Map.of("type", "input_text", "text", invocation.systemPrompt()))
            ),
            Map.of(
                "role", "user",
                "content", List.of(Map.of("type", "input_text", "text", invocation.userPrompt()))
            )
        ));
        body.put("temperature", invocation.temperature());
        body.put("max_output_tokens", invocation.maxTokens());
        return body;
    }

    private Map<String, Object> buildVisionRequest(String modelName, TextModelInvocation invocation) {
        List<Map<String, Object>> userContent = new ArrayList<>();
        userContent.add(Map.of("type", "input_text", "text", invocation.userPrompt()));
        for (String imageUrl : invocation.imageUrls()) {
            userContent.add(Map.of("type", "input_image", "image_url", imageUrl));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", List.of(
            Map.of(
                "role", "system",
                "content", List.of(Map.of("type", "input_text", "text", invocation.systemPrompt()))
            ),
            Map.of(
                "role", "user",
                "content", userContent
            )
        ));
        body.put("temperature", invocation.temperature());
        body.put("max_output_tokens", invocation.maxTokens());
        if (invocation.seed() != null) {
            body.put("seed", invocation.seed());
        }
        return body;
    }
}
