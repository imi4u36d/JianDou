package com.jiandou.api.generation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.text.PreparedTextModelRequest;
import com.jiandou.api.generation.text.TextCompletionInvocation;
import com.jiandou.api.generation.text.TextModelInvocation;
import com.jiandou.api.generation.text.TextModelInvocationStrategy;
import com.jiandou.api.generation.text.VisionCompletionInvocation;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/**
 * 兼容多种 OpenAI 风格文本接口。
 * 具体如何组装请求体由策略实现负责，当前类只负责执行与结果提取。
 */
@Service
public class CompatibleTextModelClient {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;
    private final List<TextModelInvocationStrategy> invocationStrategies;

    public CompatibleTextModelClient(ObjectMapper objectMapper, List<TextModelInvocationStrategy> invocationStrategies) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().build();
        this.invocationStrategies = List.copyOf(invocationStrategies);
    }

    public TextModelResponse generateText(
        ModelRuntimeProfile profile,
        String systemPrompt,
        String userPrompt,
        double temperature,
        int maxTokens
    ) {
        if (!profile.ready()) {
            throw new GenerationConfigurationException("text model config missing api key or base url");
        }
        return execute(profile, new TextCompletionInvocation(systemPrompt, userPrompt, temperature, maxTokens));
    }

    public TextModelResponse generateVisionText(
        ModelRuntimeProfile profile,
        String systemPrompt,
        String userPrompt,
        List<String> imageUrls,
        double temperature,
        int maxTokens,
        Integer seed
    ) {
        if (!profile.ready()) {
            throw new GenerationConfigurationException("vision model config missing api key or base url");
        }
        List<String> normalizedImageUrls = imageUrls == null ? List.of() : imageUrls.stream()
            .filter(item -> item != null && !item.isBlank())
            .map(String::trim)
            .toList();
        if (normalizedImageUrls.isEmpty()) {
            throw new GenerationProviderException("vision model request requires at least one image url");
        }
        return execute(
            profile,
            new VisionCompletionInvocation(systemPrompt, userPrompt, temperature, maxTokens, normalizedImageUrls, seed)
        );
    }

    private TextModelResponse execute(ModelRuntimeProfile profile, TextModelInvocation invocation) {
        PreparedTextModelRequest prepared = prepare(profile, invocation);
        String payload = encode(prepared.body());
        HttpRequest request = HttpRequest.newBuilder(URI.create(prepared.endpoint()))
            .header("Authorization", "Bearer " + profile.apiKey())
            .header("Content-Type", "application/json")
            .timeout(Duration.ofSeconds(Math.max(30, profile.timeoutSeconds())))
            .POST(HttpRequest.BodyPublishers.ofString(payload))
            .build();
        long startedAt = System.nanoTime();
        HttpResponse<String> response;
        try {
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException | InterruptedException ex) {
            if (ex instanceof InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new GenerationProviderException(
                    invocation.vision() ? "vision model request interrupted" : "text model request interrupted"
                );
            }
            throw new GenerationProviderException(
                (invocation.vision() ? "vision" : "text") + " model request failed: " + ex.getMessage()
            );
        }
        int latencyMs = (int) ((System.nanoTime() - startedAt) / 1_000_000L);
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new GenerationProviderException(
                (invocation.vision() ? "vision" : "text")
                    + " model request failed: http "
                    + response.statusCode()
                    + " "
                    + truncate(response.body(), 320)
            );
        }
        Map<String, Object> responseMap = decode(response.body());
        String text = extractText(responseMap).trim();
        if (text.isBlank()) {
            throw new GenerationProviderException((invocation.vision() ? "vision" : "text") + " model response is empty");
        }
        String endpointHost = "";
        try {
            endpointHost = URI.create(prepared.endpoint()).getHost();
        } catch (Exception ignored) {
            endpointHost = "";
        }
        return new TextModelResponse(
            text,
            prepared.endpoint(),
            endpointHost == null ? "" : endpointHost,
            latencyMs,
            prepared.responsesApi(),
            stringValue(responseMap.get("id"))
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

    private String encode(Map<String, Object> body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (IOException ex) {
            throw new GenerationProviderException("text model request encode failed: " + ex.getMessage());
        }
    }

    private Map<String, Object> decode(String raw) {
        try {
            return objectMapper.readValue(raw, MAP_TYPE);
        } catch (IOException ex) {
            throw new GenerationProviderException("text model response decode failed: " + ex.getMessage());
        }
    }

    private String extractText(Map<String, Object> responseMap) {
        String outputText = stringValue(responseMap.get("output_text"));
        if (!outputText.isBlank()) {
            return outputText;
        }
        String fromOutput = extractFromOutput(responseMap.get("output"));
        if (!fromOutput.isBlank()) {
            return fromOutput;
        }
        String fromChoices = extractFromChoices(responseMap.get("choices"));
        if (!fromChoices.isBlank()) {
            return fromChoices;
        }
        return stringValue(responseMap.get("text"));
    }

    private String extractFromOutput(Object raw) {
        if (!(raw instanceof List<?> items)) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            appendContent(builder, map.get("content"));
        }
        return builder.toString().trim();
    }

    private String extractFromChoices(Object raw) {
        if (!(raw instanceof List<?> choices) || choices.isEmpty()) {
            return "";
        }
        Object first = choices.get(0);
        if (!(first instanceof Map<?, ?> map)) {
            return "";
        }
        Object message = map.get("message");
        if (message instanceof Map<?, ?> messageMap) {
            Object content = messageMap.get("content");
            if (content instanceof String str) {
                return str.trim();
            }
            StringBuilder builder = new StringBuilder();
            appendContent(builder, content);
            return builder.toString().trim();
        }
        return "";
    }

    private void appendContent(StringBuilder builder, Object raw) {
        if (raw instanceof String str) {
            appendText(builder, str);
            return;
        }
        if (raw instanceof List<?> items) {
            for (Object item : items) {
                appendContent(builder, item);
            }
            return;
        }
        if (!(raw instanceof Map<?, ?> map)) {
            return;
        }
        String text = stringValue(map.get("text"));
        if (!text.isBlank()) {
            appendText(builder, text);
            return;
        }
        Object nestedContent = map.get("content");
        if (nestedContent != null) {
            appendContent(builder, nestedContent);
        }
    }

    private void appendText(StringBuilder builder, String text) {
        if (text == null || text.isBlank()) {
            return;
        }
        if (builder.length() > 0) {
            builder.append('\n');
        }
        builder.append(text.trim());
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String truncate(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() <= limit ? value : value.substring(0, limit);
    }
}
