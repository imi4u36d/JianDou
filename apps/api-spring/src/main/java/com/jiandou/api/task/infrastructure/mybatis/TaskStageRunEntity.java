package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_task_stage_runs")
public class TaskStageRunEntity {

    @TableId("task_stage_run_id")
    private String taskStageRunId;
    @TableField("task_id")
    private String taskId;
    @TableField("attempt_id")
    private String attemptId;
    @TableField("stage_name")
    private String stageName;
    @TableField("stage_seq")
    private Integer stageSeq;
    @TableField("clip_index")
    private Integer clipIndex;
    private String status;
    @TableField("worker_instance_id")
    private String workerInstanceId;
    @TableField("started_at")
    private OffsetDateTime startedAt;
    @TableField("finished_at")
    private OffsetDateTime finishedAt;
    @TableField("duration_ms")
    private Integer durationMs;
    @TableField("input_summary_json")
    private String inputSummaryJson;
    @TableField("output_summary_json")
    private String outputSummaryJson;
    @TableField("error_code")
    private String errorCode;
    @TableField("error_message")
    private String errorMessage;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskStageRunId() {
        return taskStageRunId;
    }

    public void setTaskStageRunId(String taskStageRunId) {
        this.taskStageRunId = taskStageRunId;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public String getAttemptId() {
        return attemptId;
    }

    public void setAttemptId(String attemptId) {
        this.attemptId = attemptId;
    }

    public String getStageName() {
        return stageName;
    }

    public void setStageName(String stageName) {
        this.stageName = stageName;
    }

    public Integer getStageSeq() {
        return stageSeq;
    }

    public void setStageSeq(Integer stageSeq) {
        this.stageSeq = stageSeq;
    }

    public Integer getClipIndex() {
        return clipIndex;
    }

    public void setClipIndex(Integer clipIndex) {
        this.clipIndex = clipIndex;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getWorkerInstanceId() {
        return workerInstanceId;
    }

    public void setWorkerInstanceId(String workerInstanceId) {
        this.workerInstanceId = workerInstanceId;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(OffsetDateTime finishedAt) {
        this.finishedAt = finishedAt;
    }

    public Integer getDurationMs() {
        return durationMs;
    }

    public void setDurationMs(Integer durationMs) {
        this.durationMs = durationMs;
    }

    public String getInputSummaryJson() {
        return inputSummaryJson;
    }

    public void setInputSummaryJson(String inputSummaryJson) {
        this.inputSummaryJson = inputSummaryJson;
    }

    public String getOutputSummaryJson() {
        return outputSummaryJson;
    }

    public void setOutputSummaryJson(String outputSummaryJson) {
        this.outputSummaryJson = outputSummaryJson;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public void setErrorCode(String errorCode) {
        this.errorCode = errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public Integer getTimezoneOffsetMinutes() {
        return timezoneOffsetMinutes;
    }

    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) {
        this.timezoneOffsetMinutes = timezoneOffsetMinutes;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

    public Integer getIsDeleted() {
        return isDeleted;
    }

    public void setIsDeleted(Integer isDeleted) {
        this.isDeleted = isDeleted;
    }
}
