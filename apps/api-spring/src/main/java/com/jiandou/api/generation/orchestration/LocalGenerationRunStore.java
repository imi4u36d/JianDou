package com.jiandou.api.generation.orchestration;

import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.generation.exception.GenerationNotImplementedException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Stream;
import org.springframework.stereotype.Component;

/**
 * 本地生成运行存储。
 */
@Component
public final class LocalGenerationRunStore {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final Path generationRunsDir;
    private final ObjectMapper objectMapper;

    /**
     * 创建新的本地生成运行存储。
     */
    public LocalGenerationRunStore(
        JiandouStorageProperties storageProperties,
        ObjectMapper objectMapper
    ) {
        this.generationRunsDir = storageProperties.resolveGenerationRunsDir();
        this.objectMapper = objectMapper;
    }

    /**
     * 处理persist运行。
     * @param runId 运行标识值
     * @param run 运行值
     */
    public void persistRun(String runId, Map<String, Object> run) {
        try {
            Files.createDirectories(generationRunsDir.resolve(runId));
            Path output = generationRunsDir.resolve(runId).resolve("run.json");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(output.toFile(), run);
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run persistence failed: " + ex.getMessage());
        }
    }

    /**
     * 列出Runs。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    public List<Map<String, Object>> listRuns(int limit) {
        int resolvedLimit = Math.max(1, limit);
        try {
            if (!Files.exists(generationRunsDir)) {
                return List.of();
            }
            try (Stream<Path> paths = Files.list(generationRunsDir)) {
                return paths
                    .filter(Files::isDirectory)
                    .map(path -> loadRun(path.getFileName().toString()))
                    .filter(Objects::nonNull)
                    .sorted((left, right) -> String.valueOf(right.getOrDefault("updatedAt", ""))
                        .compareTo(String.valueOf(left.getOrDefault("updatedAt", ""))))
                    .limit(resolvedLimit)
                    .toList();
            }
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run list failed: " + ex.getMessage());
        }
    }

    /**
     * 加载运行。
     * @param runId 运行标识值
     * @return 处理结果
     */
    public Map<String, Object> loadRun(String runId) {
        try {
            Path input = generationRunsDir.resolve(runId).resolve("run.json");
            if (!Files.exists(input)) {
                return null;
            }
            return objectMapper.readValue(input.toFile(), MAP_TYPE);
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run load failed: " + ex.getMessage());
        }
    }
}
