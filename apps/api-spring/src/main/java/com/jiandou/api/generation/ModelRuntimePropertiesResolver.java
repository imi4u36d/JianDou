package com.jiandou.api.generation;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.YamlMapFactoryBean;
import org.springframework.core.env.Environment;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

@Service
public class ModelRuntimePropertiesResolver {

    private static final Logger log = LoggerFactory.getLogger(ModelRuntimePropertiesResolver.class);

    private final Environment environment;
    private final GenerationConfigPathLocator configPathLocator;
    private final long cacheTtlMillis;
    private final boolean failFastOnConfigError;
    private volatile CachedSnapshot cachedSnapshot;

    public ModelRuntimePropertiesResolver(Environment environment) {
        this(environment, new GenerationConfigPathLocator(environment));
    }

    @Autowired
    public ModelRuntimePropertiesResolver(Environment environment, GenerationConfigPathLocator configPathLocator) {
        this.environment = environment;
        this.configPathLocator = configPathLocator;
        this.cacheTtlMillis = resolveCacheTtlMillis();
        this.failFastOnConfigError = resolveConfigFailFast();
    }

    public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
        ConfigSnapshot current = snapshot();
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return new ModelRuntimeProfile(
                "",
                "",
                "",
                "",
                "",
                intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
                doubleValue(firstNonBlank(current.value("model", "temperature"), "0.15"), 0.15),
                intValue(firstNonBlank(current.value("model", "max_tokens"), "2000"), 2000),
                current.source()
            );
        }
        String modelSection = "model.models.\"" + modelName + "\"";
        String provider = firstNonBlank(
            property("JIANDOU_MODEL_PROVIDER"),
            current.value(modelSection, "provider"),
            ""
        );
        String providerSection = "model.providers." + provider;
        String fallbackModel = firstNonBlank(
            property("JIANDOU_MODEL_FALLBACK"),
            current.value(modelSection, "fallback_model"),
            current.value(modelSection, "fallback"),
            ""
        );
        String apiKey = firstNonBlank(
            property("JIANDOU_MODEL_API_KEY"),
            current.value(providerSection, "api_key"),
            ""
        );
        String baseUrl = normalizeBaseUrl(firstNonBlank(
            property("JIANDOU_MODEL_BASE_URL"),
            property("JIANDOU_MODEL_ENDPOINT"),
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
        String source = current.source();
        if (!property("JIANDOU_MODEL_API_KEY").isBlank() || !property("JIANDOU_MODEL_BASE_URL").isBlank()) {
            source = "env";
        }
        return new ModelRuntimeProfile(
            provider,
            modelName,
            fallbackModel,
            apiKey,
            baseUrl,
            timeoutSeconds,
            temperature,
            maxTokens,
            source
        );
    }

    public String configSource() {
        return snapshot().source();
    }

    public List<String> configErrors() {
        return snapshot().errors();
    }

    public void refresh() {
        synchronized (this) {
            cachedSnapshot = null;
        }
    }

    public String value(String section, String key, String fallback) {
        return firstNonBlank(snapshot().value(section, key), fallback);
    }

    public int intValue(String section, String key, int fallback) {
        return intValue(snapshot().value(section, key), fallback);
    }

    public List<Map<String, Object>> listModelsByKind(String kind) {
        String targetKind = trimToEmpty(kind).toLowerCase(Locale.ROOT);
        if (targetKind.isBlank()) {
            return List.of();
        }
        Map<String, Object> models = snapshot().map("model.models");
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
            item.put("provider", trimToEmpty(stringValue(section.get("provider"))));
            item.put("family", trimToEmpty(stringValue(section.get("family"))));
            item.put("description", trimToEmpty(stringValue(section.get("description"))));
            item.put("kind", targetKind);
            String fallbackModel = firstNonBlank(stringValue(section.get("fallback_model")), stringValue(section.get("fallback")));
            if (!fallbackModel.isBlank()) {
                item.put("fallbackModel", fallbackModel);
            }
            item.put("supportsSeed", boolValue(stringValue(section.get("supports_seed"))));
            items.add(item);
        }
        return items;
    }

    public boolean supportsSeed(String requestedModel) {
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return false;
        }
        String modelSection = "model.models.\"" + modelName + "\"";
        return boolValue(snapshot().value(modelSection, "supports_seed"));
    }

    public Map<String, String> section(String sectionName) {
        return snapshot().section(sectionName);
    }

    public List<ConfigSection> listSections(String prefix) {
        return snapshot().listSections(prefix);
    }

    public MediaProviderProfile resolveImageProfile(String requestedModel) {
        ConfigSnapshot current = snapshot();
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return new MediaProviderProfile(
                "",
                "",
                "",
                "",
                "",
                intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
                5,
                120,
                false,
                false,
                true,
                current.source()
            );
        }
        String modelSection = "model.models.\"" + modelName + "\"";
        String provider = firstNonBlank(current.value(modelSection, "provider"), "");
        String providerSection = "model.providers." + provider;
        return new MediaProviderProfile(
            provider,
            modelName,
            current.value(providerSection, "api_key"),
            normalizeBaseUrl(current.value(providerSection, "base_url")),
            normalizeBaseUrl(current.value(providerSection + ".extras", "task_base_url")),
            intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
            5,
            120,
            false,
            false,
            true,
            current.source()
        );
    }

    public MediaProviderProfile resolveVideoProfile(String requestedModel) {
        ConfigSnapshot current = snapshot();
        String modelName = trimToEmpty(requestedModel);
        if (modelName.isBlank()) {
            return new MediaProviderProfile(
                "",
                "",
                "",
                "",
                "",
                intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
                intValue(firstNonBlank(current.value("model.providers.seedance.extras", "poll_interval_seconds"), "8"), 8),
                intValue(firstNonBlank(current.value("model.providers.seedance.extras", "poll_timeout_seconds"), "600"), 600),
                false,
                false,
                true,
                current.source()
            );
        }
        String modelSection = "model.models.\"" + modelName + "\"";
        String provider = firstNonBlank(current.value(modelSection, "provider"), "");
        String providerSection = "model.providers." + provider;
        String baseUrl = normalizeBaseUrl(current.value(providerSection, "base_url"));
        String taskBaseUrl = normalizeBaseUrl(firstNonBlank(
            current.value(providerSection + ".extras", "task_base_url"),
            provider.startsWith("wan") && !baseUrl.isBlank() ? deriveDashscopeTaskBaseUrl(baseUrl) : ""
        ));
        return new MediaProviderProfile(
            provider,
            modelName,
            current.value(providerSection, "api_key"),
            baseUrl,
            taskBaseUrl,
            intValue(firstNonBlank(current.value("model", "timeout_seconds"), "120"), 120),
            intValue(firstNonBlank(current.value(providerSection + ".extras", "poll_interval_seconds"), "8"), 8),
            intValue(firstNonBlank(current.value(providerSection + ".extras", "poll_timeout_seconds"), "600"), 600),
            boolValue(current.value(providerSection + ".extras", "prompt_extend")),
            boolValue(current.value(providerSection + ".extras", "camera_fixed")),
            !current.value(providerSection + ".extras", "watermark").isBlank()
                ? boolValue(current.value(providerSection + ".extras", "watermark"))
                : true,
            current.source()
        );
    }

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
            ConfigFileState fileState = ConfigFileState.from(locatedConfig.configFile());
            // Cache invalidates on TTL expiry, config path change, or file fingerprint change.
            if (cacheEnabled() && latest != null && latest.matches(fileState, locatedConfig.configFile())) {
                cachedSnapshot = latest.refresh(now);
                return latest.snapshot();
            }
            ConfigSnapshot loaded = loadSnapshot(locatedConfig);
            cachedSnapshot = new CachedSnapshot(loaded, locatedConfig.configFile(), fileState, now);
            return loaded;
        }
    }

    private ConfigSnapshot loadSnapshot(GenerationConfigPathLocator.LocatedConfig locatedConfig) {
        Path configPath = locatedConfig.configFile();
        if (configPath == null || !Files.exists(configPath)) {
            String message = "Generation config file missing: " + locatedConfig.detail();
            log.warn(message);
            return failOrSnapshot(Map.of(), locatedConfig.source(), message, null);
        }
        try {
            return new ConfigSnapshot(
                loadConfigTree(configPath),
                "file:" + configPath.toAbsolutePath().normalize(),
                List.of()
            );
        } catch (RuntimeException ex) {
            String message = "Failed to load generation config from " + configPath.toAbsolutePath().normalize() + ": " + ex.getMessage();
            log.error(message, ex);
            return failOrSnapshot(Map.of(), "error:" + configPath.toAbsolutePath().normalize(), message, ex);
        }
    }

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

    private boolean cacheStillValid(CachedSnapshot cached, long now) {
        if (!cacheEnabled() || cached == null) {
            return false;
        }
        return now - cached.loadedAtMillis() < cacheTtlMillis;
    }

    private boolean cacheEnabled() {
        return cacheTtlMillis > 0L;
    }

    private Map<String, Object> loadConfigTree(Path configPath) {
        return loadYamlTree(configPath);
    }

    private Map<String, Object> loadYamlTree(Path configPath) {
        YamlMapFactoryBean factory = new YamlMapFactoryBean();
        factory.setResources(new FileSystemResource(configPath.toFile()));
        factory.afterPropertiesSet();
        Map<String, Object> loaded = factory.getObject();
        return loaded == null ? Map.of() : normalizeMap(loaded);
    }

    private String property(String key) {
        String value = environment.getProperty(key);
        return value == null ? "" : value.trim();
    }

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

    private String deriveDashscopeTaskBaseUrl(String rawBaseUrl) {
        String normalized = normalizeBaseUrl(rawBaseUrl);
        if (normalized.isBlank()) {
            return "";
        }
        if (normalized.contains("/api/v1/tasks")) {
            return normalized;
        }
        int marker = normalized.indexOf("/api/v1/services/");
        if (marker > 0) {
            return normalized.substring(0, marker) + "/api/v1/tasks";
        }
        return normalized;
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private int intValue(String raw, int fallback) {
        try {
            return Integer.parseInt(raw.trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private double doubleValue(String raw, double fallback) {
        try {
            return Double.parseDouble(raw.trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private boolean boolValue(String raw) {
        String normalized = trimToEmpty(raw).toLowerCase(Locale.ROOT);
        return "1".equals(normalized) || "true".equals(normalized) || "yes".equals(normalized) || "on".equals(normalized);
    }

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

    @SuppressWarnings("unchecked")
    private static Map<String, Object> normalizeMap(Map<?, ?> source) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            normalized.put(String.valueOf(entry.getKey()), normalizeValue(entry.getValue()));
        }
        return normalized;
    }

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

    private static void addToken(List<String> tokens, StringBuilder current) {
        String token = current.toString().trim();
        current.setLength(0);
        if (!token.isBlank()) {
            tokens.add(token);
        }
    }

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

    private record ConfigSnapshot(Map<String, Object> root, String source, List<String> errors) {

        private String value(String sectionName, String key) {
            Object value = pathValue(sectionName + "." + key);
            return stringValue(value);
        }

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

        private Map<String, Object> map(String path) {
            Object value = pathValue(path);
            if (value instanceof Map<?, ?> mapValue) {
                return normalizeMap(mapValue);
            }
            return Map.of();
        }

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

    private record CachedSnapshot(
        ConfigSnapshot snapshot,
        Path configPath,
        ConfigFileState fileState,
        long loadedAtMillis
    ) {

        private CachedSnapshot refresh(long now) {
            return new CachedSnapshot(snapshot, configPath, fileState, now);
        }

        private boolean matches(ConfigFileState latestFileState, Path latestPath) {
            return Objects.equals(configPath, latestPath) && Objects.equals(fileState, latestFileState);
        }
    }

    private record ConfigFileState(boolean exists, long modifiedTime, long size) {

        private static ConfigFileState from(Path path) {
            if (path == null || !Files.exists(path)) {
                return new ConfigFileState(false, -1L, -1L);
            }
            try {
                return new ConfigFileState(
                    true,
                    Files.getLastModifiedTime(path).toMillis(),
                    Files.size(path)
                );
            } catch (Exception ex) {
                return new ConfigFileState(true, -1L, -1L);
            }
        }
    }

    public record ConfigSection(String name, Map<String, String> values) {}
}
