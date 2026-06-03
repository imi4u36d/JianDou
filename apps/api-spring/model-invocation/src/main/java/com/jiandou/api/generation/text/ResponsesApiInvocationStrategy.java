package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
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
        return TextModelTransportPolicy.supportsResponsesApi(profile);
    }

    /**
     * 处理prepare。
     * @param profile profile值
     * @param invocation 调用值
     * @return 处理结果
     */
    @Override
    public PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        Map<String, Object> body = buildTextRequest(profile, invocation);
        return new PreparedTextModelRequest(
            TextModelTransportPolicy.resolveEndpoint(profile.baseUrl(), true),
            body,
            true
        );
    }

    /**
     * 构建文本请求。
     * @param profile profile值
     * @param invocation 调用值
     * @return 处理结果
     */
    private Map<String, Object> buildTextRequest(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", profile.modelName());
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

}
