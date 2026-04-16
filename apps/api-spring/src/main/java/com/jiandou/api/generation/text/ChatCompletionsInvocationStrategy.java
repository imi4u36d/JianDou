package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * Chat Completions 兜底策略。
 * 当模型或网关不支持 Responses API 时，统一回退到该协议。
 */
@Component
@Order(Ordered.LOWEST_PRECEDENCE)
public class ChatCompletionsInvocationStrategy implements TextModelInvocationStrategy {

    /**
     * 检查是否supports。
     * @param profile profile值
     * @param invocation 调用值
     * @return 是否满足条件
     */
    @Override
    public boolean supports(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        return true;
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
            TextModelTransportPolicy.resolveEndpoint(profile.baseUrl(), false),
            body,
            false
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
        body.put("messages", List.of(
            Map.of("role", "system", "content", invocation.systemPrompt()),
            Map.of("role", "user", "content", invocation.userPrompt())
        ));
        body.put("temperature", invocation.temperature());
        body.put("max_tokens", invocation.maxTokens());
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
        userContent.add(Map.of("type", "text", "text", invocation.userPrompt()));
        for (String imageUrl : invocation.imageUrls()) {
            userContent.add(Map.of("type", "image_url", "image_url", Map.of("url", imageUrl)));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("messages", List.of(
            Map.of("role", "system", "content", invocation.systemPrompt()),
            Map.of("role", "user", "content", userContent)
        ));
        body.put("temperature", invocation.temperature());
        body.put("max_tokens", invocation.maxTokens());
        if (invocation.seed() != null) {
            body.put("seed", invocation.seed());
        }
        return body;
    }
}
