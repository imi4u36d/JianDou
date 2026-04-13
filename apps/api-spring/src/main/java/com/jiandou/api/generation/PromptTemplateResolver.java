package com.jiandou.api.generation;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.config.YamlMapFactoryBean;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

@Service
public class PromptTemplateResolver {

    private static final Pattern SECTION_PATTERN = Pattern.compile("^\\[(.+)]$");
    private static final Pattern ASSIGN_PATTERN = Pattern.compile("^([A-Za-z0-9_.\\-\"']+)\\s*=\\s*(.+)$");

    private final ModelRuntimePropertiesResolver modelRuntimePropertiesResolver;

    public PromptTemplateResolver(ModelRuntimePropertiesResolver modelRuntimePropertiesResolver) {
        this.modelRuntimePropertiesResolver = modelRuntimePropertiesResolver;
    }

    public String systemPrompt(String promptName, String key) {
        Path promptFile = locatePromptFile(promptName);
        if (promptFile == null || !Files.exists(promptFile)) {
            return "";
        }
        String lowerName = promptFile.getFileName().toString().toLowerCase(Locale.ROOT);
        try {
            if (lowerName.endsWith(".yml") || lowerName.endsWith(".yaml")) {
                return loadYamlPrompt(promptFile, key);
            }
            return loadTomlPrompt(promptFile, key);
        } catch (IOException ignored) {
            return "";
        }
    }

    private Path locatePromptFile(String promptName) {
        String promptDirectory = modelRuntimePropertiesResolver.value("prompt", "file", "config/prompts");
        Path current = Paths.get("").toAbsolutePath().normalize();
        for (int depth = 0; depth < 6 && current != null; depth++) {
            Path base = current.resolve(promptDirectory);
            Path yml = base.resolve(promptName + ".yml");
            if (Files.exists(yml)) {
                return yml;
            }
            Path yaml = base.resolve(promptName + ".yaml");
            if (Files.exists(yaml)) {
                return yaml;
            }
            Path toml = base.resolve(promptName + ".toml");
            if (Files.exists(toml)) {
                return toml;
            }
            current = current.getParent();
        }
        return null;
    }

    private String loadYamlPrompt(Path promptFile, String key) {
        YamlMapFactoryBean factory = new YamlMapFactoryBean();
        factory.setResources(new FileSystemResource(promptFile.toFile()));
        factory.afterPropertiesSet();
        Map<String, Object> loaded = factory.getObject();
        if (loaded == null) {
            return "";
        }
        Object systemPrompts = normalizeMap(loaded).get("system_prompts");
        if (!(systemPrompts instanceof Map<?, ?> systemPromptMap)) {
            return "";
        }
        Object value = normalizeMap(systemPromptMap).get(key);
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String loadTomlPrompt(Path promptFile, String key) throws IOException {
        boolean inSystemPrompts = false;
        for (String rawLine : Files.readAllLines(promptFile, StandardCharsets.UTF_8)) {
            String line = rawLine.trim();
            if (line.isBlank()) {
                continue;
            }
            Matcher sectionMatcher = SECTION_PATTERN.matcher(line);
            if (sectionMatcher.matches()) {
                inSystemPrompts = "system_prompts".equals(sectionMatcher.group(1).trim());
                continue;
            }
            if (!inSystemPrompts) {
                continue;
            }
            Matcher assignMatcher = ASSIGN_PATTERN.matcher(line);
            if (!assignMatcher.matches()) {
                continue;
            }
            String name = unquote(assignMatcher.group(1).trim());
            if (!key.equals(name)) {
                continue;
            }
            return parseTomlValue(assignMatcher.group(2).trim());
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> normalizeMap(Map<?, ?> source) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof Map<?, ?> mapValue) {
                normalized.put(String.valueOf(entry.getKey()), normalizeMap(mapValue));
                continue;
            }
            normalized.put(String.valueOf(entry.getKey()), value);
        }
        return normalized;
    }

    private String parseTomlValue(String value) {
        String trimmed = value.trim();
        if (trimmed.startsWith("\"\"\"") && trimmed.endsWith("\"\"\"") && trimmed.length() >= 6) {
            return trimmed.substring(3, trimmed.length() - 3).trim();
        }
        if (trimmed.length() >= 2) {
            if ((trimmed.startsWith("\"") && trimmed.endsWith("\"")) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
                return trimmed.substring(1, trimmed.length() - 1);
            }
        }
        return trimmed;
    }

    private String unquote(String raw) {
        String normalized = raw == null ? "" : raw.trim();
        if (normalized.length() >= 2
            && ((normalized.startsWith("\"") && normalized.endsWith("\"")) || (normalized.startsWith("'") && normalized.endsWith("'")))) {
            return normalized.substring(1, normalized.length() - 1).trim();
        }
        return normalized;
    }
}
