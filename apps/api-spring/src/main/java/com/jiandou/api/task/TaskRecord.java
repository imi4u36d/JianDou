package com.jiandou.api.task;

import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 任务聚合在内存层的写模型。
 * 当前仍保留包内可见字段，方便逐步把历史逻辑拆出而不一次性打断现有流程。
 */
public final class TaskRecord {
    String id;
    String title;
    String status;
    int progress;
    String createdAt;
    String updatedAt;
    String sourceFileName;
    String aspectRatio;
    int minDurationSeconds;
    int maxDurationSeconds;
    int retryCount;
    String startedAt;
    String finishedAt;
    int completedOutputCount;
    int currentAttemptNo;
    boolean hasTranscript;
    boolean hasTimedTranscript;
    int sourceAssetCount;
    String editingMode;
    boolean isQueued;
    Integer queuePosition;
    String activeAttemptId;
    String introTemplate;
    String outroTemplate;
    String creativePrompt;
    Integer taskSeed;
    Integer effectRating;
    String effectRatingNote = "";
    String ratedAt;
    String errorMessage = "";
    String transcriptText = "";
    String storyboardScript;
    Map<String, Object> executionContext = new LinkedHashMap<>();
    GenerationRequestSnapshot requestSnapshot = GenerationRequestSnapshot.empty();
    final List<Map<String, Object>> trace = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> statusHistory = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> attempts = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> stageRuns = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> modelCalls = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> materials = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> outputs = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> sourceAssets = new CopyOnWriteArrayList<>();

    /**
     * 对外暴露只读视图时统一走这些访问器，避免内部集合继续向更多模块泄漏。
     */
    public List<Map<String, Object>> attemptsView() {
        return attempts;
    }

    public List<Map<String, Object>> stageRunsView() {
        return stageRuns;
    }

    public List<Map<String, Object>> traceView() {
        return trace;
    }

    public List<Map<String, Object>> modelCallsView() {
        return modelCalls;
    }

    public List<Map<String, Object>> materialsView() {
        return materials;
    }

    public List<Map<String, Object>> outputsView() {
        return outputs;
    }

    public List<Map<String, Object>> sourceAssetsView() {
        return sourceAssets;
    }

    public void setActiveAttempt(String attemptId, int attemptNo) {
        this.activeAttemptId = attemptId;
        this.currentAttemptNo = attemptNo;
    }

    /**
     * 统一生成 UTC 时间字符串，减少各个协作者重复实现时间格式化逻辑。
     */
    public String nowIso() {
        return java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC).toString();
    }
}
