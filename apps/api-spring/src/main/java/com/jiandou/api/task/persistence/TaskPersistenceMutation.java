package com.jiandou.api.task.persistence;

import com.jiandou.api.task.TaskRecord;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Aggregates all persistence rows produced by one 任务-side state transition.
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

    /**
     * 处理任务。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation task(TaskRecord value) {
        this.task = value;
        this.taskId = value == null || value.id() == null ? "" : value.id();
        return this;
    }

    /**
     * 处理任务标识。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation taskId(String value) {
        this.taskId = value == null ? "" : value.trim();
        return this;
    }

    /**
     * 处理add尝试。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addAttempt(Map<String, Object> value) {
        add(attempts, value);
        return this;
    }

    /**
     * 处理add状态History。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addStatusHistory(Map<String, Object> value) {
        add(statusHistoryRows, value);
        return this;
    }

    /**
     * 处理add追踪。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addTrace(Map<String, Object> value) {
        add(traceRows, value);
        return this;
    }

    /**
     * 处理add阶段运行。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addStageRun(Map<String, Object> value) {
        add(stageRunRows, value);
        return this;
    }

    /**
     * 处理add模型调用。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addModelCall(Map<String, Object> value) {
        add(modelCallRows, value);
        return this;
    }

    /**
     * 处理add素材。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addMaterial(Map<String, Object> value) {
        add(materialRows, value);
        return this;
    }

    /**
     * 处理add结果。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addResult(Map<String, Object> value) {
        add(resultRows, value);
        return this;
    }

    /**
     * 处理add队列事件。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addQueueEvent(Map<String, Object> value) {
        add(queueEventRows, value);
        return this;
    }

    /**
     * 处理add工作节点Instance。
     * @param value 待处理的值
     * @return 处理结果
     */
    public TaskPersistenceMutation addWorkerInstance(Map<String, Object> value) {
        add(workerInstanceRows, value);
        return this;
    }

    /**
     * 处理任务。
     * @return 处理结果
     */
    public TaskRecord task() {
        return task;
    }

    /**
     * 处理任务标识。
     * @return 处理结果
     */
    public String taskId() {
        return taskId;
    }

    /**
     * 处理attempts。
     * @return 处理结果
     */
    public List<Map<String, Object>> attempts() {
        return attempts;
    }

    /**
     * 处理状态History行。
     * @return 处理结果
     */
    public List<Map<String, Object>> statusHistoryRows() {
        return statusHistoryRows;
    }

    /**
     * 处理追踪行。
     * @return 处理结果
     */
    public List<Map<String, Object>> traceRows() {
        return traceRows;
    }

    /**
     * 处理阶段运行行。
     * @return 处理结果
     */
    public List<Map<String, Object>> stageRunRows() {
        return stageRunRows;
    }

    /**
     * 处理模型调用行。
     * @return 处理结果
     */
    public List<Map<String, Object>> modelCallRows() {
        return modelCallRows;
    }

    /**
     * 处理素材行。
     * @return 处理结果
     */
    public List<Map<String, Object>> materialRows() {
        return materialRows;
    }

    /**
     * 处理结果行。
     * @return 处理结果
     */
    public List<Map<String, Object>> resultRows() {
        return resultRows;
    }

    /**
     * 处理队列事件行。
     * @return 处理结果
     */
    public List<Map<String, Object>> queueEventRows() {
        return queueEventRows;
    }

    /**
     * 处理工作节点Instance行。
     * @return 处理结果
     */
    public List<Map<String, Object>> workerInstanceRows() {
        return workerInstanceRows;
    }

    /**
     * 处理add。
     * @param target target值
     * @param value 待处理的值
     */
    private void add(List<Map<String, Object>> target, Map<String, Object> value) {
        if (value != null && !value.isEmpty()) {
            target.add(value);
        }
    }
}
