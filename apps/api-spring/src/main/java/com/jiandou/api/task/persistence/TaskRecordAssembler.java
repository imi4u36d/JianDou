package com.jiandou.api.task.persistence;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * 任务记录Assembler。
 */
@Component
public class TaskRecordAssembler {

    /**
     * 处理from任务行。
     * @param row 行值
     * @return 处理结果
     */
    public TaskRecord fromTaskRow(TaskRow row) {
        TaskRecord task = new TaskRecord();
        task.setId(row.taskId());
        task.setTitle(row.title());
        task.setStatus(row.status());
        task.setProgress(row.progress());
        task.setCreatedAt(format(row.createTime()));
        task.setUpdatedAt(format(row.updateTime()));
        task.setSourceFileName(row.sourceFileName());
        task.setAspectRatio(row.aspectRatio());
        task.setMinDurationSeconds(row.minDurationSeconds());
        task.setMaxDurationSeconds(row.maxDurationSeconds());
        task.setRetryCount(row.retryCount());
        task.setStartedAt(format(row.startedAt()));
        task.setFinishedAt(format(row.finishedAt()));
        task.setCompletedOutputCount(row.outputCount());
        task.setHasTranscript(hasTranscript(row.context()));
        task.setHasTimedTranscript(hasTimedTranscript(row.context()));
        task.setSourceAssetCount(row.sourceAssetIds() == null ? 0 : row.sourceAssetIds().size());
        task.setEditingMode(row.editingMode());
        task.setIntroTemplate(row.introTemplate());
        task.setOutroTemplate(row.outroTemplate());
        task.setCreativePrompt(row.creativePrompt());
        task.setTaskSeed(row.taskSeed());
        task.setEffectRating(row.effectRating());
        task.setEffectRatingNote(row.effectRatingNote() == null ? "" : row.effectRatingNote());
        task.setRatedAt(format(row.ratedAt()));
        task.setErrorMessage(row.errorMessage() == null ? "" : row.errorMessage());
        task.setTranscriptText(transcriptText(row.context()));
        task.setStoryboardScript(storyboardScript(row.context()));
        task.setExecutionContext(row.context() == null ? new LinkedHashMap<>() : new LinkedHashMap<>(row.context()));
        task.setRequestSnapshot(GenerationRequestSnapshot.fromMap(row.requestPayload()));
        return task;
    }

    /**
     * 应用状态History。
     * @param task 要处理的任务对象
     * @param rows 行值
     */
    public void applyStatusHistory(TaskRecord task, List<TaskStatusHistoryRow> rows) {
        task.statusHistory().clear();
        for (TaskStatusHistoryRow row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("statusHistoryId", row.taskStatusHistoryId());
            item.put("taskId", row.taskId());
            item.put("previousStatus", row.previousStatus());
            item.put("nextStatus", row.currentStatus());
            item.put("progress", row.progress());
            item.put("stage", row.stage());
            item.put("event", row.event());
            item.put("reason", row.message());
            item.put("operator", row.operatorType());
            item.put("changedAt", format(row.changeTime()));
            item.put("payload", row.payload() == null ? Map.of() : row.payload());
            task.statusHistory().add(item);
        }
    }

    /**
     * 处理转为写入模型。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public TaskWriteModel toWriteModel(TaskRecord task) {
        Map<String, Object> context = task.executionContext() == null ? new LinkedHashMap<>() : new LinkedHashMap<>(task.executionContext());
        if (task.transcriptText() != null && !task.transcriptText().isBlank()) {
            context.put("transcriptText", task.transcriptText());
        } else {
            context.remove("transcriptText");
        }
        if (task.storyboardScript() != null && !task.storyboardScript().isBlank()) {
            context.put("storyboardScript", task.storyboardScript());
        } else {
            context.remove("storyboardScript");
        }
        List<String> sourceFileNames = task.sourceFileName() == null || task.sourceFileName().isBlank()
            ? List.of()
            : List.of(task.sourceFileName());
        return new TaskWriteModel(
            task.id(),
            task.title(),
            task.aspectRatio(),
            task.minDurationSeconds(),
            task.maxDurationSeconds(),
            task.sourceFileName(),
            task.introTemplate(),
            task.outroTemplate(),
            task.creativePrompt(),
            task.taskSeed(),
            task.effectRating(),
            task.effectRatingNote() == null ? "" : task.effectRatingNote(),
            parse(task.ratedAt()),
            task.editingMode(),
            task.status(),
            task.progress(),
            task.errorMessage(),
            task.retryCount(),
            task.completedOutputCount(),
            task.requestSnapshot() == null ? new LinkedHashMap<>() : new LinkedHashMap<>(task.requestSnapshot().toMap()),
            context,
            List.of(),
            sourceFileNames,
            parse(task.startedAt()),
            parse(task.finishedAt())
        );
    }

    /**
     * 检查是否正文。
     * @param context context值
     * @return 是否满足条件
     */
    private boolean hasTranscript(Map<String, Object> context) {
        return !transcriptText(context).isBlank();
    }

    /**
     * 检查是否Timed正文。
     * @param context context值
     * @return 是否满足条件
     */
    private boolean hasTimedTranscript(Map<String, Object> context) {
        return transcriptText(context).contains("-->");
    }

    /**
     * 处理正文文本。
     * @param context context值
     * @return 处理结果
     */
    private String transcriptText(Map<String, Object> context) {
        if (context == null) {
            return "";
        }
        Object value = context.get("transcriptText");
        return value == null ? "" : String.valueOf(value);
    }

    /**
     * 处理分镜脚本。
     * @param context context值
     * @return 处理结果
     */
    private String storyboardScript(Map<String, Object> context) {
        if (context == null) {
            return null;
        }
        Object value = context.get("storyboardScript");
        return value == null ? null : String.valueOf(value);
    }

    /**
     * 格式化format。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String format(OffsetDateTime value) {
        return value == null ? null : value.toString();
    }

    /**
     * 解析解析。
     * @param value 待处理的值
     * @return 处理结果
     */
    private OffsetDateTime parse(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return OffsetDateTime.parse(value);
    }

    /**
     * 处理任务写入模型。
     * @param taskId 任务标识
     * @param title title值
     * @param aspectRatio aspectRatio值
     * @param minDurationSeconds 最小时长Seconds值
     * @param maxDurationSeconds 最大时长Seconds值
     * @param sourceFileName 来源文件Name值
     * @param introTemplate intro模板值
     * @param outroTemplate outro模板值
     * @param creativePrompt 创意提示词值
     * @param taskSeed 任务种子值
     * @param effectRating 效果评分值
     * @param effectRatingNote 效果评分Note值
     * @param ratedAt ratedAt值
     * @param editingMode 编辑模式值
     * @param status 状态值
     * @param progress 进度值
     * @param errorMessage errorMessage值
     * @param retryCount 重试数量值
     * @param completedOutputCount completed输出数量值
     * @param requestPayload 请求负载值
     * @param context context值
     * @param sourceAssetIds 来源素材标识列表值
     * @param sourceFileNames 来源文件Names值
     * @param startedAt startedAt值
     * @param finishedAt finishedAt值
     * @return 处理结果
     */
    public record TaskWriteModel(
        String taskId,
        String title,
        String aspectRatio,
        int minDurationSeconds,
        int maxDurationSeconds,
        String sourceFileName,
        String introTemplate,
        String outroTemplate,
        String creativePrompt,
        Integer taskSeed,
        Integer effectRating,
        String effectRatingNote,
        OffsetDateTime ratedAt,
        String editingMode,
        String status,
        int progress,
        String errorMessage,
        int retryCount,
        int completedOutputCount,
        Map<String, Object> requestPayload,
        Map<String, Object> context,
        List<String> sourceAssetIds,
        List<String> sourceFileNames,
        OffsetDateTime startedAt,
        OffsetDateTime finishedAt
    ) {}
}
