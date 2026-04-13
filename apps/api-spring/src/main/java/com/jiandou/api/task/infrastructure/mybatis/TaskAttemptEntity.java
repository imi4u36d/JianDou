package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_task_attempts")
public class TaskAttemptEntity {

    @TableId("task_attempt_id")
    private String taskAttemptId;
    @TableField("task_id")
    private String taskId;
    @TableField("attempt_no")
    private Integer attemptNo;
    @TableField("trigger_type")
    private String triggerType;
    private String status;
    @TableField("queue_name")
    private String queueName;
    @TableField("worker_instance_id")
    private String workerInstanceId;
    @TableField("queue_entered_at")
    private OffsetDateTime queueEnteredAt;
    @TableField("queue_left_at")
    private OffsetDateTime queueLeftAt;
    @TableField("claimed_at")
    private OffsetDateTime claimedAt;
    @TableField
    private OffsetDateTime startedAt;
    @TableField
    private OffsetDateTime finishedAt;
    @TableField("resume_from_stage")
    private String resumeFromStage;
    @TableField("resume_from_clip_index")
    private Integer resumeFromClipIndex;
    @TableField("failure_code")
    private String failureCode;
    @TableField("failure_message")
    private String failureMessage;
    @TableField("payload_json")
    private String payloadJson;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskAttemptId() {
        return taskAttemptId;
    }

    public void setTaskAttemptId(String taskAttemptId) {
        this.taskAttemptId = taskAttemptId;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public Integer getAttemptNo() {
        return attemptNo;
    }

    public void setAttemptNo(Integer attemptNo) {
        this.attemptNo = attemptNo;
    }

    public String getTriggerType() {
        return triggerType;
    }

    public void setTriggerType(String triggerType) {
        this.triggerType = triggerType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getQueueName() {
        return queueName;
    }

    public void setQueueName(String queueName) {
        this.queueName = queueName;
    }

    public String getWorkerInstanceId() {
        return workerInstanceId;
    }

    public void setWorkerInstanceId(String workerInstanceId) {
        this.workerInstanceId = workerInstanceId;
    }

    public OffsetDateTime getQueueEnteredAt() {
        return queueEnteredAt;
    }

    public void setQueueEnteredAt(OffsetDateTime queueEnteredAt) {
        this.queueEnteredAt = queueEnteredAt;
    }

    public OffsetDateTime getQueueLeftAt() {
        return queueLeftAt;
    }

    public void setQueueLeftAt(OffsetDateTime queueLeftAt) {
        this.queueLeftAt = queueLeftAt;
    }

    public OffsetDateTime getClaimedAt() {
        return claimedAt;
    }

    public void setClaimedAt(OffsetDateTime claimedAt) {
        this.claimedAt = claimedAt;
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

    public String getResumeFromStage() {
        return resumeFromStage;
    }

    public void setResumeFromStage(String resumeFromStage) {
        this.resumeFromStage = resumeFromStage;
    }

    public Integer getResumeFromClipIndex() {
        return resumeFromClipIndex;
    }

    public void setResumeFromClipIndex(Integer resumeFromClipIndex) {
        this.resumeFromClipIndex = resumeFromClipIndex;
    }

    public String getFailureCode() {
        return failureCode;
    }

    public void setFailureCode(String failureCode) {
        this.failureCode = failureCode;
    }

    public String getFailureMessage() {
        return failureMessage;
    }

    public void setFailureMessage(String failureMessage) {
        this.failureMessage = failureMessage;
    }

    public String getPayloadJson() {
        return payloadJson;
    }

    public void setPayloadJson(String payloadJson) {
        this.payloadJson = payloadJson;
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
