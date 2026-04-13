package com.jiandou.api.health;

import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import com.jiandou.api.generation.MediaProviderProfile;
import com.jiandou.api.generation.ModelRuntimeProfile;
import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;

@Service
public class RuntimeDescriptorService {

    private final ModelRuntimePropertiesResolver modelResolver;
    private final String appName;
    private final String appEnv;
    private final String executionMode;
    private final String storageRoot;

    public RuntimeDescriptorService(
        ModelRuntimePropertiesResolver modelResolver,
        @Value("${spring.application.name:JianDou Spring API}") String appName,
        @Value("${JIANDOU_APP_ENV:dev}") String appEnv,
        @Value("${JIANDOU_EXECUTION_MODE:queue}") String executionMode,
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot
    ) {
        this.modelResolver = modelResolver;
        this.appName = appName;
        this.appEnv = appEnv;
        this.executionMode = executionMode;
        this.storageRoot = storageRoot;
    }

    public Map<String, Object> describeRuntime() {
        List<Map<String, Object>> textModels = modelResolver.listModelsByKind("text");
        List<Map<String, Object>> visionModels = modelResolver.listModelsByKind("vision");
        List<Map<String, Object>> imageModels = modelResolver.listModelsByKind("image");
        List<Map<String, Object>> videoModels = modelResolver.listModelsByKind("video");
        List<String> configErrors = new ArrayList<>();
        appendCatalogErrors(configErrors, textModels, "文本");
        appendCatalogErrors(configErrors, visionModels, "视觉");
        appendCatalogErrors(configErrors, imageModels, "关键帧");
        appendCatalogErrors(configErrors, videoModels, "视频");
        boolean hasReadyTextModel = hasReadyTextModel(textModels, configErrors);
        boolean hasReadyVisionModel = hasReadyTextModel(visionModels, configErrors);
        boolean hasReadyImageModel = hasReadyImageModel(imageModels, configErrors);
        boolean hasReadyVideoModel = hasReadyVideoModel(videoModels, configErrors);
        boolean ready = configErrors.isEmpty()
            && hasReadyTextModel
            && hasReadyVisionModel
            && hasReadyImageModel
            && hasReadyVideoModel;
        Map<String, Object> model = new LinkedHashMap<>();
        model.put("provider", "");
        model.put("primary_model", "");
        model.put("fallback_model", "");
        model.put("text_analysis_provider", "");
        model.put("text_analysis_model", "");
        model.put("vision_model", "");
        model.put("vision_fallback_model", "");
        model.put("endpoint_host", "");
        model.put("api_key_present", hasReadyTextModel || hasReadyVisionModel || hasReadyImageModel || hasReadyVideoModel);
        model.put("ready", ready);
        model.put("temperature", doubleValue(modelResolver.value("model", "temperature", "0.15"), 0.15));
        model.put("max_tokens", intValue(modelResolver.value("model", "max_tokens", "2000"), 2000));
        model.put("config_source", modelResolver.configSource());
        model.put("config_errors", configErrors.toArray(String[]::new));

        Map<String, Object> planning = new LinkedHashMap<>();
        planning.put("timed_transcript_supported", true);
        planning.put("transcript_semantic_planning", true);
        planning.put("visual_content_analysis", true);
        planning.put("visual_event_reasoning", true);
        planning.put("subtitle_visual_fusion", true);
        planning.put("audio_peak_signal", true);
        planning.put("scene_boundary_signal", true);
        planning.put("fusion_timeline_planning", true);
        planning.put("fallback_heuristic_enabled", false);

        Map<String, Object> runtime = new LinkedHashMap<>();
        runtime.put("name", appName);
        runtime.put("env", appEnv);
        runtime.put("execution_mode", executionMode);
        runtime.put("database_url", property("JIANDOU_DATABASE_URL", "jdbc:mysql://127.0.0.1:3306/ai_cut"));
        runtime.put("model_provider", "");
        runtime.put("storage_root", Paths.get(storageRoot).toAbsolutePath().normalize().toString());
        runtime.put("model", model);
        runtime.put("planning_capabilities", planning);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", true);
        payload.put("runtime", runtime);
        return payload;
    }

    private void appendCatalogErrors(List<String> errors, List<Map<String, Object>> models, String label) {
        if (models.isEmpty()) {
            errors.add("未配置可用" + label + "模型");
        }
    }

    private boolean hasReadyTextModel(List<Map<String, Object>> textModels, List<String> errors) {
        boolean ready = false;
        for (Map<String, Object> model : textModels) {
            String modelName = String.valueOf(model.getOrDefault("value", "")).trim();
            if (modelName.isBlank()) {
                continue;
            }
            ModelRuntimeProfile profile = modelResolver.resolveTextProfile(modelName);
            if (profile.ready()) {
                ready = true;
                continue;
            }
            errors.add("模型 " + modelName + " 缺少 api_key 或 base_url");
        }
        return ready;
    }

    private boolean hasReadyImageModel(List<Map<String, Object>> imageModels, List<String> errors) {
        boolean ready = false;
        for (Map<String, Object> model : imageModels) {
            String modelName = String.valueOf(model.getOrDefault("value", "")).trim();
            if (modelName.isBlank()) {
                continue;
            }
            MediaProviderProfile profile = modelResolver.resolveImageProfile(modelName);
            if (profile.ready()) {
                ready = true;
                continue;
            }
            errors.add("模型 " + modelName + " 缺少 api_key 或 base_url");
        }
        return ready;
    }

    private boolean hasReadyVideoModel(List<Map<String, Object>> videoModels, List<String> errors) {
        boolean ready = false;
        for (Map<String, Object> model : videoModels) {
            String modelName = String.valueOf(model.getOrDefault("value", "")).trim();
            if (modelName.isBlank()) {
                continue;
            }
            MediaProviderProfile profile = modelResolver.resolveVideoProfile(modelName);
            if (profile.ready()) {
                ready = true;
                continue;
            }
            errors.add("模型 " + modelName + " 缺少 api_key 或 base_url");
        }
        return ready;
    }

    private int intValue(String raw, int fallback) {
        try {
            int value = Integer.parseInt(String.valueOf(raw).trim());
            return value > 0 ? value : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private double doubleValue(String raw, double fallback) {
        try {
            return Double.parseDouble(String.valueOf(raw).trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String property(String key, String defaultValue) {
        String value = System.getenv(key);
        return value == null ? defaultValue : value.trim();
    }
}
