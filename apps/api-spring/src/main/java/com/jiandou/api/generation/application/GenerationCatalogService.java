package com.jiandou.api.generation.application;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.orchestration.GenerationRunSupport;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * 生成目录服务。
 */
@Component
public class GenerationCatalogService {

    private final ModelRuntimePropertiesResolver modelResolver;
    private final GenerationRunSupport support;

    /**
     * 创建新的生成目录服务。
     * @param modelResolver 模型解析器值
     * @param support 支持值
     */
    public GenerationCatalogService(ModelRuntimePropertiesResolver modelResolver, GenerationRunSupport support) {
        this.modelResolver = modelResolver;
        this.support = support;
    }

    /**
     * 处理目录。
     * @return 处理结果
     */
    public Map<String, Object> catalog() {
        String defaultAspectRatio = support.firstNonBlank(
            modelResolver.value("pipeline", "default_aspect_ratio", "9:16"),
            "9:16"
        );
        String defaultStylePreset = support.firstNonBlank(
            modelResolver.value("catalog.defaults", "style_preset", "cinematic"),
            "cinematic"
        );
        String defaultVideoSize = support.firstNonBlank(
            modelResolver.value("catalog.defaults", "video_size", "720*1280"),
            "720*1280"
        );
        int defaultVideoDurationSeconds = support.firstPositiveInt(
            modelResolver.intValue("catalog.defaults", "video_duration_seconds", 0),
            8
        );
        String defaultImageSize = modelResolver.value("catalog.defaults", "image_size", "1024x1024");
        List<Map<String, Object>> textModels = modelResolver.listModelsByKind(GenerationModelKinds.TEXT);
        List<Map<String, Object>> visionModels = modelResolver.listModelsByKind(GenerationModelKinds.VISION);
        List<Map<String, Object>> imageModels = modelResolver.listModelsByKind(GenerationModelKinds.IMAGE);
        List<Map<String, Object>> videoModels = modelResolver.listModelsByKind(GenerationModelKinds.VIDEO);
        List<String> videoModelNames = videoModels.stream()
            .map(item -> String.valueOf(item.getOrDefault("value", "")).trim())
            .filter(item -> !item.isBlank())
            .toList();
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("defaultAspectRatio", defaultAspectRatio);
        payload.put("aspectRatios", aspectRatioOptions());
        payload.put("stylePresets", stylePresetOptions());
        payload.put("imageSizes", imageSizeOptions());
        payload.put("textAnalysisModels", textModels);
        payload.put("defaultTextAnalysisModel", null);
        payload.put("visionModels", visionModels);
        payload.put("defaultVisionModel", null);
        payload.put("imageModels", imageModels);
        payload.put("videoModels", videoModels);
        payload.put("defaultVideoModel", null);
        payload.put("videoSizes", videoSizeOptions(videoModels, videoModelNames));
        payload.put("videoDurations", videoDurationOptions(videoModels, videoModelNames));
        payload.put("defaultStylePreset", defaultStylePreset);
        payload.put("defaultImageSize", defaultImageSize);
        payload.put("defaultVideoSize", defaultVideoSize);
        payload.put("defaultVideoDurationSeconds", defaultVideoDurationSeconds);
        payload.put("configSource", modelResolver.configSource());
        return payload;
    }

    /**
     * 处理aspectRatio选项。
     * @return 处理结果
     */
    private List<Map<String, Object>> aspectRatioOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.aspect_ratios")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", support.firstNonBlank(section.values().get("label"), section.name()));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "9:16", "label", "竖版 9:16"));
            items.add(Map.of("value", "16:9", "label", "横版 16:9"));
        }
        return items;
    }

    /**
     * 处理风格预设选项。
     * @return 处理结果
     */
    private List<Map<String, Object>> stylePresetOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.style_presets")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("key", section.name());
            row.put("label", support.firstNonBlank(section.values().get("label"), section.name()));
            row.put("description", support.firstNonBlank(section.values().get("description"), ""));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("key", "cinematic", "label", "电影写实", "description", "贴近真实影视剧照与镜头语言"));
            items.add(Map.of("key", "drama", "label", "短剧冲突", "description", "更强调人物冲突和情绪推进"));
        }
        return items;
    }

    /**
     * 处理图像Size选项。
     * @return 处理结果
     */
    private List<Map<String, Object>> imageSizeOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.image_sizes")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", support.firstNonBlank(section.values().get("label"), section.name()));
            row.put("width", support.positiveInt(section.values().get("width"), 0));
            row.put("height", support.positiveInt(section.values().get("height"), 0));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "1024x1024", "label", "1:1 · 1024x1024", "width", 1024, "height", 1024));
            items.add(Map.of("value", "720x1280", "label", "9:16 · 720x1280", "width", 720, "height", 1280));
        }
        return items;
    }

    /**
     * 处理视频Size选项。
     * @param videoModels 视频Models值
     * @param videoModelNames 视频模型Names值
     * @return 处理结果
     */
    private List<Map<String, Object>> videoSizeOptions(List<Map<String, Object>> videoModels, List<String> videoModelNames) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.video_sizes")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", support.firstNonBlank(section.values().get("label"), section.name()));
            row.put("width", support.positiveInt(section.values().get("width"), 0));
            row.put("height", support.positiveInt(section.values().get("height"), 0));
            row.put("supportedModels", modelsSupportingSize(videoModels, section.name(), videoModelNames));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "480*854", "label", "480P · 480 x 854", "width", 480, "height", 854, "supportedModels", videoModelNames));
            items.add(Map.of("value", "854*480", "label", "480P · 854 x 480", "width", 854, "height", 480, "supportedModels", videoModelNames));
            items.add(Map.of("value", "720*1280", "label", "720P · 720 x 1280", "width", 720, "height", 1280, "supportedModels", videoModelNames));
            items.add(Map.of("value", "1280*720", "label", "720P · 1280 x 720", "width", 1280, "height", 720, "supportedModels", videoModelNames));
            items.add(Map.of("value", "1080*1920", "label", "1080P · 1080 x 1920", "width", 1080, "height", 1920, "supportedModels", videoModelNames));
            items.add(Map.of("value", "1920*1080", "label", "1080P · 1920 x 1080", "width", 1920, "height", 1080, "supportedModels", videoModelNames));
        }
        return items;
    }

    /**
     * 处理视频时长选项。
     * @param videoModels 视频Models值
     * @param videoModelNames 视频模型Names值
     * @return 处理结果
     */
    private List<Map<String, Object>> videoDurationOptions(List<Map<String, Object>> videoModels, List<String> videoModelNames) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.video_durations")) {
            int duration = support.positiveInt(section.name(), 0);
            if (duration <= 0) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", duration);
            row.put("label", support.firstNonBlank(section.values().get("label"), duration + " 秒"));
            row.put("supportedModels", modelsSupportingDuration(videoModels, duration, videoModelNames));
            items.add(row);
        }
        if (items.isEmpty()) {
            for (int duration : List.of(4, 6, 8, 10, 12)) {
                items.add(Map.of("value", duration, "label", duration + " 秒", "supportedModels", videoModelNames));
            }
        }
        return items;
    }

    /**
     * 处理modelsSupportingSize。
     * @param videoModels 视频Models值
     * @param size size值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private List<String> modelsSupportingSize(List<Map<String, Object>> videoModels, String size, List<String> fallback) {
        List<String> matched = new ArrayList<>();
        String normalizedSize = support.normalizeValue(size);
        for (Map<String, Object> videoModel : videoModels) {
            for (String supportedSize : support.stringList(videoModel.get("supportedSizes"))) {
                if (support.normalizeValue(supportedSize).equals(normalizedSize)) {
                    matched.add(String.valueOf(videoModel.getOrDefault("value", "")).trim());
                    break;
                }
            }
        }
        return matched.isEmpty() ? fallback : matched;
    }

    /**
     * 处理modelsSupporting时长。
     * @param videoModels 视频Models值
     * @param duration 时长值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private List<String> modelsSupportingDuration(List<Map<String, Object>> videoModels, int duration, List<String> fallback) {
        List<String> matched = new ArrayList<>();
        for (Map<String, Object> videoModel : videoModels) {
            for (Integer supportedDuration : support.integerList(videoModel.get("supportedDurations"))) {
                if (supportedDuration != null && supportedDuration == duration) {
                    matched.add(String.valueOf(videoModel.getOrDefault("value", "")).trim());
                    break;
                }
            }
        }
        return matched.isEmpty() ? fallback : matched;
    }
}
