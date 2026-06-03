package com.jiandou.api.generation.runtime;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.exception.GenerationConfigurationException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.YamlMapFactoryBean;
import org.springframework.core.env.Environment;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

/**
 * 模型运行时Properties解析器。
 */
@Service
public class ModelRuntimePropertiesResolver {

    private static final Logger log = LoggerFactory.getLogger(ModelRuntimePropertiesResolver.class);

    private final Environment environment;
    private final GenerationConfigPathLocator configPathLocator;
    private final RuntimeModelCredentialProvider credentialProvider;
    private final long cacheTtlMillis;
    private final boolean failFastOnConfigError;
    private volatile CachedSnapshot cachedSnapshot;

    /**
     * 创建新的模型运行时Properties解析器。
     * @param environment environment值
     */
    public ModelRuntimePropertiesResolver(Environment environment) {
        this(environment, new GenerationConfigPathLocator(environment), null);
    }

    /**
     * 创建新的模型运行时Properties解析器。
     * @param environment environment值
     * @param configPathLocator 配置路径Locator值
     */
    public ModelRuntimePropertiesResolver(Environment environment, GenerationConfigPathLocator configPathLocator) {
        this(environment, configPathLocator, null);
    }

    /**
     * 创建新的模型运行时Properties解析器。
     * @param environment environment值
     * @param configPathLocator 配置路径Locator值
     * @param credentialProvider 用户模型凭证Provider值
     */
    @Autowired
    public ModelRuntimePropertiesResolver(
        Environment environment,
        GenerationConfigPathLocator configPathLocator,
        RuntimeModelCredentialProvider credentialProvider
    ) {
        this.environment = environment;
        this.configPathLocator = configPathLocator;
        this.credentialProvider = credentialProvider;
        this.cacheTtlMillis = resolveCacheTtlMillis();
        this.failFastOnConfigError = resolveConfigFailFast();
    }

    /**
     * 处理解析文本Profile。
     * @param requestedModel requested模型值
     * @return 处理结果
     */
    public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
        return resolveTextProfile(requestedModel, null);
    }

    /**
     * 处理解析文本Profile。
     * @param requestedModel requested模型值
     * @param userId 用户ID值
     * @return 处理结果
     */
    public ModelRuntimeProfile resolveTextProfile(String requestedModel, Long userId) {
        ConfigSnapshot current = snapshot();
        boolean userScoped = userId != null;
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return new ModelRuntimeProfile(
                new TextProviderConfig(
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
                    doubleValue(firstNonBlank(current.value("model", "temperature"), "0.15"), 0.15),
                    intValue(firstNonBlank(current.value("model", "max_tokens"), "2000"), 2000),
                    current.source()
                ),
                new TextProviderCapabilities(false, false)
            );
        }
        ResolvedModel resolvedModel = resolveConfiguredModel(current, modelName);
        String modelSection = resolvedModel.sectionPath();
        Map<String, Object> modelValues = resolvedModel.section();
        String kind = firstNonBlank(stringValue(modelValues.get("kind")), GenerationModelKinds.TEXT).toLowerCase(Locale.ROOT);
        String provider = firstNonBlank(
            property("JIANDOU_MODEL_PROVIDER"),
            stringValue(modelValues.get("provider")),
            ""
        );
        String providerSection = "model.providers." + provider;
        String vendor = firstNonBlank(stringValue(modelValues.get("vendor")), current.value(providerSection, "vendor"));
        String apiKey = resolveApiKey(current, userId, provider, vendor, providerSection);
        String baseUrl = normalizeBaseUrl(firstNonBlank(
            property("JIANDOU_MODEL_BASE_URL"),
            property("JIANDOU_MODEL_ENDPOINT"),
            providerProperty(provider, "BASE_URL"),
            providerProperty(provider, "ENDPOINT"),
            current.value(providerSection, "base_url"),
            deriveBaseUrlFromHost(property("JIANDOU_MODEL_ENDPOINT_HOST")),
            ""
        ));
        int timeoutSeconds = intValue(
            firstNonBlank(
                property("JIANDOU_MODEL_TIMEOUT"),
                current.value(modelSection, "timeout_seconds"),
                current.value(providerSection + ".extras", "timeout_seconds"),
                current.value("model", "timeout_seconds"),
                "120"
            ),
            120
        );
        double temperature = doubleValue(
            firstNonBlank(
                property("JIANDOU_MODEL_TEMPERATURE"),
                current.value(modelSection, "temperature"),
                current.value("model", "temperature"),
                "0.15"
            ),
            0.15
        );
        int maxTokens = intValue(
            firstNonBlank(
                property("JIANDOU_MODEL_MAX_TOKENS"),
                current.value(modelSection, "max_tokens"),
                current.value("model", "max_tokens"),
                "2000"
            ),
            2000
        );
        String source = resolveConfigSource(userScoped, apiKey, provider, vendor, current.source(), !property("JIANDOU_MODEL_PROVIDER").isBlank());
        return new ModelRuntimeProfile(
            new TextProviderConfig(
                kind,
                modelName,
                provider,
                configuredProviderModel(modelName, resolvedModel),
                apiKey,
                baseUrl,
                timeoutSeconds,
                temperature,
                maxTokens,
                source
            ),
            new TextProviderCapabilities(
                boolValue(stringValue(modelValues.get("supports_seed"))),
                resolveTextSupportsResponsesApi(current, providerSection, provider, baseUrl)
            )
        );
    }

    /**
     * 处理配置来源。
     * @return 处理结果
     */
    public String configSource() {
        return snapshot().source();
    }

    /**
     * 处理配置Errors。
     * @return 处理结果
     */
    public List<String> configErrors() {
        return snapshot().errors();
    }

    /**
     * 处理refresh。
     */
    public void refresh() {
        synchronized (this) {
            cachedSnapshot = null;
        }
    }

    /**
     * 处理值。
     * @param section section值
     * @param key key值
     * @param fallback 兜底值
     * @return 处理结果
     */
    public String value(String section, String key, String fallback) {
        return firstNonBlank(snapshot().value(section, key), fallback);
    }

    /**
     * 处理int值。
     * @param section section值
     * @param key key值
     * @param fallback 兜底值
     * @return 处理结果
     */
    public int intValue(String section, String key, int fallback) {
        return intValue(snapshot().value(section, key), fallback);
    }

    /**
     * 列出ModelsBy类型。
     * @param kind 类型值
     * @return 处理结果
     */
    public List<Map<String, Object>> listModelsByKind(String kind) {
        String targetKind = trimToEmpty(kind).toLowerCase(Locale.ROOT);
        if (targetKind.isBlank()) {
            return List.of();
        }
        ConfigSnapshot current = snapshot();
        Map<String, Object> models = current.map("model.models");
        if (models.isEmpty()) {
            return List.of();
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Map.Entry<String, Object> entry : models.entrySet()) {
            if (!(entry.getValue() instanceof Map<?, ?> sectionRaw)) {
                continue;
            }
            Map<String, Object> section = normalizeMap(sectionRaw);
            if (!targetKind.equals(trimToEmpty(stringValue(section.get("kind"))).toLowerCase(Locale.ROOT))) {
                continue;
            }
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("value", entry.getKey());
            item.put("label", firstNonBlank(stringValue(section.get("label")), entry.getKey()));
            String provider = trimToEmpty(stringValue(section.get("provider")));
            String providerSection = provider.isBlank() ? "" : "model.providers." + provider;
            item.put("provider", provider);
            item.put("vendor", firstNonBlank(
                trimToEmpty(stringValue(section.get("vendor"))),
                providerSection.isBlank() ? "" : current.value(providerSection, "vendor")
            ));
            item.put("family", trimToEmpty(stringValue(section.get("family"))));
            item.put("description", trimToEmpty(stringValue(section.get("description"))));
            item.put("kind", targetKind);
            if (GenerationModelKinds.TEXT.equals(targetKind)) {
                ModelRuntimeProfile textProfile = resolveTextProfile(entry.getKey());
                item.put("supportsSeed", textProfile.supportsSeed());
                item.put("supportsResponsesApi", textProfile.supportsResponsesApi());
                items.add(item);
                continue;
            }
            MediaProviderProfile mediaProfile = (GenerationModelKinds.IMAGE.equals(targetKind) || GenerationModelKinds.VIDEO.equals(targetKind))
                ? resolveMediaProfile(entry.getKey(), targetKind, current, null)
                : null;
            item.put("supportsSeed", mediaProfile != null ? mediaProfile.supportsSeed() : boolValue(stringValue(section.get("supports_seed"))));
            if (mediaProfile != null) {
                if (GenerationModelKinds.VIDEO.equals(targetKind)) {
                    item.put("generationMode", firstNonBlank(mediaProfile.generationMode(), "i2v"));
                }
                item.put("supportedSizes", mediaProfile.supportedSizes());
                item.put("supportedDurations", mediaProfile.supportedDurations());
            }
            items.add(item);
        }
        return items;
    }

    /**
     * 检查是否supports种子。
     * @param requestedModel requested模型值
     * @return 是否满足条件
     */
    public boolean supportsSeed(String requestedModel) {
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return false;
        }
        ResolvedModel resolvedModel = resolveConfiguredModel(snapshot(), modelName);
        return boolValue(stringValue(resolvedModel.section().get("supports_seed")));
    }

    /**
     * 处理section。
     * @param sectionName sectionName值
     * @return 处理结果
     */
    public Map<String, String> section(String sectionName) {
        return snapshot().section(sectionName);
    }

    /**
     * 列出Sections。
     * @param prefix prefix值
     * @return 处理结果
     */
    public List<ConfigSection> listSections(String prefix) {
        return snapshot().listSections(prefix);
    }

    /**
     * 处理解析图像Profile。
     * @param requestedModel requested模型值
     * @return 处理结果
     */
    public MediaProviderProfile resolveImageProfile(String requestedModel) {
        return resolveImageProfile(requestedModel, null);
    }

    /**
     * 处理解析图像Profile。
     * @param requestedModel requested模型值
     * @param userId 用户ID值
     * @return 处理结果
     */
    public MediaProviderProfile resolveImageProfile(String requestedModel, Long userId) {
        return resolveMediaProfile(requestedModel, GenerationModelKinds.IMAGE, userId);
    }

    /**
     * 处理解析视频Profile。
     * @param requestedModel requested模型值
     * @return 处理结果
     */
    public MediaProviderProfile resolveVideoProfile(String requestedModel) {
        return resolveVideoProfile(requestedModel, null);
    }

    /**
     * 处理解析视频Profile。
     * @param requestedModel requested模型值
     * @param userId 用户ID值
     * @return 处理结果
     */
    public MediaProviderProfile resolveVideoProfile(String requestedModel, Long userId) {
        return resolveMediaProfile(requestedModel, GenerationModelKinds.VIDEO, userId);
    }

    /**
     * 统一解析媒体Profile。
     * @param requestedModel requested模型值
     * @param expectedKind 期望类型值
     * @return 处理结果
     */
    public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind) {
        ConfigSnapshot current = snapshot();
        return resolveMediaProfile(requestedModel, expectedKind, current, null);
    }

    /**
     * 统一解析媒体Profile。
     * @param requestedModel requested模型值
     * @param expectedKind 期望类型值
     * @param userId 用户ID值
     * @return 处理结果
     */
    public MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind, Long userId) {
        ConfigSnapshot current = snapshot();
        return resolveMediaProfile(requestedModel, expectedKind, current, userId);
    }

    /**
     * 统一解析媒体Profile。
     * @param requestedModel requested模型值
     * @return 处理结果
     */
    public MediaProviderProfile resolveMediaProfile(String requestedModel) {
        ConfigSnapshot current = snapshot();
        ResolvedModel resolvedModel = resolveConfiguredModel(current, trimToEmpty(requestedModel));
        String kind = firstNonBlank(stringValue(resolvedModel.section().get("kind")), "").toLowerCase(Locale.ROOT);
        return resolveMediaProfile(requestedModel, kind, current, null);
    }

    /**
     * 统一解析媒体Profile。
     * @param requestedModel requested模型值
     * @param userId 用户ID值
     * @return 处理结果
     */
    public MediaProviderProfile resolveMediaProfile(String requestedModel, Long userId) {
        ConfigSnapshot current = snapshot();
        ResolvedModel resolvedModel = resolveConfiguredModel(current, trimToEmpty(requestedModel));
        String kind = firstNonBlank(stringValue(resolvedModel.section().get("kind")), "").toLowerCase(Locale.ROOT);
        return resolveMediaProfile(requestedModel, kind, current, userId);
    }

    private MediaProviderProfile resolveMediaProfile(String requestedModel, String expectedKind, ConfigSnapshot current, Long userId) {
        boolean userScoped = userId != null;
        String modelName = trimToEmpty(requestedModel);
        String normalizedExpectedKind = trimToEmpty(expectedKind).toLowerCase(Locale.ROOT);
        if (modelName.isBlank()) {
            return emptyMediaProfile(
                normalizedExpectedKind,
                intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
                current.source()
            );
        }
        ResolvedModel resolvedModel = resolveConfiguredModel(current, modelName);
        String modelSection = resolvedModel.sectionPath();
        Map<String, Object> modelValues = resolvedModel.section();
        String actualKind = firstNonBlank(stringValue(modelValues.get("kind")), normalizedExpectedKind).toLowerCase(Locale.ROOT);
        String provider = firstNonBlank(stringValue(modelValues.get("provider")), "");
        String providerSection = "model.providers." + provider;
        String vendor = firstNonBlank(stringValue(modelValues.get("vendor")), current.value(providerSection, "vendor"));
        String baseUrl = normalizeBaseUrl(firstNonBlank(
            providerProperty(provider, "BASE_URL"),
            providerProperty(provider, "ENDPOINT"),
            current.value(providerSection, "base_url")
        ));
        String taskBaseUrl = normalizeBaseUrl(firstNonBlank(
            providerProperty(provider, "TASK_BASE_URL"),
            current.value(providerSection + ".extras", "task_base_url")
        ));
        String apiKey = resolveApiKey(current, userId, provider, vendor, providerSection);
        String source = resolveConfigSource(userScoped, apiKey, provider, vendor, current.source(), false);
        return new MediaProviderProfile(
            new MediaProviderConfig(
                actualKind,
                modelName,
                provider,
                configuredProviderModel(modelName, resolvedModel),
                apiKey,
                baseUrl,
                taskBaseUrl,
                intValue(
                    firstNonBlank(
                        providerProperty(provider, "TIMEOUT_SECONDS"),
                        current.value(modelSection, "timeout_seconds"),
                        current.value(providerSection + ".extras", "timeout_seconds"),
                        current.value("model", "timeout_seconds"),
                        "120"
                    ),
                    120
                ),
                source
            ),
            new MediaProviderCapabilities(
                boolValue(stringValue(modelValues.get("supports_seed"))),
                boolValue(current.value(providerSection + ".extras", "prompt_extend")),
                boolValue(current.value(providerSection + ".extras", "camera_fixed")),
                resolveWatermarkDefault(actualKind, current.value(providerSection + ".extras", "watermark")),
                intValue(
                    firstNonBlank(
                        current.value(providerSection + ".extras", "poll_interval_seconds"),
                        GenerationModelKinds.VIDEO.equals(actualKind) ? "8" : "5"
                    ),
                    GenerationModelKinds.VIDEO.equals(actualKind) ? 8 : 5
                ),
                intValue(
                    firstNonBlank(
                        current.value(providerSection + ".extras", "poll_timeout_seconds"),
                        GenerationModelKinds.VIDEO.equals(actualKind) ? "600" : "120"
                    ),
                    GenerationModelKinds.VIDEO.equals(actualKind) ? 600 : 120
	                ),
	                firstNonBlank(stringValue(modelValues.get("generation_mode")), GenerationModelKinds.VIDEO.equals(actualKind) ? "i2v" : ""),
	                parseStringList(modelValues.get("supported_sizes")),
	                parseIntegerList(modelValues.get("supported_durations")),
	                boolValue(stringValue(modelValues.get("supports_image_data_uri_references")))
	            )
	        );
	    }

    /**
     * 处理快照。
     * @return 处理结果
     */
    private ConfigSnapshot snapshot() {
        long now = System.currentTimeMillis();
        CachedSnapshot current = cachedSnapshot;
        if (cacheStillValid(current, now)) {
            return current.snapshot();
        }
        synchronized (this) {
            CachedSnapshot latest = cachedSnapshot;
            if (cacheStillValid(latest, now)) {
                return latest.snapshot();
            }
            GenerationConfigPathLocator.LocatedConfig locatedConfig = configPathLocator.locateAppConfig();
            Path secretsConfigPath = configPathLocator.resolveSecretsConfigPath();
            ConfigSnapshot loaded = loadSnapshot(locatedConfig, secretsConfigPath);
            cachedSnapshot = new CachedSnapshot(loaded, now);
            return loaded;
        }
    }

    /**
     * 加载快照。
     * @param locatedConfig located配置值
     * @return 处理结果
     */
    private ConfigSnapshot loadSnapshot(GenerationConfigPathLocator.LocatedConfig locatedConfig, Path secretsConfigPath) {
        List<Path> configFiles = locatedConfig.configFiles();
        if (configFiles == null || configFiles.isEmpty()) {
            String message = "Generation config directory missing: " + locatedConfig.detail();
            log.warn(message);
            return failOrSnapshot(Map.of(), locatedConfig.source(), message, null);
        }
        try {
            String source = configFiles.stream()
                .map(path -> "file:" + path.toAbsolutePath().normalize())
                .collect(Collectors.joining(" + "));
            if (secretsConfigPath != null && Files.exists(secretsConfigPath)) {
                source = source + " + file:" + secretsConfigPath.toAbsolutePath().normalize();
            }
            return new ConfigSnapshot(
                loadConfigTree(configFiles, secretsConfigPath),
                source,
                List.of()
            );
        } catch (RuntimeException ex) {
            String message = "Failed to load generation config from " + locatedConfig.source() + ": " + ex.getMessage();
            log.error(message, ex);
            return failOrSnapshot(Map.of(), "error:" + locatedConfig.source(), message, ex);
        }
    }

    /**
     * 将Or快照标记为失败。
     * @param root root值
     * @param source 来源值
     * @param message 消息文本
     * @param cause cause值
     * @return 处理结果
     */
    private ConfigSnapshot failOrSnapshot(
        Map<String, Object> root,
        String source,
        String message,
        RuntimeException cause
    ) {
        if (failFastOnConfigError) {
            if (cause == null) {
                throw new GenerationConfigurationException(message);
            }
            throw new GenerationConfigurationException(message + " (cause=" + cause.getClass().getSimpleName() + ")");
        }
        return new ConfigSnapshot(root, source, List.of(message));
    }

    /**
     * 检查是否cacheStillValid。
     * @param cached cached值
     * @param now 当前值
     * @return 是否满足条件
     */
    private boolean cacheStillValid(CachedSnapshot cached, long now) {
        if (!cacheEnabled() || cached == null) {
            return false;
        }
        return now - cached.loadedAtMillis() < cacheTtlMillis;
    }

    /**
     * 检查是否cacheEnabled。
     * @return 是否满足条件
     */
    private boolean cacheEnabled() {
        return cacheTtlMillis > 0L;
    }

    /**
     * 加载配置Tree。
     * @param configPaths 配置路径值
     * @return 处理结果
     */
    private Map<String, Object> loadConfigTree(List<Path> configPaths, Path secretsConfigPath) {
        Map<String, Object> base = new LinkedHashMap<>();
        for (Path configPath : configPaths) {
            base = mergeMaps(base, loadYamlTree(configPath));
        }
        if (secretsConfigPath == null || !Files.isRegularFile(secretsConfigPath)) {
            return base;
        }
        return mergeMaps(base, loadYamlTree(secretsConfigPath));
    }

    /**
     * 加载YamlTree。
     * @param configPath 配置路径值
     * @return 处理结果
     */
    private Map<String, Object> loadYamlTree(Path configPath) {
        YamlMapFactoryBean factory = new YamlMapFactoryBean();
        factory.setResources(new FileSystemResource(configPath.toFile()));
        factory.afterPropertiesSet();
        Map<String, Object> loaded = factory.getObject();
        return loaded == null ? Map.of() : normalizeMap(loaded);
    }

    private Map<String, Object> mergeMaps(Map<String, Object> base, Map<String, Object> override) {
        Map<String, Object> merged = new LinkedHashMap<>(base);
        for (Map.Entry<String, Object> entry : override.entrySet()) {
            Object currentValue = merged.get(entry.getKey());
            Object overrideValue = entry.getValue();
            if (currentValue instanceof Map<?, ?> currentMap && overrideValue instanceof Map<?, ?> overrideMap) {
                merged.put(entry.getKey(), mergeMaps(normalizeMap(currentMap), normalizeMap(overrideMap)));
                continue;
            }
            merged.put(entry.getKey(), overrideValue);
        }
        return merged;
    }

    /**
     * 处理property。
     * @param key key值
     * @return 处理结果
     */
    private String property(String key) {
        String value = environment.getProperty(key);
        return value == null ? "" : value.trim();
    }

    private String providerProperty(String provider, String suffix) {
        return scopedProperty(provider, suffix);
    }

    private String vendorProperty(String vendor, String suffix) {
        return scopedProperty(vendor, suffix);
    }

    private String scopedProperty(String scope, String suffix) {
        String normalizedScope = trimToEmpty(scope).toUpperCase(Locale.ROOT).replaceAll("[^A-Z0-9]+", "_");
        if (normalizedScope.isBlank()) {
            return "";
        }
        return property("JIANDOU_MODEL_" + normalizedScope + "_" + suffix);
    }

    private String resolveApiKey(
        ConfigSnapshot current,
        Long userId,
        String provider,
        String vendor,
        String providerSection
    ) {
        if (userId != null) {
            return resolveUserApiKey(current, userId, provider, vendor);
        }
        return firstNonBlank(
            property("JIANDOU_MODEL_API_KEY"),
            providerProperty(provider, "API_KEY"),
            vendorProperty(vendor, "API_KEY"),
            vendor.isBlank() ? "" : current.value("model.providers." + vendor, "api_key"),
            current.value(providerSection, "api_key"),
            resolveSharedConfiguredApiKey(current, provider, vendor),
            ""
        );
    }

    private String resolveUserApiKey(ConfigSnapshot current, Long userId, String provider, String vendor) {
        if (userId == null || credentialProvider == null) {
            return "";
        }
        return trimToEmpty(credentialProvider.findRuntimeApiKey(userId, preferredApiKeyScopes(current, provider, vendor)));
    }

    private List<String> preferredApiKeyScopes(ConfigSnapshot current, String provider, String vendor) {
        List<String> scopes = new ArrayList<>();
        addApiKeyScope(scopes, provider);
        addApiKeyScope(scopes, vendor);
        for (String siblingProvider : sameVendorProviderKeys(current, provider, vendor)) {
            addApiKeyScope(scopes, siblingProvider);
        }
        return List.copyOf(scopes);
    }

    private String resolveSharedConfiguredApiKey(ConfigSnapshot current, String provider, String vendor) {
        for (String siblingProvider : sameVendorProviderKeys(current, provider, vendor)) {
            String apiKey = current.value("model.providers." + siblingProvider, "api_key");
            if (!apiKey.isBlank()) {
                return apiKey;
            }
        }
        return "";
    }

    private List<String> sameVendorProviderKeys(ConfigSnapshot current, String provider, String vendor) {
        String normalizedVendor = normalize(vendor);
        if (normalizedVendor.isBlank()) {
            return List.of();
        }
        List<String> providerKeys = new ArrayList<>();
        for (ConfigSection section : current.listSections("model.providers")) {
            String sectionVendor = firstNonBlank(section.values().get("vendor"));
            if (!normalizedVendor.equals(normalize(sectionVendor))) {
                continue;
            }
            addApiKeyScope(providerKeys, section.name());
            addApiKeyScope(providerKeys, section.values().get("provider"));
        }
        providerKeys.removeIf(candidate -> normalize(candidate).equals(normalize(provider)));
        return List.copyOf(providerKeys);
    }

    private void addApiKeyScope(List<String> scopes, String candidate) {
        String normalizedCandidate = trimToEmpty(candidate);
        if (!normalizedCandidate.isBlank() && scopes.stream().noneMatch(item -> normalize(item).equals(normalize(normalizedCandidate)))) {
            scopes.add(normalizedCandidate);
        }
    }

    private String resolveConfigSource(
        boolean userScoped,
        String apiKey,
        String provider,
        String vendor,
        String defaultSource,
        boolean providerOverridden
    ) {
        if (userScoped) {
            return apiKey.isBlank() ? defaultSource : "user-db";
        }
        if (
            !property("JIANDOU_MODEL_API_KEY").isBlank()
                || !providerProperty(provider, "API_KEY").isBlank()
                || !vendorProperty(vendor, "API_KEY").isBlank()
                || !property("JIANDOU_MODEL_BASE_URL").isBlank()
                || !providerProperty(provider, "BASE_URL").isBlank()
                || !providerProperty(provider, "TASK_BASE_URL").isBlank()
                || providerOverridden
        ) {
            return "env";
        }
        return defaultSource;
    }

    /**
     * 处理deriveBaseURLFromHost。
     * @param host host值
     * @return 处理结果
     */
    private String deriveBaseUrlFromHost(String host) {
        String value = trimToEmpty(host);
        if (value.isBlank()) {
            return "";
        }
        if (value.startsWith("http://") || value.startsWith("https://")) {
            return normalizeBaseUrl(value);
        }
        return "https://" + value + "/v1";
    }

    /**
     * 规范化BaseURL。
     * @param raw 原始值
     * @return 处理结果
     */
    private String normalizeBaseUrl(String raw) {
        String value = trimToEmpty(raw);
        if (value.isBlank()) {
            return "";
        }
        String normalized = value.replaceAll("/+$", "");
        if (normalized.endsWith("/responses")) {
            return normalized.substring(0, normalized.length() - "/responses".length());
        }
        if (normalized.endsWith("/chat/completions")) {
            return normalized.substring(0, normalized.length() - "/chat/completions".length());
        }
        return normalized;
    }

    private MediaProviderProfile emptyMediaProfile(String kind, int timeoutSeconds, String source) {
        boolean video = GenerationModelKinds.VIDEO.equals(kind);
        return new MediaProviderProfile(
            new MediaProviderConfig(
                kind,
                "",
                "",
                "",
                "",
                "",
                "",
                timeoutSeconds,
                source
            ),
            new MediaProviderCapabilities(
                false,
                false,
                false,
                !video,
	                video ? 8 : 5,
	                video ? 600 : 120,
	                video ? "i2v" : "",
	                List.of(),
	                List.of(),
	                false
	            )
	        );
	    }

    private boolean resolveWatermarkDefault(String kind, String configuredWatermark) {
        if (!configuredWatermark.isBlank()) {
            return boolValue(configuredWatermark);
        }
        return !GenerationModelKinds.IMAGE.equals(kind);
    }

    private ResolvedModel resolveConfiguredModel(ConfigSnapshot current, String requestedModel) {
        String normalizedRequestedModel = trimToEmpty(requestedModel);
        if (normalizedRequestedModel.isBlank()) {
            return new ResolvedModel("", Map.of());
        }
        Map<String, Object> models = current.map("model.models");
        Object direct = models.get(normalizedRequestedModel);
        if (direct instanceof Map<?, ?> directSection) {
            return new ResolvedModel(normalizedRequestedModel, normalizeMap(directSection));
        }
        return new ResolvedModel(normalizedRequestedModel, Map.of());
    }

    private String configuredProviderModel(String requestedModel, ResolvedModel resolvedModel) {
        return firstNonBlank(
            stringValue(resolvedModel.section().get("provider_model")),
            resolvedModel.canonicalName(),
            trimToEmpty(requestedModel)
        );
    }

    private List<String> parseStringList(Object raw) {
        String value = stringValue(raw);
        if (value.isBlank()) {
            return List.of();
        }
        return java.util.Arrays.stream(value.split(","))
            .map(String::trim)
            .filter(item -> !item.isBlank())
            .distinct()
            .toList();
    }

    private List<Integer> parseIntegerList(Object raw) {
        String value = stringValue(raw);
        if (value.isBlank()) {
            return List.of();
        }
        List<Integer> items = new ArrayList<>();
        for (String item : value.split(",")) {
            int parsed = intValue(item, -1);
            if (parsed > 0 && !items.contains(parsed)) {
                items.add(parsed);
            }
        }
        return List.copyOf(items);
    }

    private boolean resolveTextSupportsResponsesApi(
        ConfigSnapshot current,
        String providerSection,
        String provider,
        String baseUrl
    ) {
        String configured = current.value(providerSection + ".extras", "use_responses_api");
        if (!configured.isBlank()) {
            return boolValue(configured);
        }
        return supportsResponsesApiByDefault(provider, baseUrl);
    }

    private boolean supportsResponsesApiByDefault(String provider, String baseUrl) {
        String normalizedProvider = trimToEmpty(provider).toLowerCase(Locale.ROOT);
        String normalizedBaseUrl = trimToEmpty(baseUrl).toLowerCase(Locale.ROOT);
        return "openai".equals(normalizedProvider)
            || normalizedProvider.contains("ark")
            || normalizedProvider.contains("volc")
            || normalizedBaseUrl.contains("openai.com")
            || normalizedBaseUrl.contains("volces.com/api/v3");
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    /**
     * 处理trim转为Empty。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private String normalize(String value) {
        return trimToEmpty(value).toLowerCase(Locale.ROOT);
    }

    /**
     * 处理int值。
     * @param raw 原始值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private int intValue(String raw, int fallback) {
        try {
            return Integer.parseInt(raw.trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    /**
     * 处理double值。
     * @param raw 原始值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private double doubleValue(String raw, double fallback) {
        try {
            return Double.parseDouble(raw.trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    /**
     * 检查是否布尔值。
     * @param raw 原始值
     * @return 是否满足条件
     */
    private boolean boolValue(String raw) {
        String normalized = trimToEmpty(raw).toLowerCase(Locale.ROOT);
        return "1".equals(normalized) || "true".equals(normalized) || "yes".equals(normalized) || "on".equals(normalized);
    }

    /**
     * 处理解析CacheTtlMillis。
     * @return 处理结果
     */
    private long resolveCacheTtlMillis() {
        int seconds = intValue(
            firstNonBlank(
                property("JIANDOU_CONFIG_CACHE_TTL_SECONDS"),
                property("jiandou.config.cache-ttl-seconds"),
                property("JIANDOU_CONFIG_REFRESH_SECONDS"),
                property("jiandou.config.refresh-seconds"),
                "5"
            ),
            5
        );
        if (seconds < 0) {
            seconds = 0;
        }
        if (seconds > 3600) {
            seconds = 3600;
        }
        return seconds * 1000L;
    }

    /**
     * 检查是否解析配置失败Fast。
     * @return 是否满足条件
     */
    private boolean resolveConfigFailFast() {
        String modelLevel = firstNonBlank(
            property("JIANDOU_MODEL_CONFIG_FAIL_FAST"),
            property("jiandou.model.config.fail-fast")
        );
        if (!modelLevel.isBlank()) {
            return boolValue(modelLevel);
        }
        return boolValue(firstNonBlank(
            property("JIANDOU_CONFIG_FAIL_FAST"),
            property("jiandou.config.fail-fast"),
            "false"
        ));
    }

    /**
     * 规范化Map。
     * @param source 来源值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> normalizeMap(Map<?, ?> source) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            normalized.put(String.valueOf(entry.getKey()), normalizeValue(entry.getValue()));
        }
        return normalized;
    }

    /**
     * 规范化值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private static Object normalizeValue(Object value) {
        if (value instanceof Map<?, ?> mapValue) {
            return normalizeMap(mapValue);
        }
        if (value instanceof List<?> listValue) {
            List<Object> normalized = new ArrayList<>(listValue.size());
            for (Object item : listValue) {
                normalized.add(normalizeValue(item));
            }
            return normalized;
        }
        return value;
    }

    /**
     * 解析路径。
     * @param rawPath 原始路径值
     * @return 处理结果
     */
    private static List<String> parsePath(String rawPath) {
        String value = rawPath == null ? "" : rawPath.trim();
        if (value.isBlank()) {
            return List.of();
        }
        List<String> tokens = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        char quote = 0;
        for (int index = 0; index < value.length(); index++) {
            char item = value.charAt(index);
            if ((item == '"' || item == '\'') && quote == 0) {
                quote = item;
                continue;
            }
            if (item == quote) {
                quote = 0;
                continue;
            }
            if (item == '.' && quote == 0) {
                addToken(tokens, current);
                continue;
            }
            current.append(item);
        }
        addToken(tokens, current);
        return tokens;
    }

    /**
     * 处理addToken。
     * @param tokens tokens值
     * @param current current值
     */
    private static void addToken(List<String> tokens, StringBuilder current) {
        String token = current.toString().trim();
        current.setLength(0);
        if (!token.isBlank()) {
            tokens.add(token);
        }
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private static String stringValue(Object value) {
        if (value == null) {
            return "";
        }
        if (value instanceof List<?> listValue) {
            return listValue.stream()
                .map(ModelRuntimePropertiesResolver::stringValue)
                .filter(item -> !item.isBlank())
                .collect(Collectors.joining(","));
        }
        return String.valueOf(value).trim();
    }

    /**
     * 处理配置快照。
     * @param root root值
     * @param source 来源值
     * @param errors errors值
     * @return 处理结果
     */
    private record ConfigSnapshot(Map<String, Object> root, String source, List<String> errors) {

        /**
         * 处理值。
         * @param sectionName sectionName值
         * @param key key值
         * @return 处理结果
         */
        private String value(String sectionName, String key) {
            Object value = pathValue(sectionName + "." + key);
            return stringValue(value);
        }

        /**
         * 处理section。
         * @param sectionName sectionName值
         * @return 处理结果
         */
        private Map<String, String> section(String sectionName) {
            Object value = pathValue(sectionName);
            if (!(value instanceof Map<?, ?> mapValue)) {
                return Map.of();
            }
            Map<String, String> section = new LinkedHashMap<>();
            for (Map.Entry<String, Object> entry : normalizeMap(mapValue).entrySet()) {
                section.put(entry.getKey(), stringValue(entry.getValue()));
            }
            return section;
        }

        /**
         * 列出Sections。
         * @param prefix prefix值
         * @return 处理结果
         */
        private List<ConfigSection> listSections(String prefix) {
            Object value = pathValue(prefix);
            if (!(value instanceof Map<?, ?> mapValue)) {
                return List.of();
            }
            List<ConfigSection> sections = new ArrayList<>();
            for (Map.Entry<String, Object> entry : normalizeMap(mapValue).entrySet()) {
                if (!(entry.getValue() instanceof Map<?, ?> childMap)) {
                    continue;
                }
                Map<String, String> values = new LinkedHashMap<>();
                for (Map.Entry<String, Object> child : normalizeMap(childMap).entrySet()) {
                    values.put(child.getKey(), stringValue(child.getValue()));
                }
                sections.add(new ConfigSection(entry.getKey(), values));
            }
            return sections;
        }

        /**
         * 映射map。
         * @param path 路径值
         * @return 处理结果
         */
        private Map<String, Object> map(String path) {
            Object value = pathValue(path);
            if (value instanceof Map<?, ?> mapValue) {
                return normalizeMap(mapValue);
            }
            return Map.of();
        }

        /**
         * 处理路径值。
         * @param path 路径值
         * @return 处理结果
         */
        private Object pathValue(String path) {
            Object current = root;
            for (String token : parsePath(path)) {
                if (!(current instanceof Map<?, ?> mapValue)) {
                    return null;
                }
                current = normalizeMap(mapValue).get(token);
                if (current == null) {
                    return null;
                }
            }
            return current;
        }
    }

    /**
     * 处理Cached快照。
     * @param snapshot 快照值
     * @param loadedAtMillis loadedAtMillis值
     * @return 处理结果
     */
    private record CachedSnapshot(
        ConfigSnapshot snapshot,
        long loadedAtMillis
    ) {}

    private record ResolvedModel(
        String canonicalName,
        Map<String, Object> section
    ) {
        private String sectionPath() {
            if (canonicalName == null || canonicalName.isBlank()) {
                return "";
            }
            return "model.models.\"" + canonicalName + "\"";
        }
    }

    /**
     * 处理配置Section。
     * @param name name值
     * @param values 值
     * @return 处理结果
     */
    public record ConfigSection(String name, Map<String, String> values) {}
}
