package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_task_queue_events")
public class TaskQueueEventEntity {

    @TableId("task_queue_event_id")
    private String taskQueueEventId;
    @TableField("task_id")
    private String taskId;
    @TableField("attempt_id")
    private String attemptId;
    @TableField("queue_name")
    private String queueName;
    @TableField("event_type")
    private String eventType;
    @TableField("worker_instance_id")
    private String workerInstanceId;
    @TableField("queue_position_hint")
    private Integer queuePositionHint;
    @TableField("payload_json")
    private String payloadJson;
    @TableField("event_time")
    private OffsetDateTime eventTime;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskQueueEventId() {
        return taskQueueEventId;
    }

    public void setTaskQueueEventId(String taskQueueEventId) {
        this.taskQueueEventId = taskQueueEventId;
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

    public String getQueueName() {
        return queueName;
    }

    public void setQueueName(String queueName) {
        this.queueName = queueName;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(String eventType) {
        this.eventType = eventType;
    }

    public String getWorkerInstanceId() {
        return workerInstanceId;
    }

    public void setWorkerInstanceId(String workerInstanceId) {
        this.workerInstanceId = workerInstanceId;
    }

    public Integer getQueuePositionHint() {
        return queuePositionHint;
    }

    public void setQueuePositionHint(Integer queuePositionHint) {
        this.queuePositionHint = queuePositionHint;
    }

    public String getPayloadJson() {
        return payloadJson;
    }

    public void setPayloadJson(String payloadJson) {
        this.payloadJson = payloadJson;
    }

    public OffsetDateTime getEventTime() {
        return eventTime;
    }

    public void setEventTime(OffsetDateTime eventTime) {
        this.eventTime = eventTime;
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
