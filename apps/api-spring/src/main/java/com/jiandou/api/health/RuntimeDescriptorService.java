package com.jiandou.api.health;

import com.jiandou.api.generation.MediaProviderProfile;
import com.jiandou.api.generation.ModelRuntimeProfile;
import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import com.jiandou.api.health.dto.RuntimeDescriptorResponse;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 汇总当前运行环境、模型目录和规划能力，用于健康检查与管理端展示。
 */
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

    public RuntimeDescriptorResponse describeRuntime() {
        List<ModelCatalogItem> textModels = toCatalogItems(modelResolver.listModelsByKind("text"));
        List<ModelCatalogItem> visionModels = toCatalogItems(modelResolver.listModelsByKind("vision"));
        List<ModelCatalogItem> imageModels = toCatalogItems(modelResolver.listModelsByKind("image"));
        List<ModelCatalogItem> videoModels = toCatalogItems(modelResolver.listModelsByKind("video"));
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

        RuntimeDescriptorResponse.ModelInfo model = new RuntimeDescriptorResponse.ModelInfo(
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            hasReadyTextModel || hasReadyVisionModel || hasReadyImageModel || hasReadyVideoModel,
            ready,
            doubleValue(modelResolver.value("model", "temperature", "0.15"), 0.15),
            intValue(modelResolver.value("model", "max_tokens", "2000"), 2000),
            modelResolver.configSource(),
            configErrors
        );

        RuntimeDescriptorResponse.PlanningCapabilities planning = new RuntimeDescriptorResponse.PlanningCapabilities(
            true,
            true,
            true,
            true,
            true,
            true,
            true,
            true,
            false
        );

        RuntimeDescriptorResponse.RuntimeInfo runtime = new RuntimeDescriptorResponse.RuntimeInfo(
            appName,
            appEnv,
            executionMode,
            property("JIANDOU_DATABASE_URL", "jdbc:mysql://127.0.0.1:3306/ai_cut"),
            "",
            Paths.get(storageRoot).toAbsolutePath().normalize().toString(),
            model,
            planning
        );

        return new RuntimeDescriptorResponse(true, runtime);
    }

    /**
     * 如果某类模型一个都没有，就直接记录配置缺口，避免前端误判为“未加载完成”。
     */
    private void appendCatalogErrors(List<String> errors, List<ModelCatalogItem> models, String label) {
        if (models.isEmpty()) {
            errors.add("未配置可用" + label + "模型");
        }
    }

    /**
     * 文本和视觉模型都走文本配置解析，因此共用这套就绪校验逻辑。
     */
    private boolean hasReadyTextModel(List<ModelCatalogItem> textModels, List<String> errors) {
        boolean ready = false;
        for (ModelCatalogItem model : textModels) {
            String modelName = model.value();
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

    private boolean hasReadyImageModel(List<ModelCatalogItem> imageModels, List<String> errors) {
        boolean ready = false;
        for (ModelCatalogItem model : imageModels) {
            String modelName = model.value();
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

    private boolean hasReadyVideoModel(List<ModelCatalogItem> videoModels, List<String> errors) {
        boolean ready = false;
        for (ModelCatalogItem model : videoModels) {
            String modelName = model.value();
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

    private List<ModelCatalogItem> toCatalogItems(List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return List.of();
        }
        List<ModelCatalogItem> items = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            items.add(ModelCatalogItem.from(row));
        }
        return List.copyOf(items);
    }

    /**
     * 把目录接口里的弱类型配置行转换成内部强类型记录，方便后续统一校验。
     */
    private record ModelCatalogItem(
        String value,
        String label,
        String provider,
        String family,
        String description,
        String kind,
        String fallbackModel,
        boolean supportsSeed
    ) {

        private static ModelCatalogItem from(Map<String, Object> row) {
            if (row == null || row.isEmpty()) {
                return new ModelCatalogItem("", "", "", "", "", "", "", false);
            }
            return new ModelCatalogItem(
                stringValue(row.get("value")),
                stringValue(row.get("label")),
                stringValue(row.get("provider")),
                stringValue(row.get("family")),
                stringValue(row.get("description")),
                stringValue(row.get("kind")),
                stringValue(row.get("fallbackModel")),
                booleanValue(row.get("supportsSeed"))
            );
        }

        private static String stringValue(Object raw) {
            return raw == null ? "" : String.valueOf(raw).trim();
        }

        private static boolean booleanValue(Object raw) {
            if (raw instanceof Boolean value) {
                return value;
            }
            return Boolean.parseBoolean(stringValue(raw));
        }
    }
}
