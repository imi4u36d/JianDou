package com.jiandou.api.task;

import com.jiandou.api.task.persistence.TaskRow;
import com.jiandou.api.task.persistence.TaskStatusHistoryRow;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class TaskRecordAssembler {

    public TaskRecord fromTaskRow(TaskRow row) {
        TaskRecord task = new TaskRecord();
        task.id = row.taskId();
        task.title = row.title();
        task.status = row.status();
        task.platform = row.platform();
        task.progress = row.progress();
        task.createdAt = format(row.createTime());
        task.updatedAt = format(row.updateTime());
        task.sourceFileName = row.sourceFileName();
        task.aspectRatio = row.aspectRatio();
        task.minDurationSeconds = row.minDurationSeconds();
        task.maxDurationSeconds = row.maxDurationSeconds();
        task.retryCount = row.retryCount();
        task.startedAt = format(row.startedAt());
        task.finishedAt = format(row.finishedAt());
        task.completedOutputCount = row.outputCount();
        task.hasTranscript = hasTranscript(row.context());
        task.hasTimedTranscript = hasTimedTranscript(row.context());
        task.sourceAssetCount = row.sourceAssetIds() == null ? 0 : row.sourceAssetIds().size();
        task.editingMode = row.editingMode();
        task.introTemplate = row.introTemplate();
        task.outroTemplate = row.outroTemplate();
        task.creativePrompt = row.creativePrompt();
        task.taskSeed = row.taskSeed();
        task.effectRating = row.effectRating();
        task.effectRatingNote = row.effectRatingNote() == null ? "" : row.effectRatingNote();
        task.ratedAt = format(row.ratedAt());
        task.errorMessage = row.errorMessage() == null ? "" : row.errorMessage();
        task.transcriptText = transcriptText(row.context());
        task.storyboardScript = storyboardScript(row.context());
        task.executionContext = row.context() == null ? new LinkedHashMap<>() : new LinkedHashMap<>(row.context());
        task.requestSnapshot = row.requestPayload() == null ? new LinkedHashMap<>() : new LinkedHashMap<>(row.requestPayload());
        return task;
    }

    public void applyStatusHistory(TaskRecord task, List<TaskStatusHistoryRow> rows) {
        task.statusHistory.clear();
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
            task.statusHistory.add(item);
        }
    }

    public TaskWriteModel toWriteModel(TaskRecord task) {
        Map<String, Object> context = task.executionContext == null ? new LinkedHashMap<>() : new LinkedHashMap<>(task.executionContext);
        if (task.transcriptText != null && !task.transcriptText.isBlank()) {
            context.put("transcriptText", task.transcriptText);
        } else {
            context.remove("transcriptText");
        }
        if (task.storyboardScript != null && !task.storyboardScript.isBlank()) {
            context.put("storyboardScript", task.storyboardScript);
        } else {
            context.remove("storyboardScript");
        }
        List<String> sourceFileNames = task.sourceFileName == null || task.sourceFileName.isBlank()
            ? List.of()
            : List.of(task.sourceFileName);
        return new TaskWriteModel(
            task.id,
            task.title,
            task.platform,
            task.aspectRatio,
            task.minDurationSeconds,
            task.maxDurationSeconds,
            task.sourceFileName,
            task.introTemplate,
            task.outroTemplate,
            task.creativePrompt,
            task.taskSeed,
            task.effectRating,
            task.effectRatingNote == null ? "" : task.effectRatingNote,
            parse(task.ratedAt),
            task.editingMode,
            task.status,
            task.progress,
            task.errorMessage,
            task.retryCount,
            task.completedOutputCount,
            task.requestSnapshot == null ? new LinkedHashMap<>() : new LinkedHashMap<>(task.requestSnapshot),
            context,
            List.of(),
            sourceFileNames,
            parse(task.startedAt),
            parse(task.finishedAt)
        );
    }

    private boolean hasTranscript(Map<String, Object> context) {
        return !transcriptText(context).isBlank();
    }

    private boolean hasTimedTranscript(Map<String, Object> context) {
        return transcriptText(context).contains("-->");
    }

    private String transcriptText(Map<String, Object> context) {
        if (context == null) {
            return "";
        }
        Object value = context.get("transcriptText");
        return value == null ? "" : String.valueOf(value);
    }

    private String storyboardScript(Map<String, Object> context) {
        if (context == null) {
            return null;
        }
        Object value = context.get("storyboardScript");
        return value == null ? null : String.valueOf(value);
    }

    private String format(OffsetDateTime value) {
        return value == null ? null : value.toString();
    }

    private OffsetDateTime parse(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return OffsetDateTime.parse(value);
    }

    public record TaskWriteModel(
        String taskId,
        String title,
        String platform,
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
