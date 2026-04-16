package com.jiandou.api.generation.orchestration;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.GenerationRunStatuses;
import com.jiandou.api.generation.TextModelResponse;
import com.jiandou.api.generation.exception.GenerationNotImplementedException;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.media.LocalMediaArtifactService.ImageArtifact;
import com.jiandou.api.media.LocalMediaArtifactService.StoredArtifact;
import com.jiandou.api.media.LocalMediaArtifactService.TextArtifact;
import com.jiandou.api.generation.text.TextCompletionInvocation;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * 生成运行支持。
 */
@Component
public class GenerationRunSupport {

    private final LocalMediaArtifactService localMediaArtifactService;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final TextModelProviderRegistry textModelProviderRegistry;

    /**
     * 创建新的生成运行支持。
     * @param localMediaArtifactService 本地媒体产物服务值
     * @param modelResolver 模型解析器值
     * @param textModelClient 文本模型客户端值
     */
    public GenerationRunSupport(
        LocalMediaArtifactService localMediaArtifactService,
        ModelRuntimePropertiesResolver modelResolver,
        TextModelProviderRegistry textModelProviderRegistry
    ) {
        this.localMediaArtifactService = localMediaArtifactService;
        this.modelResolver = modelResolver;
        this.textModelProviderRegistry = textModelProviderRegistry;
    }

    /**
     * 处理运行Envelope。
     * @param runId 运行标识值
     * @param kind 类型值
     * @param request 请求体
     * @param result 结果值
     * @param specificResultKey 特定结果Key值
     * @return 处理结果
     */
    public Map<String, Object> runEnvelope(
        String runId,
        String kind,
        Map<String, Object> request,
        Map<String, Object> result,
        String specificResultKey
    ) {
        return runEnvelope(runId, kind, request, result, specificResultKey, GenerationRunStatuses.SUCCEEDED);
    }

    /**
     * 处理运行Envelope。
     * @param runId 运行标识值
     * @param kind 类型值
     * @param request 请求体
     * @param result 结果值
     * @param specificResultKey 特定结果Key值
     * @param status 状态值
     * @return 处理结果
     */
    public Map<String, Object> runEnvelope(
        String runId,
        String kind,
        Map<String, Object> request,
        Map<String, Object> result,
        String specificResultKey,
        String status
    ) {
        String now = nowIso();
        Map<String, Object> run = new LinkedHashMap<>();
        run.put("id", runId);
        run.put("kind", kind);
        run.put("status", status);
        run.put("createdAt", now);
        run.put("updatedAt", now);
        run.put("input", mapValue(request.get("input")));
        run.put("model", mapValue(request.get("model")));
        run.put("options", mapValue(request.get("options")));
        run.put("storage", mapValue(request.get("storage")));
        run.put("result", result);
        run.put(specificResultKey, result);
        return run;
    }

    /**
     * 更新运行状态。
     * @param run 运行值
     * @param status 状态值
     */
    public void updateRunStatus(Map<String, Object> run, String status) {
        run.put("status", status);
        run.put("updatedAt", nowIso());
    }

    /**
     * 处理嵌套值。
     * @param payload 附加负载数据
     * @param parentKey 父级Key值
     * @param childKey childKey值
     * @param defaultValue 默认值
     * @return 处理结果
     */
    public String nestedValue(Map<String, Object> payload, String parentKey, String childKey, String defaultValue) {
        Object parent = payload.get(parentKey);
        if (parent instanceof Map<?, ?> map) {
            Object child = map.get(childKey);
            if (child != null) {
                return String.valueOf(child);
            }
        }
        return defaultValue;
    }

    /**
     * 映射值。
     * @param value 待处理的值
     * @return 处理结果
     */
    public Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> normalized = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                normalized.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return normalized;
        }
        return new LinkedHashMap<>();
    }

    /**
     * 处理嵌套Int。
     * @param payload 附加负载数据
     * @param parentKey 父级Key值
     * @param childKey childKey值
     * @param defaultValue 默认值
     * @return 处理结果
     */
    public int nestedInt(Map<String, Object> payload, String parentKey, String childKey, int defaultValue) {
        Object parent = payload.get(parentKey);
        if (parent instanceof Map<?, ?> map) {
            Object child = map.get(childKey);
            if (child instanceof Number number) {
                return number.intValue();
            }
            if (child != null) {
                try {
                    return (int) Math.round(Double.parseDouble(String.valueOf(child)));
                } catch (NumberFormatException ignored) {
                }
            }
        }
        return defaultValue;
    }

    /**
     * 处理嵌套NullableInt。
     * @param payload 附加负载数据
     * @param parentKey 父级Key值
     * @param childKey childKey值
     * @return 处理结果
     */
    public Integer nestedNullableInt(Map<String, Object> payload, String parentKey, String childKey) {
        Object parent = payload.get(parentKey);
        if (!(parent instanceof Map<?, ?> map)) {
            return null;
        }
        Object child = map.get(childKey);
        if (child instanceof Number number) {
            return number.intValue();
        }
        if (child != null) {
            try {
                return (int) Math.round(Double.parseDouble(String.valueOf(child)));
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    /**
     * 检查是否嵌套Boolean。
     * @param payload 附加负载数据
     * @param parentKey 父级Key值
     * @param childKey childKey值
     * @param defaultValue 默认值
     * @return 是否满足条件
     */
    public boolean nestedBoolean(Map<String, Object> payload, String parentKey, String childKey, boolean defaultValue) {
        Object parent = payload.get(parentKey);
        if (!(parent instanceof Map<?, ?> map)) {
            return defaultValue;
        }
        Object child = map.get(childKey);
        if (child instanceof Boolean bool) {
            return bool;
        }
        if (child instanceof Number number) {
            return number.intValue() != 0;
        }
        if (child instanceof String text) {
            String normalized = text.trim().toLowerCase(Locale.ROOT);
            if (List.of("1", "true", "yes", "on").contains(normalized)) {
                return true;
            }
            if (List.of("0", "false", "no", "off").contains(normalized)) {
                return false;
            }
        }
        return defaultValue;
    }

    /**
     * 处理调用日志。
     * @param stage 阶段名称
     * @param event 事件名称
     * @param status 状态值
     * @param message 消息文本
     * @param details details值
     * @return 处理结果
     */
    public Map<String, Object> callLog(String stage, String event, String status, String message, Map<String, Object> details) {
        Map<String, Object> safeDetails = new LinkedHashMap<>();
        if (details != null) {
            for (Map.Entry<String, Object> entry : details.entrySet()) {
                if (entry.getValue() != null) {
                    safeDetails.put(entry.getKey(), entry.getValue());
                }
            }
        }
        if (!safeDetails.containsKey("source")) {
            safeDetails.put("source", "spring");
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("timestamp", nowIso());
        row.put("stage", stage);
        row.put("event", event);
        row.put("status", status);
        row.put("message", message);
        row.put("details", safeDetails);
        return row;
    }

    /**
     * 处理写入Placeholder图像。
     * @param runId 运行标识值
     * @param fileName 文件Name值
     * @param width width值
     * @param height height值
     * @param prompt 提示词值
     * @param stylePreset 风格预设值
     * @return 处理结果
     */
    public ImageArtifact writePlaceholderImage(String runId, String fileName, int width, int height, String prompt, String stylePreset) {
        try {
            return localMediaArtifactService.writePromptCard(
                "gen/_runs/" + runId,
                fileName,
                width,
                height,
                fileName.replace(".png", "").toUpperCase(Locale.ROOT) + " PLACEHOLDER",
                "style: " + stylePreset,
                prompt == null || prompt.isBlank() ? "placeholder output" : prompt
            );
        } catch (RuntimeException ex) {
            throw new GenerationNotImplementedException("generation image artifact write failed: " + ex.getMessage());
        }
    }

    /**
     * 处理写入文本产物。
     * @param runId 运行标识值
     * @param request 请求体
     * @param fileName 文件Name值
     * @param content content值
     * @return 处理结果
     */
    public TextArtifact writeTextArtifact(String runId, Map<String, Object> request, String fileName, String content) {
        try {
            return localMediaArtifactService.writeText(storageRelativeDir(request, runId), storageFileName(request, fileName), content);
        } catch (RuntimeException ex) {
            throw new GenerationNotImplementedException("generation run artifact write failed: " + ex.getMessage());
        }
    }

    /**
     * 处理写入Binary产物。
     * @param runId 运行标识值
     * @param request 请求体
     * @param fileStem 文件Stem值
     * @param extension extension值
     * @param data data值
     * @return 处理结果
     */
    public BinaryArtifact writeBinaryArtifact(String runId, Map<String, Object> request, String fileStem, String extension, byte[] data) {
        try {
            String relativeDir = storageRelativeDir(request, runId);
            String normalizedExtension = (extension == null || extension.isBlank()) ? "bin" : extension;
            String fileName = storageFileStem(request, fileStem) + "." + normalizedExtension;
            StoredArtifact stored = localMediaArtifactService.writeBinary(relativeDir, fileName, data);
            return new BinaryArtifact(
                stored.fileName(),
                stored.absolutePath(),
                stored.publicUrl(),
                stored.sizeBytes(),
                mimeTypeFromFileName(stored.fileName())
            );
        } catch (RuntimeException ex) {
            throw new GenerationProviderException("generation binary artifact write failed: " + ex.getMessage());
        }
    }

    /**
     * 处理materializeBinary产物。
     * @param runId 运行标识值
     * @param relativeDir relativeDir值
     * @param fileStem 文件Stem值
     * @param sourceUrl 来源URL值
     * @return 处理结果
     */
    public BinaryArtifact materializeBinaryArtifact(String runId, String relativeDir, String fileStem, String sourceUrl) {
        try {
            String extension = extensionFromMimeOrUrl("", sourceUrl, "video");
            String fileName = fileStem + "." + extension;
            StoredArtifact stored = localMediaArtifactService.materializeArtifact(sourceUrl, relativeDir, fileName);
            return new BinaryArtifact(
                stored.fileName(),
                stored.absolutePath(),
                stored.publicUrl(),
                stored.sizeBytes(),
                mimeTypeFromFileName(stored.fileName())
            );
        } catch (RuntimeException ex) {
            throw new GenerationProviderException("generation binary artifact materialize failed: " + ex.getMessage());
        }
    }

    /**
     * 解析Dimensions。
     * @param raw 原始值
     * @param fallbackWidth 兜底Width值
     * @param fallbackHeight 兜底Height值
     * @return 处理结果
     */
    public int[] parseDimensions(String raw, int fallbackWidth, int fallbackHeight) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT).replace("x", "*");
        String[] parts = normalized.split("\\*");
        if (parts.length == 2) {
            try {
                return new int[] {Integer.parseInt(parts[0]), Integer.parseInt(parts[1])};
            } catch (Exception ignored) {
            }
        }
        return new int[] {fallbackWidth, fallbackHeight};
    }

    /**
     * 处理boundedTemperature。
     * @param value 待处理的值
     * @param min 最小值
     * @param max 最大值
     * @return 处理结果
     */
    public double boundedTemperature(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    /**
     * 处理条带MarkdownFence。
     * @param text 文本值
     * @return 处理结果
     */
    public String stripMarkdownFence(String text) {
        String value = text == null ? "" : text.trim();
        if (!value.startsWith("```")) {
            return value;
        }
        int firstBreak = value.indexOf('\n');
        int lastFence = value.lastIndexOf("```");
        if (firstBreak < 0 || lastFence <= firstBreak) {
            return value.replace("```", "").trim();
        }
        return value.substring(firstBreak + 1, lastFence).trim();
    }

    /**
     * 处理truncate文本。
     * @param value 待处理的值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public String truncateText(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() <= limit ? value : value.substring(0, limit);
    }

    /**
     * 处理extensionFromMimeOrURL。
     * @param mimeType mime类型值
     * @param sourceUrl 来源URL值
     * @param mediaType 媒体类型值
     * @return 处理结果
     */
    public String extensionFromMimeOrUrl(String mimeType, String sourceUrl, String mediaType) {
        String normalizedMime = mimeType == null ? "" : mimeType.toLowerCase(Locale.ROOT);
        if (normalizedMime.startsWith("image/png")) {
            return "png";
        }
        if (normalizedMime.startsWith("image/jpeg")) {
            return "jpg";
        }
        if (normalizedMime.startsWith("image/webp")) {
            return "webp";
        }
        if (normalizedMime.startsWith("video/mp4")) {
            return "mp4";
        }
        if (normalizedMime.startsWith("video/webm")) {
            return "webm";
        }
        if (sourceUrl != null && !sourceUrl.isBlank()) {
            String path = sourceUrl;
            int queryIndex = path.indexOf('?');
            if (queryIndex >= 0) {
                path = path.substring(0, queryIndex);
            }
            int dotIndex = path.lastIndexOf('.');
            if (dotIndex >= 0 && dotIndex < path.length() - 1) {
                return path.substring(dotIndex + 1).toLowerCase(Locale.ROOT);
            }
        }
        return GenerationModelKinds.IMAGE.equals(mediaType) ? "png" : "mp4";
    }

    /**
     * 处理当前Iso。
     * @return 处理结果
     */
    public String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    /**
     * 处理storageRelativeDir。
     * @param request 请求体
     * @param runId 运行标识值
     * @return 处理结果
     */
    public String storageRelativeDir(Map<String, Object> request, String runId) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("relativeDir"));
        return configured.isBlank() ? "gen/_runs/" + runId : configured;
    }

    /**
     * 处理storage文件Stem。
     * @param request 请求体
     * @param fallback 兜底值
     * @return 处理结果
     */
    public String storageFileStem(Map<String, Object> request, String fallback) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("fileStem"));
        return configured.isBlank() ? fallback : configured;
    }

    /**
     * 处理storage文件Name。
     * @param request 请求体
     * @param fallback 兜底值
     * @return 处理结果
     */
    public String storageFileName(Map<String, Object> request, String fallback) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("fileName"));
        return configured.isBlank() ? fallback : configured;
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    public String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理positiveInt。
     * @param raw 原始值
     * @param fallback 兜底值
     * @return 处理结果
     */
    public int positiveInt(String raw, int fallback) {
        try {
            int value = Integer.parseInt(String.valueOf(raw).trim());
            return value > 0 ? value : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    /**
     * 处理首个PositiveInt。
     * @param values 值
     * @return 处理结果
     */
    public int firstPositiveInt(int... values) {
        for (int value : values) {
            if (value > 0) {
                return value;
            }
        }
        return 0;
    }

    /**
     * 规范化值。
     * @param value 待处理的值
     * @return 处理结果
     */
    public String normalizeValue(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    /**
     * 处理required模型。
     * @param value 待处理的值
     * @param fieldName fieldName值
     * @param label 标签值
     * @return 处理结果
     */
    public String requiredModel(String value, String fieldName, String label) {
        String normalized = value == null ? "" : value.trim();
        if (!normalized.isBlank()) {
            return normalized;
        }
        throw new IllegalArgumentException("请先选择" + label + "（" + fieldName + "）");
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    public String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    /**
     * 解析String列表。
     * @param raw 原始值
     * @param fallback 兜底值
     * @return 处理结果
     */
    public List<String> parseStringList(String raw, List<String> fallback) {
        List<String> items = new ArrayList<>();
        if (raw != null) {
            for (String part : raw.split(",")) {
                String normalized = part == null ? "" : part.trim();
                if (!normalized.isBlank()) {
                    items.add(normalized);
                }
            }
        }
        return items.isEmpty() ? fallback : items;
    }

    /**
     * 解析Integer列表。
     * @param raw 原始值
     * @param fallback 兜底值
     * @return 处理结果
     */
    public List<Integer> parseIntegerList(String raw, List<Integer> fallback) {
        List<Integer> items = new ArrayList<>();
        if (raw != null) {
            for (String part : raw.split(",")) {
                int parsed = positiveInt(part, 0);
                if (parsed > 0) {
                    items.add(parsed);
                }
            }
        }
        return items.isEmpty() ? fallback : items;
    }

    /**
     * 处理string列表。
     * @param value 待处理的值
     * @return 处理结果
     */
    public List<String> stringList(Object value) {
        if (value instanceof List<?> items) {
            List<String> results = new ArrayList<>();
            for (Object item : items) {
                String normalized = String.valueOf(item == null ? "" : item).trim();
                if (!normalized.isBlank()) {
                    results.add(normalized);
                }
            }
            return results;
        }
        return List.of();
    }

    /**
     * 处理integer列表。
     * @param value 待处理的值
     * @return 处理结果
     */
    public List<Integer> integerList(Object value) {
        if (value instanceof List<?> items) {
            List<Integer> results = new ArrayList<>();
            for (Object item : items) {
                int parsed = positiveInt(item == null ? "" : String.valueOf(item), 0);
                if (parsed > 0) {
                    results.add(parsed);
                }
            }
            return results;
        }
        return List.of();
    }

    /**
     * 规范化FrameRole。
     * @param frameRole frameRole值
     * @return 处理结果
     */
    public String normalizeFrameRole(String frameRole) {
        return "last".equalsIgnoreCase(stringValue(frameRole)) ? "last" : "first";
    }

    /**
     * 处理appendNegative提示词。
     * @param prompt 提示词值
     * @param negativePrompt negative提示词值
     * @return 处理结果
     */
    public String appendNegativePrompt(String prompt, String negativePrompt) {
        if (prompt == null || prompt.isBlank()) {
            return "写实影视风格。负面约束：" + negativePrompt;
        }
        return prompt.trim() + "\n负面约束：" + negativePrompt;
    }

    /**
     * 检查是否inferSeedanceCameraFixed。
     * @param prompt 提示词值
     * @param fallback 兜底值
     * @return 是否满足条件
     */
    public boolean inferSeedanceCameraFixed(String prompt, boolean fallback) {
        String normalized = stringValue(prompt).toLowerCase(Locale.ROOT);
        if (normalized.isBlank()) {
            return fallback;
        }
        if (normalized.contains("固定镜头")
            || normalized.contains("固定机位")
            || normalized.contains("镜头固定")
            || normalized.contains("机位固定")
            || normalized.contains("镜头保持固定")
            || normalized.contains("监控视角")
            || normalized.contains("监控镜头")
            || normalized.contains("鱼眼监控")) {
            return true;
        }
        return fallback;
    }

    /**
     * 生成文本With兜底。
     * @param primaryProfile primaryProfile值
     * @param stage 阶段名称
     * @param systemPrompt 系统提示词值
     * @param userPrompt user提示词值
     * @param temperature temperature值
     * @param maxTokens 最大Tokens值
     * @param callChain 调用Chain值
     * @return 处理结果
     */
    public TextGenerationAttempt generateTextWithFallback(
        ModelRuntimeProfile primaryProfile,
        String stage,
        String systemPrompt,
        String userPrompt,
        double temperature,
        int maxTokens,
        List<Map<String, Object>> callChain
    ) {
        try {
            return new TextGenerationAttempt(
                primaryProfile,
                textModelProviderRegistry.resolve(primaryProfile).generate(
                    primaryProfile,
                    new TextCompletionInvocation(systemPrompt, userPrompt, temperature, maxTokens)
                )
            );
        } catch (RuntimeException primaryEx) {
            String fallbackModel = primaryProfile.fallbackModel();
            if (fallbackModel == null || fallbackModel.isBlank() || fallbackModel.equalsIgnoreCase(primaryProfile.modelName())) {
                throw primaryEx;
            }
            callChain.add(callLog(stage, stage + ".fallback", "retry", "主文本模型失败，尝试回退到备用模型。", Map.of(
                "requestedModel", primaryProfile.modelName(),
                "fallbackModel", fallbackModel,
                /**
                 * 处理truncate文本。
                 * @param primaryEx.getMessage( primaryEx.getMessage(值
                 * @param 240 240值
                 * @return 处理结果
                 */
                "error", truncateText(primaryEx.getMessage(), 240)
            )));
            ModelRuntimeProfile fallbackProfile = modelResolver.resolveTextProfile(fallbackModel);
            return new TextGenerationAttempt(
                fallbackProfile,
                textModelProviderRegistry.resolve(fallbackProfile).generate(
                    fallbackProfile,
                    new TextCompletionInvocation(systemPrompt, userPrompt, temperature, maxTokens)
                )
            );
        }
    }

    /**
     * 构建模型信息。
     * @param profile profile值
     * @param requestedModel requested模型值
     * @param mediaKind 媒体类型值
     * @param response 响应体
     * @param sourceTag 来源Tag值
     * @return 处理结果
     */
    public Map<String, Object> buildModelInfo(
        ModelRuntimeProfile profile,
        String requestedModel,
        String mediaKind,
        TextModelResponse response,
        String sourceTag
    ) {
        Map<String, Object> modelInfo = new LinkedHashMap<>();
        modelInfo.put("provider", profile.provider());
        modelInfo.put("modelName", profile.modelName());
        modelInfo.put("providerModel", profile.modelName());
        modelInfo.put("requestedModel", requestedModel);
        modelInfo.put("resolvedModel", profile.modelName());
        modelInfo.put("textAnalysisModel", profile.modelName());
        modelInfo.put("mediaKind", mediaKind);
        modelInfo.put("endpointHost", response == null ? profile.endpointHost() : response.endpointHost());
        modelInfo.put("configSource", profile.source());
        modelInfo.put("generationSource", sourceTag);
        return modelInfo;
    }

    /**
     * 构建媒体模型信息。
     * @param textProfile 文本Profile值
     * @param rewriteProfile rewriteProfile值
     * @param visionProfile 视觉Profile值
     * @param mediaProfile 媒体Profile值
     * @param requestedModel requested模型值
     * @param mediaKind 媒体类型值
     * @param textResponse 文本响应值
     * @param visionResponse 视觉响应值
     * @param resolvedModel resolved模型值
     * @param endpointHost endpointHost值
     * @param taskEndpointHost 任务EndpointHost值
     * @param sourceTag 来源Tag值
     * @return 处理结果
     */
    public Map<String, Object> buildMediaModelInfo(
        ModelRuntimeProfile textProfile,
        ModelRuntimeProfile rewriteProfile,
        ModelRuntimeProfile visionProfile,
        MediaProviderProfile mediaProfile,
        String requestedModel,
        String mediaKind,
        TextModelResponse textResponse,
        TextModelResponse visionResponse,
        String resolvedModel,
        String endpointHost,
        String taskEndpointHost,
        String sourceTag
    ) {
        Map<String, Object> modelInfo = new LinkedHashMap<>();
        modelInfo.put("provider", mediaProfile.provider());
        modelInfo.put("modelName", resolvedModel);
        modelInfo.put("providerModel", resolvedModel);
        modelInfo.put("requestedModel", requestedModel);
        modelInfo.put("resolvedModel", resolvedModel);
        modelInfo.put("textAnalysisModel", textProfile.modelName());
        modelInfo.put("textAnalysisProvider", textProfile.provider());
        modelInfo.put("textAnalysisEndpointHost", textProfile.endpointHost());
        if (rewriteProfile != null) {
            modelInfo.put("promptRewriteModel", rewriteProfile.modelName());
            modelInfo.put("promptRewriteProvider", rewriteProfile.provider());
            modelInfo.put("promptRewriteEndpointHost", textResponse == null ? rewriteProfile.endpointHost() : textResponse.endpointHost());
        }
        if (visionProfile != null) {
            modelInfo.put("visionAnalysisModel", visionProfile.modelName());
            modelInfo.put("visionAnalysisProvider", visionProfile.provider());
            modelInfo.put("visionAnalysisEndpointHost", visionResponse == null ? visionProfile.endpointHost() : visionResponse.endpointHost());
        }
        modelInfo.put("mediaKind", mediaKind);
        modelInfo.put("endpointHost", endpointHost);
        modelInfo.put("taskEndpointHost", taskEndpointHost);
        modelInfo.put("configSource", mediaProfile.source());
        modelInfo.put("generationSource", sourceTag);
        return modelInfo;
    }

    /**
     * 处理mime类型From文件Name。
     * @param fileName 文件Name值
     * @return 处理结果
     */
    private String mimeTypeFromFileName(String fileName) {
        String value = fileName == null ? "" : fileName.toLowerCase(Locale.ROOT);
        if (value.endsWith(".mp4")) {
            return "video/mp4";
        }
        if (value.endsWith(".webm")) {
            return "video/webm";
        }
        if (value.endsWith(".png")) {
            return "image/png";
        }
        if (value.endsWith(".jpg") || value.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        if (value.endsWith(".webp")) {
            return "image/webp";
        }
        return "application/octet-stream";
    }

    /**
     * 处理Binary产物。
     * @param fileName 文件Name值
     * @param absolutePath absolute路径值
     * @param publicUrl publicURL值
     * @param sizeBytes sizeBytes值
     * @param mimeType mime类型值
     * @return 处理结果
     */
    public record BinaryArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        String mimeType
    ) {
    }

    /**
     * 处理文本生成尝试。
     * @param profile profile值
     * @param response 响应体
     * @return 处理结果
     */
    public record TextGenerationAttempt(
        ModelRuntimeProfile profile,
        TextModelResponse response
    ) {
    }
}
