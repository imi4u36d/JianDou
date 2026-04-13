package com.jiandou.api.task;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

public final class TaskRecord {
    String id;
    String title;
    String status;
    String platform;
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
    Map<String, Object> requestSnapshot = new LinkedHashMap<>();
    final List<Map<String, Object>> trace = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> statusHistory = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> attempts = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> stageRuns = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> modelCalls = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> materials = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> outputs = new CopyOnWriteArrayList<>();
    final List<Map<String, Object>> sourceAssets = new CopyOnWriteArrayList<>();

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
}
