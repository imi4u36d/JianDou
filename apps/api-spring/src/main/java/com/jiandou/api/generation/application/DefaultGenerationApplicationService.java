package com.jiandou.api.generation.application;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.GenerationRunKinds;
import com.jiandou.api.generation.exception.GenerationRunNotFoundException;
import com.jiandou.api.generation.exception.UnsupportedGenerationKindException;
import com.jiandou.api.generation.orchestration.GenerationRunFactory;
import com.jiandou.api.generation.orchestration.GenerationRunSupport;
import com.jiandou.api.generation.orchestration.LocalGenerationRunStore;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

/**
 * 默认生成应用服务。
 */
@Service
public class DefaultGenerationApplicationService implements GenerationApplicationService {

    private final ConcurrentHashMap<String, Map<String, Object>> runs = new ConcurrentHashMap<>();
    private final LocalGenerationRunStore generationRunStore;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final GenerationCatalogService catalogService;
    private final GenerationRunFactory generationRunFactory;
    private final GenerationRunSupport support;

    /**
     * 创建新的默认生成应用服务。
     * @param generationRunStore 生成运行存储值
     * @param modelResolver 模型解析器值
     * @param catalogService 目录服务值
     * @param generationRunFactory 生成运行工厂值
     * @param support 支持值
     */
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

    /**
     * 处理目录。
     * @return 处理结果
     */
    @Override
    public Map<String, Object> catalog() {
        return catalogService.catalog();
    }

    /**
     * 创建运行。
     * @param request 请求体
     * @return 处理结果
     */
    @Override
    public Map<String, Object> createRun(Map<String, Object> request) {
        String runId = "run_" + UUID.randomUUID().toString().replace("-", "");
        String kind = String.valueOf(request.getOrDefault("kind", GenerationRunKinds.PROBE));
        Map<String, Object> run = switch (kind.toLowerCase()) {
            case GenerationRunKinds.PROBE -> generationRunFactory.createProbeRun(runId, request);
            case GenerationRunKinds.SCRIPT -> generationRunFactory.createScriptRun(runId, request);
            case GenerationRunKinds.IMAGE -> generationRunFactory.createImageRun(runId, request);
            case GenerationRunKinds.VIDEO -> generationRunFactory.createVideoRun(runId, request);
            /**
             * 处理Unsupported生成类型异常。
             * @param kind 类型值
             * @return 处理结果
             */
            default -> throw new UnsupportedGenerationKindException(kind);
        };
        runs.put(runId, run);
        persistRun(runId, run);
        return run;
    }

    /**
     * 列出Runs。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    @Override
    public List<Map<String, Object>> listRuns(int limit) {
        return generationRunStore.listRuns(limit);
    }

    /**
     * 返回运行。
     * @param runId 运行标识值
     * @return 处理结果
     */
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

    /**
     * 处理usage。
     * @return 处理结果
     */
    @Override
    public Map<String, Object> usage() {
        List<Map<String, Object>> items = modelResolver.listModelsByKind(GenerationModelKinds.TEXT).stream()
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

    /**
     * 处理persist运行。
     * @param runId 运行标识值
     * @param run 运行值
     */
    private void persistRun(String runId, Map<String, Object> run) {
        generationRunStore.persistRun(runId, run);
    }
}
