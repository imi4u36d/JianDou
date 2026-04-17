package com.jiandou.api.admin.application;

import com.jiandou.api.admin.dto.AdminModelConfigKeyUpdateRequest;
import com.jiandou.api.admin.dto.AdminModelConfigResponse;
import com.jiandou.api.admin.dto.AdminModelConfigValidationResponse;
import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/**
 * 管理端模型配置服务。
 */
@Service
public class AdminModelConfigService {

    private static final List<String> KIND_ORDER = List.of(
        GenerationModelKinds.TEXT,
        GenerationModelKinds.VISION,
        GenerationModelKinds.IMAGE,
        GenerationModelKinds.VIDEO
    );
    private static final String MISSING_API_KEY_ISSUE = "缺少 api_key";

    private final ModelRuntimePropertiesResolver modelResolver;
    private final AdminModelConfigSecretsService secretsService;

    /**
     * 创建新的管理端模型配置服务。
     * @param modelResolver 模型解析器值
     * @param secretsService secrets 落盘服务值
     */
    public AdminModelConfigService(ModelRuntimePropertiesResolver modelResolver, AdminModelConfigSecretsService secretsService) {
        this.modelResolver = modelResolver;
        this.secretsService = secretsService;
    }

    /**
     * 返回当前模型配置快照。
     * @return 处理结果
     */
    public AdminModelConfigResponse read() {
        List<AdminModelConfigResponse.ModelItem> models = new ArrayList<>();
        models.addAll(readTextModels(GenerationModelKinds.TEXT));
        models.addAll(readTextModels(GenerationModelKinds.VISION));
        models.addAll(readMediaModels(GenerationModelKinds.IMAGE));
        models.addAll(readMediaModels(GenerationModelKinds.VIDEO));
        models.sort(Comparator
            .comparingInt((AdminModelConfigResponse.ModelItem item) -> kindIndex(item.kind()))
            .thenComparing(AdminModelConfigResponse.ModelItem::name, String.CASE_INSENSITIVE_ORDER));

        List<AdminModelConfigResponse.ProviderItem> providers = readProviders(models);
        return new AdminModelConfigResponse(
            modelResolver.configSource(),
            buildSummary(models, providers),
            readDefaults(),
            providers,
            List.copyOf(models),
            modelResolver.configErrors()
        );
    }

    /**
     * 校验模型接入 API Key 草稿。
     * @param request 密钥输入请求值
     * @return 处理结果
     */
    public AdminModelConfigValidationResponse validateKeys(AdminModelConfigKeyUpdateRequest request) {
        AdminModelConfigResponse current = read();
        AdminModelConfigResponse snapshot = applyApiKeyOverrides(current, collectApiKeyUpdates(request, current.providers()));
        boolean valid = snapshot.configErrors().isEmpty() && snapshot.models().stream().allMatch(AdminModelConfigResponse.ModelItem::ready);
        return new AdminModelConfigValidationResponse(valid, snapshot);
    }

    /**
     * 保存模型接入 API Key 覆盖，并刷新运行时快照。
     * @param request 密钥输入请求值
     * @return 处理结果
     */
    public AdminModelConfigResponse saveKeys(AdminModelConfigKeyUpdateRequest request) {
        AdminModelConfigResponse current = read();
        ApiKeyUpdateBatch updates = collectApiKeyUpdates(request, current.providers());
        if (!updates.errors().isEmpty()) {
            throw new IllegalArgumentException(String.join(" / ", updates.errors()));
        }
        if (updates.apiKeys().isEmpty()) {
            return current;
        }
        secretsService.saveApiKeys(updates.apiKeys());
        modelResolver.refresh();
        return read();
    }

    private AdminModelConfigResponse.Defaults readDefaults() {
        return new AdminModelConfigResponse.Defaults(
            modelResolver.value("pipeline", "default_aspect_ratio", "9:16"),
            modelResolver.value("catalog.defaults", "style_preset", "cinematic"),
            modelResolver.value("catalog.defaults", "image_size", "1024x1024"),
            modelResolver.value("catalog.defaults", "video_size", "720*1280"),
            modelResolver.intValue("catalog.defaults", "video_duration_seconds", 8),
            modelResolver.intValue("model", "timeout_seconds", 120),
            doubleValue(modelResolver.value("model", "temperature", "0.15"), 0.15),
            modelResolver.intValue("model", "max_tokens", 2000)
        );
    }

    private ApiKeyUpdateBatch collectApiKeyUpdates(
        AdminModelConfigKeyUpdateRequest request,
        List<AdminModelConfigResponse.ProviderItem> providers
    ) {
        Map<String, String> knownProviders = new LinkedHashMap<>();
        for (AdminModelConfigResponse.ProviderItem provider : providers) {
            knownProviders.put(normalize(provider.key()), provider.key());
            if (!provider.provider().isBlank()) {
                knownProviders.putIfAbsent(normalize(provider.provider()), provider.key());
            }
        }
        List<String> errors = new ArrayList<>();
        Map<String, String> updates = new LinkedHashMap<>();
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        List<AdminModelConfigKeyUpdateRequest.ProviderKeyInput> inputs = request == null || request.providers() == null
            ? List.of()
            : request.providers();
        for (AdminModelConfigKeyUpdateRequest.ProviderKeyInput input : inputs) {
            String requestedKey = trimToEmpty(input == null ? null : input.key());
            String apiKey = trimToEmpty(input == null ? null : input.apiKey());
            if (requestedKey.isBlank()) {
                if (!apiKey.isBlank()) {
                    errors.add("存在未命名模型接入");
                }
                continue;
            }
            String resolvedKey = knownProviders.get(normalize(requestedKey));
            if (resolvedKey == null) {
                if (!apiKey.isBlank()) {
                    errors.add("未知模型接入: " + requestedKey);
                }
                continue;
            }
            if (!seen.add(resolvedKey)) {
                errors.add("模型接入重复: " + resolvedKey);
                continue;
            }
            if (!apiKey.isBlank()) {
                updates.put(resolvedKey, apiKey);
            }
        }
        return new ApiKeyUpdateBatch(Map.copyOf(updates), List.copyOf(errors));
    }

    private AdminModelConfigResponse applyApiKeyOverrides(
        AdminModelConfigResponse base,
        ApiKeyUpdateBatch updates
    ) {
        Map<String, AdminModelConfigResponse.ProviderItem> providersByLookup = new LinkedHashMap<>();
        List<AdminModelConfigResponse.ProviderItem> providers = new ArrayList<>();
        for (AdminModelConfigResponse.ProviderItem provider : base.providers()) {
            boolean apiKeyConfigured = provider.apiKeyConfigured() || updates.apiKeys().containsKey(provider.key());
            AdminModelConfigResponse.ProviderItem updated = new AdminModelConfigResponse.ProviderItem(
                provider.key(),
                provider.provider(),
                provider.vendor(),
                provider.kinds(),
                provider.baseUrl(),
                provider.taskBaseUrl(),
                provider.endpointHost(),
                provider.taskEndpointHost(),
                apiKeyConfigured,
                provider.baseUrlConfigured(),
                provider.taskBaseUrlConfigured(),
                provider.extras(),
                provider.modelNames()
            );
            providers.add(updated);
            providersByLookup.put(normalize(updated.key()), updated);
            if (!updated.provider().isBlank()) {
                providersByLookup.putIfAbsent(normalize(updated.provider()), updated);
            }
        }

        List<AdminModelConfigResponse.ModelItem> models = base.models().stream()
            .map(model -> applyModelApiKeyOverride(model, providersByLookup.get(normalize(model.provider()))))
            .toList();

        List<String> configErrors = new ArrayList<>(base.configErrors());
        for (String error : updates.errors()) {
            if (!configErrors.contains(error)) {
                configErrors.add(error);
            }
        }
        return new AdminModelConfigResponse(
            base.configSource(),
            buildSummary(models, providers),
            base.defaults(),
            List.copyOf(providers),
            List.copyOf(models),
            List.copyOf(configErrors)
        );
    }

    private AdminModelConfigResponse.ModelItem applyModelApiKeyOverride(
        AdminModelConfigResponse.ModelItem model,
        AdminModelConfigResponse.ProviderItem provider
    ) {
        List<String> issues = rebuildIssues(model.issues(), provider);
        return new AdminModelConfigResponse.ModelItem(
            model.name(),
            model.label(),
            model.kind(),
            model.provider(),
            model.vendor(),
            model.family(),
            model.description(),
            model.fallbackModel(),
            model.supportsSeed(),
            model.supportsResponsesApi(),
            model.prefersChatCompletionsForVision(),
            model.generationMode(),
            model.supportedSizes(),
            model.supportedDurations(),
            issues.isEmpty(),
            model.configSource(),
            model.endpointHost(),
            model.taskEndpointHost(),
            List.copyOf(issues)
        );
    }

    private List<String> rebuildIssues(
        List<String> existingIssues,
        AdminModelConfigResponse.ProviderItem provider
    ) {
        List<String> issues = new ArrayList<>();
        boolean missingApiKey = provider == null
            ? existingIssues.contains(MISSING_API_KEY_ISSUE)
            : !provider.apiKeyConfigured();
        if (missingApiKey) {
            issues.add(MISSING_API_KEY_ISSUE);
        }
        for (String issue : existingIssues) {
            if (MISSING_API_KEY_ISSUE.equals(issue) || issues.contains(issue)) {
                continue;
            }
            issues.add(issue);
        }
        return issues;
    }

    private AdminModelConfigResponse.Summary buildSummary(
        List<AdminModelConfigResponse.ModelItem> models,
        List<AdminModelConfigResponse.ProviderItem> providers
    ) {
        int providerCount = providers == null ? 0 : providers.size();
        int vendorCount = providers == null
            ? 0
            : (int) providers.stream()
                .map(AdminModelConfigResponse.ProviderItem::vendor)
                .map(this::normalize)
                .filter(value -> !value.isBlank())
                .distinct()
                .count();
        return new AdminModelConfigResponse.Summary(
            providerCount,
            vendorCount,
            models.size(),
            countReadyModels(models, null),
            countReadyModels(models, GenerationModelKinds.TEXT),
            countReadyModels(models, GenerationModelKinds.VISION),
            countReadyModels(models, GenerationModelKinds.IMAGE),
            countReadyModels(models, GenerationModelKinds.VIDEO)
        );
    }

    private List<AdminModelConfigResponse.ModelItem> readTextModels(String kind) {
        List<AdminModelConfigResponse.ModelItem> items = new ArrayList<>();
        for (Map<String, Object> item : modelResolver.listModelsByKind(kind)) {
            String name = stringValue(item.get("value"));
            ModelRuntimeProfile profile = modelResolver.resolveTextProfile(name);
            List<String> issues = new ArrayList<>();
            if (profile.apiKey().isBlank()) {
                issues.add(MISSING_API_KEY_ISSUE);
            }
            if (profile.baseUrl().isBlank()) {
                issues.add("缺少 base_url");
            }
            items.add(new AdminModelConfigResponse.ModelItem(
                name,
                firstNonBlank(stringValue(item.get("label")), name),
                kind,
                profile.provider(),
                stringValue(item.get("vendor")),
                stringValue(item.get("family")),
                stringValue(item.get("description")),
                stringValue(item.get("fallbackModel")),
                booleanValue(item.get("supportsSeed")),
                booleanValue(item.get("supportsResponsesApi")),
                booleanValue(item.get("prefersChatCompletionsForVision")),
                "",
                List.of(),
                List.of(),
                issues.isEmpty() && profile.ready(),
                profile.source(),
                profile.endpointHost(),
                "",
                List.copyOf(issues)
            ));
        }
        return items;
    }

    private List<AdminModelConfigResponse.ModelItem> readMediaModels(String kind) {
        List<AdminModelConfigResponse.ModelItem> items = new ArrayList<>();
        for (Map<String, Object> item : modelResolver.listModelsByKind(kind)) {
            String name = stringValue(item.get("value"));
            MediaProviderProfile profile = modelResolver.resolveMediaProfile(name, kind);
            List<String> issues = new ArrayList<>();
            if (profile.apiKey().isBlank()) {
                issues.add(MISSING_API_KEY_ISSUE);
            }
            if (profile.baseUrl().isBlank()) {
                issues.add("缺少 base_url");
            }
            if (GenerationModelKinds.VIDEO.equals(kind) && profile.taskBaseUrl().isBlank()) {
                issues.add("缺少 task_base_url");
            }
            items.add(new AdminModelConfigResponse.ModelItem(
                name,
                firstNonBlank(stringValue(item.get("label")), name),
                kind,
                profile.provider(),
                stringValue(item.get("vendor")),
                stringValue(item.get("family")),
                stringValue(item.get("description")),
                "",
                booleanValue(item.get("supportsSeed")),
                false,
                false,
                stringValue(item.get("generationMode")),
                stringList(item.get("supportedSizes")),
                integerList(item.get("supportedDurations")),
                issues.isEmpty() && profile.ready(),
                profile.source(),
                profile.endpointHost(),
                profile.taskEndpointHost(),
                List.copyOf(issues)
            ));
        }
        return items;
    }

    private List<AdminModelConfigResponse.ProviderItem> readProviders(List<AdminModelConfigResponse.ModelItem> models) {
        List<AdminModelConfigResponse.ProviderItem> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("model.providers")) {
            String key = section.name();
            String providerName = firstNonBlank(section.values().get("provider"), key);
            String vendorName = firstNonBlank(
                section.values().get("vendor"),
                models.stream()
                    .filter(item -> providerName.equalsIgnoreCase(item.provider()) || key.equalsIgnoreCase(item.provider()))
                    .map(AdminModelConfigResponse.ModelItem::vendor)
                    .filter(value -> value != null && !value.isBlank())
                    .findFirst()
                    .orElse("")
            );
            List<AdminModelConfigResponse.ModelItem> providerModels = models.stream()
                .filter(item -> providerName.equalsIgnoreCase(item.provider()) || key.equalsIgnoreCase(item.provider()))
                .toList();
            AdminModelConfigResponse.ModelItem sampleTextModel = providerModels.stream()
                .filter(item -> GenerationModelKinds.TEXT.equals(item.kind()) || GenerationModelKinds.VISION.equals(item.kind()))
                .findFirst()
                .orElse(null);
            AdminModelConfigResponse.ModelItem sampleVideoModel = providerModels.stream()
                .filter(item -> GenerationModelKinds.VIDEO.equals(item.kind()))
                .findFirst()
                .orElse(null);
            String baseUrl = firstNonBlank(
                resolveModelBaseUrl(sampleTextModel),
                resolveModelBaseUrl(sampleVideoModel),
                section.values().get("base_url")
            );
            String taskBaseUrl = firstNonBlank(
                resolveTaskBaseUrl(sampleVideoModel),
                modelResolver.value("model.providers." + key + ".extras", "task_base_url", "")
            );
            String endpointHost = hostOf(baseUrl);
            String taskEndpointHost = hostOf(taskBaseUrl);
            Map<String, String> extras = new LinkedHashMap<>(modelResolver.section("model.providers." + key + ".extras"));
            items.add(new AdminModelConfigResponse.ProviderItem(
                key,
                providerName,
                vendorName,
                providerModels.stream().map(AdminModelConfigResponse.ModelItem::kind).distinct().sorted(this::compareKinds).toList(),
                baseUrl,
                taskBaseUrl,
                endpointHost,
                taskEndpointHost,
                !firstNonBlank(resolveApiKey(sampleTextModel), resolveApiKey(sampleVideoModel), section.values().get("api_key")).isBlank(),
                !baseUrl.isBlank(),
                !taskBaseUrl.isBlank(),
                Map.copyOf(extras),
                providerModels.stream().map(AdminModelConfigResponse.ModelItem::name).toList()
            ));
        }
        items.sort(Comparator.comparing(AdminModelConfigResponse.ProviderItem::key, String.CASE_INSENSITIVE_ORDER));
        return items;
    }

    private String resolveApiKey(AdminModelConfigResponse.ModelItem model) {
        if (model == null) {
            return "";
        }
        if (GenerationModelKinds.TEXT.equals(model.kind()) || GenerationModelKinds.VISION.equals(model.kind())) {
            return modelResolver.resolveTextProfile(model.name()).apiKey();
        }
        return modelResolver.resolveMediaProfile(model.name(), model.kind()).apiKey();
    }

    private String resolveModelBaseUrl(AdminModelConfigResponse.ModelItem model) {
        if (model == null) {
            return "";
        }
        if (GenerationModelKinds.TEXT.equals(model.kind()) || GenerationModelKinds.VISION.equals(model.kind())) {
            return modelResolver.resolveTextProfile(model.name()).baseUrl();
        }
        return modelResolver.resolveMediaProfile(model.name(), model.kind()).baseUrl();
    }

    private String resolveTaskBaseUrl(AdminModelConfigResponse.ModelItem model) {
        if (model == null) {
            return "";
        }
        return modelResolver.resolveMediaProfile(model.name(), model.kind()).taskBaseUrl();
    }

    private int countReadyModels(List<AdminModelConfigResponse.ModelItem> models, String kind) {
        return (int) models.stream()
            .filter(AdminModelConfigResponse.ModelItem::ready)
            .filter(item -> kind == null || kind.equals(item.kind()))
            .count();
    }

    private int compareKinds(String left, String right) {
        return Integer.compare(kindIndex(left), kindIndex(right));
    }

    private int kindIndex(String kind) {
        int index = KIND_ORDER.indexOf(normalize(kind));
        return index >= 0 ? index : KIND_ORDER.size();
    }

    private String hostOf(String raw) {
        try {
            return java.net.URI.create(raw).getHost();
        } catch (Exception ignored) {
            return "";
        }
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean booleanValue(Object value) {
        if (value instanceof Boolean booleanValue) {
            return booleanValue;
        }
        String normalized = stringValue(value).toLowerCase(Locale.ROOT);
        return "true".equals(normalized) || "1".equals(normalized) || "yes".equals(normalized) || "on".equals(normalized);
    }

    private List<String> stringList(Object value) {
        if (value instanceof List<?> items) {
            return items.stream().map(this::stringValue).filter(item -> !item.isBlank()).toList();
        }
        String normalized = stringValue(value);
        if (normalized.isBlank()) {
            return List.of();
        }
        return java.util.Arrays.stream(normalized.split(","))
            .map(String::trim)
            .filter(item -> !item.isBlank())
            .collect(Collectors.toCollection(LinkedHashSet::new))
            .stream()
            .toList();
    }

    private List<Integer> integerList(Object value) {
        if (value instanceof List<?> items) {
            return items.stream()
                .map(this::stringValue)
                .map(this::integerValue)
                .filter(item -> item != null && item > 0)
                .distinct()
                .toList();
        }
        List<Integer> numbers = new ArrayList<>();
        for (String item : stringList(value)) {
            Integer parsed = integerValue(item);
            if (parsed != null && parsed > 0 && !numbers.contains(parsed)) {
                numbers.add(parsed);
            }
        }
        return List.copyOf(numbers);
    }

    private Integer integerValue(String value) {
        try {
            return Integer.parseInt(value.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private double doubleValue(String raw, double fallback) {
        try {
            return Double.parseDouble(String.valueOf(raw).trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private record ApiKeyUpdateBatch(
        Map<String, String> apiKeys,
        List<String> errors
    ) {
    }
}
