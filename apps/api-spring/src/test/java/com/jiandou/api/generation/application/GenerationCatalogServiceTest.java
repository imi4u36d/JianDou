package com.jiandou.api.generation.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.orchestration.GenerationRunSupport;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver.ConfigSection;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GenerationCatalogServiceTest {

    @Test
    void catalogFallsBackToBuiltInDefaults() {
        ModelRuntimePropertiesResolver modelResolver = mock(ModelRuntimePropertiesResolver.class);
        GenerationCatalogService service = new GenerationCatalogService(modelResolver, new GenerationRunSupport(null, null, null));
        when(modelResolver.value(anyString(), anyString(), anyString())).thenAnswer(invocation -> invocation.getArgument(2));
        when(modelResolver.intValue(anyString(), anyString(), eq(0))).thenReturn(0);
        when(modelResolver.listModelsByKind(anyString())).thenReturn(List.of());
        when(modelResolver.listSections(anyString())).thenReturn(List.of());
        when(modelResolver.configSource()).thenReturn("dir:/workspace/config");

        Map<String, Object> payload = service.catalog();

        assertEquals("9:16", payload.get("defaultAspectRatio"));
        assertEquals("cinematic", payload.get("defaultStylePreset"));
        assertEquals("1024x1024", payload.get("defaultImageSize"));
        assertEquals("720*1280", payload.get("defaultVideoSize"));
        assertEquals(8, payload.get("defaultVideoDurationSeconds"));
        assertEquals("dir:/workspace/config", payload.get("configSource"));
        assertEquals(2, list(payload, "aspectRatios").size());
        assertEquals(2, list(payload, "stylePresets").size());
        assertEquals(2, list(payload, "imageSizes").size());
        assertEquals(6, list(payload, "videoSizes").size());
        assertEquals(List.of(4, 6, 8, 10, 12), list(payload, "videoDurations").stream().map(item -> item.get("value")).toList());
    }

    @Test
    void catalogUsesConfiguredSectionsAndMatchesVideoCapabilities() {
        ModelRuntimePropertiesResolver modelResolver = mock(ModelRuntimePropertiesResolver.class);
        GenerationCatalogService service = new GenerationCatalogService(modelResolver, new GenerationRunSupport(null, null, null));
        when(modelResolver.value("pipeline", "default_aspect_ratio", "9:16")).thenReturn("16:9");
        when(modelResolver.value("catalog.defaults", "style_preset", "cinematic")).thenReturn("neo");
        when(modelResolver.value("catalog.defaults", "video_size", "720*1280")).thenReturn("720*1280");
        when(modelResolver.value("catalog.defaults", "image_size", "1024x1024")).thenReturn("1536x1024");
        when(modelResolver.intValue("catalog.defaults", "video_duration_seconds", 0)).thenReturn(8);
        when(modelResolver.listSections("catalog.aspect_ratios")).thenReturn(List.of(
            new ConfigSection("3:4", Map.of("label", "海报 3:4"))
        ));
        when(modelResolver.listSections("catalog.style_presets")).thenReturn(List.of(
            new ConfigSection("neo", Map.of("label", "霓虹风格", "description", "夜景与高反差"))
        ));
        when(modelResolver.listSections("catalog.image_sizes")).thenReturn(List.of(
            new ConfigSection("1536x1024", Map.of("label", "横版", "width", "1536", "height", "1024"))
        ));
        when(modelResolver.listSections("catalog.video_sizes")).thenReturn(List.of(
            new ConfigSection("720*1280", Map.of("label", "720P", "width", "720", "height", "1280"))
        ));
        when(modelResolver.listSections("catalog.video_durations")).thenReturn(List.of(
            new ConfigSection("8", Map.of("label", "8 秒"))
        ));
        when(modelResolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(Map.of("value", "gpt-4.1")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.VISION)).thenReturn(List.of(Map.of("value", "gpt-4.1-vision")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of(Map.of("value", "seedream-3.0")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(
            Map.of("value", "seedance", "supportedSizes", List.of("720*1280"), "supportedDurations", List.of(8)),
            Map.of("value", "wanx", "supportedSizes", List.of("1280*720"), "supportedDurations", List.of(10))
        ));
        when(modelResolver.configSource()).thenReturn("dir:/workspace/config");

        Map<String, Object> payload = service.catalog();

        assertEquals("16:9", payload.get("defaultAspectRatio"));
        assertEquals("neo", payload.get("defaultStylePreset"));
        assertEquals("1536x1024", payload.get("defaultImageSize"));
        assertEquals("720*1280", payload.get("defaultVideoSize"));
        assertEquals(8, payload.get("defaultVideoDurationSeconds"));
        assertEquals("dir:/workspace/config", payload.get("configSource"));
        assertEquals(List.of("seedance"), list(payload, "videoSizes").get(0).get("supportedModels"));
        assertEquals(List.of("seedance"), list(payload, "videoDurations").get(0).get("supportedModels"));
        assertEquals("海报 3:4", list(payload, "aspectRatios").get(0).get("label"));
        assertEquals("夜景与高反差", list(payload, "stylePresets").get(0).get("description"));
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> list(Map<String, Object> payload, String key) {
        return (List<Map<String, Object>>) payload.get(key);
    }
}
