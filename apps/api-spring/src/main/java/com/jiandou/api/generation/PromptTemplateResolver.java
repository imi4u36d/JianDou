package com.jiandou.api.generation;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.config.YamlMapFactoryBean;
import org.springframework.core.env.Environment;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

@Service
public class PromptTemplateResolver {

    private static final Logger log = LoggerFactory.getLogger(PromptTemplateResolver.class);

    private final Environment environment;
    private final ModelRuntimePropertiesResolver modelRuntimePropertiesResolver;
    private final GenerationConfigPathLocator configPathLocator;
    private final boolean failFastOnPromptError;
    private volatile PromptDiagnostics diagnostics = PromptDiagnostics.empty();

    public PromptTemplateResolver(
        Environment environment,
        ModelRuntimePropertiesResolver modelRuntimePropertiesResolver,
        GenerationConfigPathLocator configPathLocator
    ) {
        this.environment = environment;
        this.modelRuntimePropertiesResolver = modelRuntimePropertiesResolver;
        this.configPathLocator = configPathLocator;
        this.failFastOnPromptError = resolvePromptFailFast();
    }

    public String systemPrompt(String promptName, String key) {
        Path promptFile = locatePromptFile(promptName);
        if (promptFile == null || !Files.exists(promptFile)) {
            return failOrEmpty(
                "Prompt file not found for promptName=" + promptName + " key=" + key + " source=" + modelRuntimePropertiesResolver.configSource(),
                null
            );
        }
        try {
            String resolved = loadYamlPrompt(promptFile, key);
            diagnostics = PromptDiagnostics.empty();
            return resolved;
        } catch (RuntimeException ex) {
            return failOrEmpty(
                "Failed to load prompt template from file=" + promptFile.toAbsolutePath().normalize() + " key=" + key + ": " + ex.getMessage(),
                ex
            );
        }
    }

    public List<String> promptErrors() {
        return diagnostics.errors();
    }

    private Path locatePromptFile(String promptName) {
        String promptDirectory = firstNonBlank(
            property("JIANDOU_PROMPT_DIR"),
            property("jiandou.prompt.dir"),
            modelRuntimePropertiesResolver.value("prompt", "file", "config/prompts")
        );
        Path base = configPathLocator.resolvePath(promptDirectory);
        if (base == null) {
            failOrEmpty("Prompt directory cannot be resolved: " + promptDirectory, null);
            return null;
        }
        Path yml = base.resolve(promptName + ".yml").toAbsolutePath().normalize();
        if (Files.exists(yml)) {
            return yml;
        }
        Path yaml = base.resolve(promptName + ".yaml").toAbsolutePath().normalize();
        if (Files.exists(yaml)) {
            return yaml;
        }
        return null;
    }

    private String loadYamlPrompt(Path promptFile, String key) {
        YamlMapFactoryBean factory = new YamlMapFactoryBean();
        factory.setResources(new FileSystemResource(promptFile.toFile()));
        factory.afterPropertiesSet();
        Map<String, Object> loaded = factory.getObject();
        if (loaded == null) {
            throw new IllegalStateException("Prompt yaml is empty");
        }
        Object systemPrompts = normalizeMap(loaded).get("system_prompts");
        if (!(systemPrompts instanceof Map<?, ?> systemPromptMap)) {
            throw new IllegalStateException("Prompt yaml missing system_prompts section");
        }
        Object value = normalizeMap(systemPromptMap).get(key);
        if (value == null) {
            throw new IllegalStateException("Prompt key not found: " + key);
        }
        String text = String.valueOf(value).trim();
        if (text.isBlank()) {
            throw new IllegalStateException("Prompt key is blank: " + key);
        }
        return text;
    }

    private String failOrEmpty(String message, RuntimeException cause) {
        diagnostics = new PromptDiagnostics(List.of(message));
        if (cause == null) {
            log.warn(message);
        } else {
            log.error(message, cause);
        }
        if (failFastOnPromptError) {
            throw new GenerationConfigurationException(message);
        }
        return "";
    }

    private boolean resolvePromptFailFast() {
        String promptLevel = firstNonBlank(
            property("JIANDOU_PROMPT_FAIL_FAST"),
            property("jiandou.prompt.fail-fast")
        );
        if (!promptLevel.isBlank()) {
            return boolValue(promptLevel);
        }
        return boolValue(firstNonBlank(
            property("JIANDOU_CONFIG_FAIL_FAST"),
            property("jiandou.config.fail-fast"),
            "false"
        ));
    }

    private boolean boolValue(String raw) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase();
        return "1".equals(normalized) || "true".equals(normalized) || "yes".equals(normalized) || "on".equals(normalized);
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String property(String key) {
        String value = environment.getProperty(key);
        return value == null ? "" : value.trim();
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

    private record PromptDiagnostics(List<String> errors) {

        private static PromptDiagnostics empty() {
            return new PromptDiagnostics(List.of());
        }
    }
}
