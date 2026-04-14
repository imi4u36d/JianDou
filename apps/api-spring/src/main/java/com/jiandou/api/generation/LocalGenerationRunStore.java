package com.jiandou.api.generation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Stream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public final class LocalGenerationRunStore {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final Path generationRunsDir;
    private final ObjectMapper objectMapper;

    public LocalGenerationRunStore(
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot,
        ObjectMapper objectMapper
    ) {
        this.generationRunsDir = Paths.get(storageRoot).toAbsolutePath().normalize().resolve("gen").resolve("_runs");
        this.objectMapper = objectMapper;
    }

    public void persistRun(String runId, Map<String, Object> run) {
        try {
            Files.createDirectories(generationRunsDir.resolve(runId));
            Path output = generationRunsDir.resolve(runId).resolve("run.json");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(output.toFile(), run);
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run persistence failed: " + ex.getMessage());
        }
    }

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
