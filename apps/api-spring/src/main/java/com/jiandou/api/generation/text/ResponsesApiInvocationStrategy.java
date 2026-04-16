package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 为支持 Responses API 的模型构建请求体。
 */
@Component
@Order(0)
public class ResponsesApiInvocationStrategy implements TextModelInvocationStrategy {

    /**
     * 检查是否supports。
     * @param profile profile值
     * @param invocation 调用值
     * @return 是否满足条件
     */
    @Override
    public boolean supports(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        return TextModelTransportPolicy.supportsResponsesApi(profile)
            /**
             * 处理视觉。
             * @param TextModelTransportPolicy.prefersChatCompletionsForVision(profile 文本模型传输Policy.prefersChatCompletionsForVision(profile值
             * @return 处理结果
             */
            && !(invocation.vision() && TextModelTransportPolicy.prefersChatCompletionsForVision(profile));
    }

    /**
     * 处理prepare。
     * @param profile profile值
     * @param invocation 调用值
     * @return 处理结果
     */
    @Override
    public PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        Map<String, Object> body = invocation.vision()
            /**
             * 构建视觉请求。
             * @param profile.modelName( profile.modelName(值
             * @param invocation 调用值
             * @return 处理结果
             */
            ? buildVisionRequest(profile.modelName(), invocation)
            /**
             * 构建文本请求。
             * @param profile.modelName( profile.modelName(值
             * @param invocation 调用值
             * @return 处理结果
             */
            : buildTextRequest(profile.modelName(), invocation);
        return new PreparedTextModelRequest(
            TextModelTransportPolicy.resolveEndpoint(profile.baseUrl(), true),
            body,
            true
        );
    }

    /**
     * 构建文本请求。
     * @param modelName 模型Name值
     * @param invocation 调用值
     * @return 处理结果
     */
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

    /**
     * 构建视觉请求。
     * @param modelName 模型Name值
     * @param invocation 调用值
     * @return 处理结果
     */
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
