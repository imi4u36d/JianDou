package com.jiandou.api.generation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class CompatibleTextModelClient {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public CompatibleTextModelClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().build();
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
        boolean useResponsesApi = useResponsesApi(profile);
        String endpoint = resolveEndpoint(profile.baseUrl(), useResponsesApi);
        Map<String, Object> body = useResponsesApi
            ? buildResponsesRequest(profile.modelName(), systemPrompt, userPrompt, temperature, maxTokens)
            : buildChatRequest(profile.modelName(), systemPrompt, userPrompt, temperature, maxTokens);
        String payload = encode(body);
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint))
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
                throw new GenerationProviderException("text model request interrupted");
            }
            throw new GenerationProviderException("text model request failed: " + ex.getMessage());
        }
        int latencyMs = (int) ((System.nanoTime() - startedAt) / 1_000_000L);
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new GenerationProviderException(
                "text model request failed: http " + response.statusCode() + " " + truncate(response.body(), 320)
            );
        }
        Map<String, Object> responseMap = decode(response.body());
        String text = extractText(responseMap).trim();
        if (text.isBlank()) {
            throw new GenerationProviderException("text model response is empty");
        }
        String endpointHost = "";
        try {
            endpointHost = URI.create(endpoint).getHost();
        } catch (Exception ignored) {
            endpointHost = "";
        }
        return new TextModelResponse(
            text,
            endpoint,
            endpointHost == null ? "" : endpointHost,
            latencyMs,
            useResponsesApi,
            stringValue(responseMap.get("id"))
        );
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
        boolean useResponsesApi = useResponsesApi(profile) && !useChatCompletionsForVision(profile);
        String endpoint = resolveEndpoint(profile.baseUrl(), useResponsesApi);
        Map<String, Object> body = useResponsesApi
            ? buildVisionResponsesRequest(profile.modelName(), systemPrompt, userPrompt, normalizedImageUrls, temperature, maxTokens, seed)
            : buildVisionChatRequest(profile.modelName(), systemPrompt, userPrompt, normalizedImageUrls, temperature, maxTokens, seed);
        String payload = encode(body);
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint))
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
                throw new GenerationProviderException("vision model request interrupted");
            }
            throw new GenerationProviderException("vision model request failed: " + ex.getMessage());
        }
        int latencyMs = (int) ((System.nanoTime() - startedAt) / 1_000_000L);
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new GenerationProviderException(
                "vision model request failed: http " + response.statusCode() + " " + truncate(response.body(), 320)
            );
        }
        Map<String, Object> responseMap = decode(response.body());
        String text = extractText(responseMap).trim();
        if (text.isBlank()) {
            throw new GenerationProviderException("vision model response is empty");
        }
        String endpointHost = "";
        try {
            endpointHost = URI.create(endpoint).getHost();
        } catch (Exception ignored) {
            endpointHost = "";
        }
        return new TextModelResponse(
            text,
            endpoint,
            endpointHost == null ? "" : endpointHost,
            latencyMs,
            useResponsesApi,
            stringValue(responseMap.get("id"))
        );
    }

    private boolean useResponsesApi(ModelRuntimeProfile profile) {
        String provider = profile.provider() == null ? "" : profile.provider().trim().toLowerCase();
        String baseUrl = profile.baseUrl() == null ? "" : profile.baseUrl().trim().toLowerCase();
        return "openai".equals(provider)
            || "qwen".equals(provider)
            || provider.contains("ark")
            || provider.contains("volc")
            || baseUrl.contains("openai.com")
            || baseUrl.contains("dashscope.aliyuncs.com")
            || baseUrl.contains("volces.com/api/v3");
    }

    private boolean useChatCompletionsForVision(ModelRuntimeProfile profile) {
        String provider = profile.provider() == null ? "" : profile.provider().trim().toLowerCase();
        String modelName = profile.modelName() == null ? "" : profile.modelName().trim().toLowerCase();
        String baseUrl = profile.baseUrl() == null ? "" : profile.baseUrl().trim().toLowerCase();
        return "qwen".equals(provider)
            || modelName.contains("-vl-")
            || baseUrl.contains("dashscope.aliyuncs.com");
    }

    private String resolveEndpoint(String baseUrl, boolean useResponsesApi) {
        String normalized = baseUrl.replaceAll("/+$", "");
        if (useResponsesApi) {
            return normalized.endsWith("/responses") ? normalized : normalized + "/responses";
        }
        return normalized.endsWith("/chat/completions") ? normalized : normalized + "/chat/completions";
    }

    private Map<String, Object> buildResponsesRequest(
        String modelName,
        String systemPrompt,
        String userPrompt,
        double temperature,
        int maxTokens
    ) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", List.of(
            Map.of(
                "role", "system",
                "content", List.of(Map.of("type", "input_text", "text", systemPrompt))
            ),
            Map.of(
                "role", "user",
                "content", List.of(Map.of("type", "input_text", "text", userPrompt))
            )
        ));
        body.put("temperature", temperature);
        body.put("max_output_tokens", maxTokens);
        return body;
    }

    private Map<String, Object> buildVisionResponsesRequest(
        String modelName,
        String systemPrompt,
        String userPrompt,
        List<String> imageUrls,
        double temperature,
        int maxTokens,
        Integer seed
    ) {
        List<Map<String, Object>> userContent = new java.util.ArrayList<>();
        userContent.add(Map.of("type", "input_text", "text", userPrompt));
        for (String imageUrl : imageUrls) {
            userContent.add(Map.of("type", "input_image", "image_url", imageUrl));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("input", List.of(
            Map.of(
                "role", "system",
                "content", List.of(Map.of("type", "input_text", "text", systemPrompt))
            ),
            Map.of(
                "role", "user",
                "content", userContent
            )
        ));
        body.put("temperature", temperature);
        body.put("max_output_tokens", maxTokens);
        if (seed != null) {
            body.put("seed", seed);
        }
        return body;
    }

    private Map<String, Object> buildChatRequest(
        String modelName,
        String systemPrompt,
        String userPrompt,
        double temperature,
        int maxTokens
    ) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("messages", List.of(
            Map.of("role", "system", "content", systemPrompt),
            Map.of("role", "user", "content", userPrompt)
        ));
        body.put("temperature", temperature);
        body.put("max_tokens", maxTokens);
        return body;
    }

    private Map<String, Object> buildVisionChatRequest(
        String modelName,
        String systemPrompt,
        String userPrompt,
        List<String> imageUrls,
        double temperature,
        int maxTokens,
        Integer seed
    ) {
        List<Map<String, Object>> userContent = new java.util.ArrayList<>();
        userContent.add(Map.of("type", "text", "text", userPrompt));
        for (String imageUrl : imageUrls) {
            userContent.add(Map.of("type", "image_url", "image_url", Map.of("url", imageUrl)));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", modelName);
        body.put("messages", List.of(
            Map.of("role", "system", "content", systemPrompt),
            Map.of("role", "user", "content", userContent)
        ));
        body.put("temperature", temperature);
        body.put("max_tokens", maxTokens);
        if (seed != null) {
            body.put("seed", seed);
        }
        return body;
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
