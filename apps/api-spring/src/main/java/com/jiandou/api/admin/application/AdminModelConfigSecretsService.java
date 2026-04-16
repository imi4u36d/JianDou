package com.jiandou.api.admin.application;

import com.jiandou.api.common.exception.ApiException;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import java.io.IOException;
import java.io.InputStream;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.yaml.snakeyaml.DumperOptions;
import org.yaml.snakeyaml.Yaml;

/**
 * 管理端模型密钥落盘服务。
 */
@Service
public class AdminModelConfigSecretsService {

    private final GenerationConfigPathLocator configPathLocator;

    /**
     * 创建新的模型密钥落盘服务。
     * @param configPathLocator 配置路径定位器值
     */
    public AdminModelConfigSecretsService(GenerationConfigPathLocator configPathLocator) {
        this.configPathLocator = configPathLocator;
    }

    /**
     * 保存 provider API Key 覆盖。
     * @param providerApiKeys provider 到 key 的映射值
     */
    public void saveApiKeys(Map<String, String> providerApiKeys) {
        Map<String, String> sanitized = sanitize(providerApiKeys);
        if (sanitized.isEmpty()) {
            return;
        }
        Path secretsPath = configPathLocator.resolveSecretsConfigPath();
        if (secretsPath == null) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "config_path_missing", "无法定位模型 secrets 配置文件路径");
        }
        try {
            Map<String, Object> root = loadExistingSecrets(secretsPath);
            Map<String, Object> model = ensureChildMap(root, "model");
            Map<String, Object> providers = ensureChildMap(model, "providers");
            for (Map.Entry<String, String> entry : sanitized.entrySet()) {
                Map<String, Object> provider = ensureChildMap(providers, entry.getKey());
                provider.put("api_key", entry.getValue());
            }
            writeSecrets(secretsPath, root);
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "config_write_failed", "写入模型 secrets 配置失败", ex);
        }
    }

    private Map<String, String> sanitize(Map<String, String> providerApiKeys) {
        if (providerApiKeys == null || providerApiKeys.isEmpty()) {
            return Map.of();
        }
        Map<String, String> sanitized = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : providerApiKeys.entrySet()) {
            String key = trimToEmpty(entry.getKey());
            String apiKey = trimToEmpty(entry.getValue());
            if (key.isBlank() || apiKey.isBlank()) {
                continue;
            }
            sanitized.put(key, apiKey);
        }
        return Map.copyOf(sanitized);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> loadExistingSecrets(Path secretsPath) throws IOException {
        if (secretsPath == null || !Files.isRegularFile(secretsPath)) {
            return new LinkedHashMap<>();
        }
        Yaml yaml = new Yaml();
        try (InputStream inputStream = Files.newInputStream(secretsPath)) {
            Object loaded = yaml.load(inputStream);
            if (loaded instanceof Map<?, ?> mapValue) {
                return normalizeMap(mapValue);
            }
            return new LinkedHashMap<>();
        } catch (RuntimeException ex) {
            throw new ApiException(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "config_parse_failed",
                "读取模型 secrets 配置失败: " + secretsPath.toAbsolutePath().normalize(),
                ex
            );
        }
    }

    private void writeSecrets(Path secretsPath, Map<String, Object> root) throws IOException {
        if (secretsPath.getParent() != null) {
            Files.createDirectories(secretsPath.getParent());
        }
        DumperOptions options = new DumperOptions();
        options.setDefaultFlowStyle(DumperOptions.FlowStyle.BLOCK);
        options.setPrettyFlow(true);
        options.setIndent(2);
        options.setIndicatorIndent(1);
        options.setDefaultScalarStyle(DumperOptions.ScalarStyle.DOUBLE_QUOTED);
        Yaml yaml = new Yaml(options);
        try (Writer writer = Files.newBufferedWriter(secretsPath, StandardCharsets.UTF_8)) {
            yaml.dump(root, writer);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> ensureChildMap(Map<String, Object> root, String key) {
        Object value = root.get(key);
        if (value instanceof Map<?, ?> mapValue) {
            Map<String, Object> normalized = normalizeMap(mapValue);
            root.put(key, normalized);
            return normalized;
        }
        Map<String, Object> child = new LinkedHashMap<>();
        root.put(key, child);
        return child;
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

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
