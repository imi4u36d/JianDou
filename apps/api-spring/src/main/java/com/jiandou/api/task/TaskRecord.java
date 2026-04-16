package com.jiandou.api.task;

import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import com.jiandou.api.task.domain.TaskStatus;
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

    public String id() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String title() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String status() {
        return status;
    }

    public TaskStatus statusEnum() {
        return TaskStatus.from(status);
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public void setStatus(TaskStatus status) {
        this.status = status == null ? "" : status.value();
    }

    public int progress() {
        return progress;
    }

    public void setProgress(int progress) {
        this.progress = progress;
    }

    public String createdAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String updatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String sourceFileName() {
        return sourceFileName;
    }

    public void setSourceFileName(String sourceFileName) {
        this.sourceFileName = sourceFileName;
    }

    public String aspectRatio() {
        return aspectRatio;
    }

    public void setAspectRatio(String aspectRatio) {
        this.aspectRatio = aspectRatio;
    }

    public int minDurationSeconds() {
        return minDurationSeconds;
    }

    public void setMinDurationSeconds(int minDurationSeconds) {
        this.minDurationSeconds = minDurationSeconds;
    }

    public int maxDurationSeconds() {
        return maxDurationSeconds;
    }

    public void setMaxDurationSeconds(int maxDurationSeconds) {
        this.maxDurationSeconds = maxDurationSeconds;
    }

    public int retryCount() {
        return retryCount;
    }

    public void setRetryCount(int retryCount) {
        this.retryCount = retryCount;
    }

    public String startedAt() {
        return startedAt;
    }

    public void setStartedAt(String startedAt) {
        this.startedAt = startedAt;
    }

    public String finishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(String finishedAt) {
        this.finishedAt = finishedAt;
    }

    public int completedOutputCount() {
        return completedOutputCount;
    }

    public void setCompletedOutputCount(int completedOutputCount) {
        this.completedOutputCount = completedOutputCount;
    }

    public int currentAttemptNo() {
        return currentAttemptNo;
    }

    public void setCurrentAttemptNo(int currentAttemptNo) {
        this.currentAttemptNo = currentAttemptNo;
    }

    public boolean hasTranscript() {
        return hasTranscript;
    }

    public void setHasTranscript(boolean hasTranscript) {
        this.hasTranscript = hasTranscript;
    }

    public boolean hasTimedTranscript() {
        return hasTimedTranscript;
    }

    public void setHasTimedTranscript(boolean hasTimedTranscript) {
        this.hasTimedTranscript = hasTimedTranscript;
    }

    public int sourceAssetCount() {
        return sourceAssetCount;
    }

    public void setSourceAssetCount(int sourceAssetCount) {
        this.sourceAssetCount = sourceAssetCount;
    }

    public String editingMode() {
        return editingMode;
    }

    public void setEditingMode(String editingMode) {
        this.editingMode = editingMode;
    }

    public boolean isQueued() {
        return isQueued;
    }

    public void setQueued(boolean queued) {
        isQueued = queued;
    }

    public Integer queuePosition() {
        return queuePosition;
    }

    public void setQueuePosition(Integer queuePosition) {
        this.queuePosition = queuePosition;
    }

    public String activeAttemptId() {
        return activeAttemptId;
    }

    public void setActiveAttemptId(String activeAttemptId) {
        this.activeAttemptId = activeAttemptId;
    }

    public String introTemplate() {
        return introTemplate;
    }

    public void setIntroTemplate(String introTemplate) {
        this.introTemplate = introTemplate;
    }

    public String outroTemplate() {
        return outroTemplate;
    }

    public void setOutroTemplate(String outroTemplate) {
        this.outroTemplate = outroTemplate;
    }

    public String creativePrompt() {
        return creativePrompt;
    }

    public void setCreativePrompt(String creativePrompt) {
        this.creativePrompt = creativePrompt;
    }

    public Integer taskSeed() {
        return taskSeed;
    }

    public void setTaskSeed(Integer taskSeed) {
        this.taskSeed = taskSeed;
    }

    public Integer effectRating() {
        return effectRating;
    }

    public void setEffectRating(Integer effectRating) {
        this.effectRating = effectRating;
    }

    public String effectRatingNote() {
        return effectRatingNote;
    }

    public void setEffectRatingNote(String effectRatingNote) {
        this.effectRatingNote = effectRatingNote;
    }

    public String ratedAt() {
        return ratedAt;
    }

    public void setRatedAt(String ratedAt) {
        this.ratedAt = ratedAt;
    }

    public String errorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public String transcriptText() {
        return transcriptText;
    }

    public void setTranscriptText(String transcriptText) {
        this.transcriptText = transcriptText;
    }

    public String storyboardScript() {
        return storyboardScript;
    }

    public void setStoryboardScript(String storyboardScript) {
        this.storyboardScript = storyboardScript;
    }

    public Map<String, Object> executionContext() {
        return executionContext;
    }

    public Map<String, Object> mutableExecutionContext() {
        if (executionContext == null) {
            executionContext = new LinkedHashMap<>();
        }
        return executionContext;
    }

    public void setExecutionContext(Map<String, Object> executionContext) {
        this.executionContext = executionContext == null ? new LinkedHashMap<>() : executionContext;
    }

    public GenerationRequestSnapshot requestSnapshot() {
        return requestSnapshot;
    }

    public void setRequestSnapshot(GenerationRequestSnapshot requestSnapshot) {
        this.requestSnapshot = requestSnapshot == null ? GenerationRequestSnapshot.empty() : requestSnapshot;
    }

    public List<Map<String, Object>> trace() {
        return trace;
    }

    public List<Map<String, Object>> statusHistory() {
        return statusHistory;
    }

    public List<Map<String, Object>> attempts() {
        return attempts;
    }

    public List<Map<String, Object>> stageRuns() {
        return stageRuns;
    }

    public List<Map<String, Object>> modelCalls() {
        return modelCalls;
    }

    public List<Map<String, Object>> materials() {
        return materials;
    }

    public List<Map<String, Object>> outputs() {
        return outputs;
    }

    public List<Map<String, Object>> sourceAssets() {
        return sourceAssets;
    }

    public void addTrace(Map<String, Object> row) {
        trace.add(row);
    }

    public void addStatusHistory(Map<String, Object> row) {
        statusHistory.add(row);
    }

    public void prependAttempt(Map<String, Object> row) {
        attempts.add(0, row);
    }

    public void addStageRun(Map<String, Object> row) {
        stageRuns.add(row);
    }

    public void addModelCall(Map<String, Object> row) {
        modelCalls.add(row);
    }

    public void addMaterial(Map<String, Object> row) {
        materials.add(row);
    }

    public void addOutput(Map<String, Object> row) {
        outputs.add(row);
    }

    public void addSourceAsset(Map<String, Object> row) {
        sourceAssets.add(row);
    }

    /**
     * 对外暴露只读视图时统一走这些访问器，避免内部集合继续向更多模块泄漏。
     */
    public List<Map<String, Object>> attemptsView() {
        return attempts;
    }

    /**
     * 处理阶段Runs视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> stageRunsView() {
        return stageRuns;
    }

    /**
     * 处理追踪视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> traceView() {
        return trace;
    }

    /**
     * 处理模型Calls视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> modelCallsView() {
        return modelCalls;
    }

    /**
     * 处理素材视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> materialsView() {
        return materials;
    }

    /**
     * 处理outputs视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> outputsView() {
        return outputs;
    }

    /**
     * 处理来源Assets视图。
     * @return 处理结果
     */
    public List<Map<String, Object>> sourceAssetsView() {
        return sourceAssets;
    }

    /**
     * 处理setActive尝试。
     * @param attemptId 尝试标识值
     * @param attemptNo 尝试No值
     */
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
