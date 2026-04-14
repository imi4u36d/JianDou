package com.jiandou.api.task;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Aggregates all persistence rows produced by one task-side state transition.
 * Repository adapters can persist this mutation in a single transaction.
 */
public final class TaskPersistenceMutation {

    private String taskId = "";
    private TaskRecord task;
    private final List<Map<String, Object>> attempts = new ArrayList<>();
    private final List<Map<String, Object>> statusHistoryRows = new ArrayList<>();
    private final List<Map<String, Object>> traceRows = new ArrayList<>();
    private final List<Map<String, Object>> stageRunRows = new ArrayList<>();
    private final List<Map<String, Object>> modelCallRows = new ArrayList<>();
    private final List<Map<String, Object>> materialRows = new ArrayList<>();
    private final List<Map<String, Object>> resultRows = new ArrayList<>();
    private final List<Map<String, Object>> queueEventRows = new ArrayList<>();
    private final List<Map<String, Object>> workerInstanceRows = new ArrayList<>();

    public TaskPersistenceMutation task(TaskRecord value) {
        this.task = value;
        this.taskId = value == null || value.id == null ? "" : value.id;
        return this;
    }

    public TaskPersistenceMutation taskId(String value) {
        this.taskId = value == null ? "" : value.trim();
        return this;
    }

    public TaskPersistenceMutation addAttempt(Map<String, Object> value) {
        add(attempts, value);
        return this;
    }

    public TaskPersistenceMutation addStatusHistory(Map<String, Object> value) {
        add(statusHistoryRows, value);
        return this;
    }

    public TaskPersistenceMutation addTrace(Map<String, Object> value) {
        add(traceRows, value);
        return this;
    }

    public TaskPersistenceMutation addStageRun(Map<String, Object> value) {
        add(stageRunRows, value);
        return this;
    }

    public TaskPersistenceMutation addModelCall(Map<String, Object> value) {
        add(modelCallRows, value);
        return this;
    }

    public TaskPersistenceMutation addMaterial(Map<String, Object> value) {
        add(materialRows, value);
        return this;
    }

    public TaskPersistenceMutation addResult(Map<String, Object> value) {
        add(resultRows, value);
        return this;
    }

    public TaskPersistenceMutation addQueueEvent(Map<String, Object> value) {
        add(queueEventRows, value);
        return this;
    }

    public TaskPersistenceMutation addWorkerInstance(Map<String, Object> value) {
        add(workerInstanceRows, value);
        return this;
    }

    public TaskRecord task() {
        return task;
    }

    public String taskId() {
        return taskId;
    }

    public List<Map<String, Object>> attempts() {
        return attempts;
    }

    public List<Map<String, Object>> statusHistoryRows() {
        return statusHistoryRows;
    }

    public List<Map<String, Object>> traceRows() {
        return traceRows;
    }

    public List<Map<String, Object>> stageRunRows() {
        return stageRunRows;
    }

    public List<Map<String, Object>> modelCallRows() {
        return modelCallRows;
    }

    public List<Map<String, Object>> materialRows() {
        return materialRows;
    }

    public List<Map<String, Object>> resultRows() {
        return resultRows;
    }

    public List<Map<String, Object>> queueEventRows() {
        return queueEventRows;
    }

    public List<Map<String, Object>> workerInstanceRows() {
        return workerInstanceRows;
    }

    private void add(List<Map<String, Object>> target, Map<String, Object> value) {
        if (value != null && !value.isEmpty()) {
            target.add(value);
        }
    }
}
