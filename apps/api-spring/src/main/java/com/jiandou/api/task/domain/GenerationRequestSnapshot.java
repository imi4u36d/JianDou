package com.jiandou.api.task.domain;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 任务创建时的请求快照。
 * 该对象用于沉淀用户意图，便于重试、诊断和后续数据迁移。
 */
public record GenerationRequestSnapshot(
    String taskType,
    String title,
    String creativePrompt,
    String aspectRatio,
    String stylePreset,
    String textAnalysisModel,
    String visionModel,
    String imageModel,
    String videoModel,
    String videoSize,
    Integer seed,
    RequestedDuration videoDuration,
    RequestedOutputCount outputCount,
    int minDurationSeconds,
    int maxDurationSeconds,
    String transcriptText,
    boolean stopBeforeVideoGeneration
) {

    public static GenerationRequestSnapshot empty() {
        return new GenerationRequestSnapshot(
            "generation",
            "",
            "",
            "",
            "cinematic",
            "",
            "",
            "",
            "",
            "",
            null,
            RequestedDuration.automatic(),
            RequestedOutputCount.automatic(),
            0,
            0,
            "",
            false
        );
    }

    public static GenerationRequestSnapshot fromMap(Map<String, Object> map) {
        if (map == null || map.isEmpty()) {
            return empty();
        }
        return new GenerationRequestSnapshot(
            stringValue(map.get("taskType"), "generation"),
            stringValue(map.get("title"), ""),
            stringValue(map.get("creativePrompt"), ""),
            stringValue(map.get("aspectRatio"), ""),
            stringValue(map.get("stylePreset"), "cinematic"),
            stringValue(map.get("textAnalysisModel"), ""),
            stringValue(map.get("visionModel"), ""),
            stringValue(map.get("imageModel"), ""),
            stringValue(map.get("videoModel"), ""),
            stringValue(map.get("videoSize"), ""),
            integerValue(map.get("seed")),
            RequestedDuration.from(map.get("videoDurationSeconds")),
            RequestedOutputCount.from(map.get("outputCount")),
            integerValue(map.get("minDurationSeconds"), 0),
            integerValue(map.get("maxDurationSeconds"), 0),
            stringValue(map.get("transcriptText"), ""),
            booleanValue(map.get("stopBeforeVideoGeneration"))
        );
    }

    public Map<String, Object> toMap() {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("taskType", taskType);
        row.put("title", title);
        row.put("creativePrompt", creativePrompt);
        row.put("aspectRatio", aspectRatio);
        row.put("stylePreset", stylePreset);
        row.put("textAnalysisModel", textAnalysisModel);
        row.put("visionModel", visionModel);
        row.put("imageModel", imageModel);
        row.put("videoModel", videoModel);
        row.put("videoSize", videoSize);
        row.put("seed", seed);
        row.put("videoDurationSeconds", videoDuration.toValue());
        row.put("outputCount", outputCount.toValue());
        row.put("minDurationSeconds", minDurationSeconds);
        row.put("maxDurationSeconds", maxDurationSeconds);
        row.put("transcriptText", transcriptText);
        row.put("stopBeforeVideoGeneration", stopBeforeVideoGeneration);
        return row;
    }

    public String modelValue(String fieldName) {
        return switch (fieldName) {
            case "textAnalysisModel" -> textAnalysisModel;
            case "visionModel" -> visionModel;
            case "imageModel" -> imageModel;
            case "videoModel" -> videoModel;
            default -> "";
        };
    }

    private static String stringValue(Object value, String fallback) {
        String normalized = value == null ? "" : String.valueOf(value).trim();
        return normalized.isBlank() ? fallback : normalized;
    }

    private static Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private static int integerValue(Object value, int fallback) {
        Integer parsed = integerValue(value);
        return parsed == null ? fallback : parsed;
    }

    private static boolean booleanValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        return value != null && Boolean.parseBoolean(String.valueOf(value).trim());
    }

    /**
     * 时长参数支持 auto 与显式秒数两种模式。
     */
    public record RequestedDuration(boolean auto, Integer seconds) {

        public static RequestedDuration automatic() {
            return new RequestedDuration(true, null);
        }

        public static RequestedDuration from(Object raw) {
            if (raw == null) {
                return automatic();
            }
            if (raw instanceof Number number) {
                return new RequestedDuration(false, Math.max(1, number.intValue()));
            }
            String value = String.valueOf(raw).trim();
            if (value.isBlank() || "auto".equalsIgnoreCase(value)) {
                return automatic();
            }
            try {
                return new RequestedDuration(false, Math.max(1, (int) Math.round(Double.parseDouble(value))));
            } catch (NumberFormatException ex) {
                return automatic();
            }
        }

        public Object toValue() {
            return auto ? "auto" : seconds;
        }
    }

    /**
     * 输出条数参数支持 auto 与显式数量两种模式。
     */
    public record RequestedOutputCount(boolean auto, Integer count) {

        public static RequestedOutputCount automatic() {
            return new RequestedOutputCount(true, null);
        }

        public static RequestedOutputCount from(Object raw) {
            if (raw == null) {
                return automatic();
            }
            if (raw instanceof Number number) {
                return new RequestedOutputCount(false, Math.max(1, number.intValue()));
            }
            String value = String.valueOf(raw).trim();
            if (value.isBlank() || "auto".equalsIgnoreCase(value)) {
                return automatic();
            }
            try {
                return new RequestedOutputCount(false, Math.max(1, Integer.parseInt(value)));
            } catch (NumberFormatException ex) {
                return automatic();
            }
        }

        public Object toValue() {
            return auto ? "auto" : count;
        }
    }
}
