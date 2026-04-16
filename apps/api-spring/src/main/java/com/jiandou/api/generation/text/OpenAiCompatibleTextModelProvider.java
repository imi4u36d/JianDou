package com.jiandou.api.generation.text;

import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.TextModelResponse;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * OpenAI 风格兼容协议的文本 provider。
 */
@Component
@Order(Ordered.LOWEST_PRECEDENCE)
public class OpenAiCompatibleTextModelProvider implements TextModelProvider {

    private final TextProviderTransport transport;
    private final List<TextModelInvocationStrategy> invocationStrategies;

    public OpenAiCompatibleTextModelProvider(TextProviderTransport transport, List<TextModelInvocationStrategy> invocationStrategies) {
        this.transport = transport;
        this.invocationStrategies = List.copyOf(invocationStrategies);
    }

    @Override
    public boolean supports(ModelRuntimeProfile profile) {
        return profile != null && !profile.provider().isBlank();
    }

    @Override
    public TextModelResponse generate(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        if (!profile.ready()) {
            throw new GenerationConfigurationException((invocation.vision() ? "vision" : "text") + " model config missing api key or base url");
        }
        if (invocation.vision() && (invocation.imageUrls() == null || invocation.imageUrls().isEmpty())) {
            throw new GenerationProviderException("vision model request requires at least one image url");
        }
        PreparedTextModelRequest prepared = prepare(profile, invocation);
        long startedAt = System.nanoTime();
        HttpResponse<String> response = transport.sendJson(
            prepared.endpoint(),
            profile.apiKey(),
            prepared.body(),
            profile.timeoutSeconds(),
            (invocation.vision() ? "vision" : "text") + " model request failed"
        );
        int latencyMs = (int) ((System.nanoTime() - startedAt) / 1_000_000L);
        Map<String, Object> responseMap = transport.decode(response.body());
        String text = transport.extractText(responseMap).trim();
        if (text.isBlank()) {
            throw new GenerationProviderException((invocation.vision() ? "vision" : "text") + " model response is empty");
        }
        return new TextModelResponse(
            text,
            prepared.endpoint(),
            transport.endpointHost(prepared.endpoint()),
            latencyMs,
            prepared.responsesApi(),
            transport.stringValue(responseMap.get("id"))
        );
    }

    private PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        List<String> triedStrategies = new ArrayList<>();
        for (TextModelInvocationStrategy strategy : invocationStrategies) {
            triedStrategies.add(strategy.getClass().getSimpleName());
            if (strategy.supports(profile, invocation)) {
                return strategy.prepare(profile, invocation);
            }
        }
        throw new GenerationProviderException("no text model invocation strategy matched: " + String.join(", ", triedStrategies));
    }
}
