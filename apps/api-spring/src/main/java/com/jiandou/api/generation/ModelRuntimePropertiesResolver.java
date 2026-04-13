package com.jiandou.api.generation;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.springframework.beans.factory.config.YamlMapFactoryBean;
import org.springframework.core.env.Environment;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

@Service
public class ModelRuntimePropertiesResolver {

    private static final Pattern SECTION_PATTERN = Pattern.compile("^\\[(.+)]$");
    private static final Pattern ASSIGN_PATTERN = Pattern.compile("^([A-Za-z0-9_.\\-\"']+)\\s*=\\s*(.+)$");

    private final Environment environment;
    private volatile ConfigSnapshot snapshot;

    public ModelRuntimePropertiesResolver(Environment environment) {
        this.environment = environment;
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
            current.source()
        );
    }

    private ConfigSnapshot snapshot() {
        ConfigSnapshot current = snapshot;
        if (current != null) {
            return current;
        }
        synchronized (this) {
            if (snapshot == null) {
                snapshot = loadSnapshot();
            }
            return snapshot;
        }
    }

    private ConfigSnapshot loadSnapshot() {
        Path configPath = locateConfigFile();
        if (configPath == null || !Files.exists(configPath)) {
            return new ConfigSnapshot(Map.of(), "");
        }
        try {
            return new ConfigSnapshot(
                loadConfigTree(configPath),
                configPath.toAbsolutePath().normalize().toString()
            );
        } catch (IOException ignored) {
            return new ConfigSnapshot(Map.of(), "");
        }
    }

    private Map<String, Object> loadConfigTree(Path configPath) throws IOException {
        String lowerCaseName = configPath.getFileName().toString().toLowerCase(Locale.ROOT);
        if (lowerCaseName.endsWith(".yml") || lowerCaseName.endsWith(".yaml")) {
            return loadYamlTree(configPath);
        }
        return loadTomlTree(configPath);
    }

    private Path locateConfigFile() {
        Path current = Paths.get("").toAbsolutePath().normalize();
        for (int depth = 0; depth < 6 && current != null; depth++) {
            Path yaml = current.resolve("config").resolve("app.yml");
            if (Files.exists(yaml)) {
                return yaml;
            }
            Path yml = current.resolve("config").resolve("app.yaml");
            if (Files.exists(yml)) {
                return yml;
            }
            Path toml = current.resolve("config").resolve("app.toml");
            if (Files.exists(toml)) {
                return toml;
            }
            current = current.getParent();
        }
        return null;
    }

    private Map<String, Object> loadYamlTree(Path configPath) {
        YamlMapFactoryBean factory = new YamlMapFactoryBean();
        factory.setResources(new FileSystemResource(configPath.toFile()));
        factory.afterPropertiesSet();
        Map<String, Object> loaded = factory.getObject();
        return loaded == null ? Map.of() : normalizeMap(loaded);
    }

    private Map<String, Object> loadTomlTree(Path configPath) throws IOException {
        Map<String, Object> root = new LinkedHashMap<>();
        String currentSection = "";
        List<String> lines = Files.readAllLines(configPath, StandardCharsets.UTF_8);
        for (String rawLine : lines) {
            String line = stripInlineComment(rawLine).trim();
            if (line.isEmpty()) {
                continue;
            }
            Matcher sectionMatcher = SECTION_PATTERN.matcher(line);
            if (sectionMatcher.matches()) {
                currentSection = sectionMatcher.group(1).trim();
                continue;
            }
            Matcher assignMatcher = ASSIGN_PATTERN.matcher(line);
            if (!assignMatcher.matches()) {
                continue;
            }
            String key = unquote(assignMatcher.group(1).trim());
            String value = parseTomlValue(assignMatcher.group(2).trim());
            List<String> path = new ArrayList<>(parsePath(currentSection));
            path.add(key);
            putPathValue(root, path, value);
        }
        return root;
    }

    private String stripInlineComment(String rawLine) {
        boolean inDoubleQuotes = false;
        boolean inSingleQuotes = false;
        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < rawLine.length(); index++) {
            char current = rawLine.charAt(index);
            if (current == '"' && !inSingleQuotes) {
                inDoubleQuotes = !inDoubleQuotes;
            } else if (current == '\'' && !inDoubleQuotes) {
                inSingleQuotes = !inDoubleQuotes;
            } else if (current == '#' && !inDoubleQuotes && !inSingleQuotes) {
                break;
            }
            builder.append(current);
        }
        return builder.toString();
    }

    private String parseTomlValue(String value) {
        String trimmed = value.trim();
        if (trimmed.length() >= 2) {
            if ((trimmed.startsWith("\"") && trimmed.endsWith("\"")) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
                return trimmed.substring(1, trimmed.length() - 1);
            }
        }
        return trimmed;
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

    private static void putPathValue(Map<String, Object> root, List<String> path, Object value) {
        if (path.isEmpty()) {
            return;
        }
        Map<String, Object> current = root;
        for (int index = 0; index < path.size() - 1; index++) {
            String segment = path.get(index);
            Object child = current.get(segment);
            if (!(child instanceof Map<?, ?> childMap)) {
                Map<String, Object> created = new LinkedHashMap<>();
                current.put(segment, created);
                current = created;
                continue;
            }
            current = normalizeMap(childMap);
            rootPathAssign(root, path.subList(0, index + 1), current);
        }
        current.put(path.get(path.size() - 1), value);
    }

    private static void rootPathAssign(Map<String, Object> root, List<String> path, Map<String, Object> value) {
        Map<String, Object> current = root;
        for (int index = 0; index < path.size() - 1; index++) {
            current = castMap(current.get(path.get(index)));
        }
        current.put(path.get(path.size() - 1), value);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        if (value instanceof Map<?, ?> mapValue) {
            return (Map<String, Object>) mapValue;
        }
        return new LinkedHashMap<>();
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

    private static String unquote(String raw) {
        String normalized = raw == null ? "" : raw.trim();
        if (normalized.length() >= 2
            && ((normalized.startsWith("\"") && normalized.endsWith("\"")) || (normalized.startsWith("'") && normalized.endsWith("'")))) {
            return normalized.substring(1, normalized.length() - 1).trim();
        }
        return normalized;
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

    private record ConfigSnapshot(Map<String, Object> root, String source) {

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

    public record ConfigSection(String name, Map<String, String> values) {
    }
}
