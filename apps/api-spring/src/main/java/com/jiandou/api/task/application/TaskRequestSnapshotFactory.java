package com.jiandou.api.task.application;

import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import org.springframework.stereotype.Component;

/**
 * 统一负责生成任务请求快照，避免快照拼装逻辑散落在应用服务中。
 */
@Component
public class TaskRequestSnapshotFactory {

    private final ModelRuntimePropertiesResolver modelResolver;

    /**
     * 创建新的任务请求快照工厂。
     * @param modelResolver 模型解析器值
     */
    public TaskRequestSnapshotFactory(ModelRuntimePropertiesResolver modelResolver) {
        this.modelResolver = modelResolver;
    }

    /**
     * 创建create。
     * @param request 请求体
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public GenerationRequestSnapshot create(CreateGenerationTaskRequest request, TaskRecord task) {
        return new GenerationRequestSnapshot(
            "generation",
            task.title(),
            task.creativePrompt(),
            task.aspectRatio(),
            firstNonBlank(
                modelResolver.value("catalog.defaults", "style_preset", "cinematic"),
                "cinematic"
            ),
            trimmed(request.textAnalysisModel(), ""),
            trimmed(request.visionModel(), ""),
            trimmed(request.imageModel(), ""),
            trimmed(request.videoModel(), ""),
            trimmed(
                request.videoSize(),
                modelResolver.value("catalog.defaults", "video_size", "720*1280")
            ),
            task.taskSeed(),
            GenerationRequestSnapshot.RequestedDuration.from(request.videoDurationSeconds()),
            GenerationRequestSnapshot.RequestedOutputCount.from(normalizeOutputCount(request.outputCount())),
            task.minDurationSeconds(),
            task.maxDurationSeconds(),
            task.transcriptText(),
            Boolean.TRUE.equals(request.stopBeforeVideoGeneration())
        );
    }

    /**
     * 规范化输出数量。
     * @param outputCount 输出数量值
     * @return 处理结果
     */
    private Object normalizeOutputCount(Object outputCount) {
        if (outputCount == null) {
            return "auto";
        }
        String raw = String.valueOf(outputCount).trim();
        if (raw.isBlank() || "auto".equalsIgnoreCase(raw)) {
            return "auto";
        }
        try {
            int value = Integer.parseInt(raw);
            if (value < 1) {
                throw new IllegalArgumentException("outputCount 必须大于 0");
            }
            return value;
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException("outputCount 必须为正整数或 auto");
        }
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    /**
     * 处理trimmed。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback == null ? "" : fallback.trim();
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? (fallback == null ? "" : fallback.trim()) : normalized;
    }
}
