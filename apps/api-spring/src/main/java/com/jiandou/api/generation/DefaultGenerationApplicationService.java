package com.jiandou.api.generation;

import com.jiandou.api.generation.application.GenerationApplicationService;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class DefaultGenerationApplicationService implements GenerationApplicationService {

    private final ConcurrentHashMap<String, Map<String, Object>> runs = new ConcurrentHashMap<>();
    private final LocalGenerationRunStore generationRunStore;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final GenerationCatalogService catalogService;
    private final GenerationRunFactory generationRunFactory;
    private final GenerationRunSupport support;

    public DefaultGenerationApplicationService(
        LocalGenerationRunStore generationRunStore,
        ModelRuntimePropertiesResolver modelResolver,
        GenerationCatalogService catalogService,
        GenerationRunFactory generationRunFactory,
        GenerationRunSupport support
    ) {
        this.generationRunStore = generationRunStore;
        this.modelResolver = modelResolver;
        this.catalogService = catalogService;
        this.generationRunFactory = generationRunFactory;
        this.support = support;
    }

    @Override
    public Map<String, Object> catalog() {
        return catalogService.catalog();
    }

    @Override
    public Map<String, Object> createRun(Map<String, Object> request) {
        String runId = "run_" + UUID.randomUUID().toString().replace("-", "");
        String kind = String.valueOf(request.getOrDefault("kind", "probe"));
        Map<String, Object> run = switch (kind.toLowerCase()) {
            case "probe" -> generationRunFactory.createProbeRun(runId, request);
            case "script" -> generationRunFactory.createScriptRun(runId, request);
            case "image" -> generationRunFactory.createImageRun(runId, request);
            case "video" -> generationRunFactory.createVideoRun(runId, request);
            default -> throw new UnsupportedGenerationKindException(kind);
        };
        runs.put(runId, run);
        persistRun(runId, run);
        return run;
    }

    @Override
    public List<Map<String, Object>> listRuns(int limit) {
        return generationRunStore.listRuns(limit);
    }

    @Override
    public Map<String, Object> getRun(String runId) {
        Map<String, Object> run = runs.get(runId);
        if (run == null) {
            run = generationRunStore.loadRun(runId);
        }
        if (run == null) {
            throw new GenerationRunNotFoundException(runId);
        }
        Map<String, Object> refreshed = generationRunFactory.refreshVideoRun(new LinkedHashMap<>(run));
        runs.put(runId, refreshed);
        persistRun(runId, refreshed);
        return refreshed;
    }

    @Override
    public Map<String, Object> usage() {
        List<Map<String, Object>> items = modelResolver.listModelsByKind("text").stream()
            .map(model -> {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("model", String.valueOf(model.getOrDefault("value", "")).trim());
                item.put("label", String.valueOf(model.getOrDefault("label", model.getOrDefault("value", ""))).trim());
                item.put("used", 0);
                item.put("unit", "count");
                item.put("remaining", 0);
                item.put("remainingUnit", "count");
                item.put("provider", String.valueOf(model.getOrDefault("provider", "")).trim());
                item.put("source", modelResolver.configSource());
                return item;
            })
            .toList();
        return Map.of(
            "items", items,
            "generatedAt", support.nowIso(),
            "updatedAt", support.nowIso()
        );
    }

    private void persistRun(String runId, Map<String, Object> run) {
        generationRunStore.persistRun(runId, run);
    }
}
