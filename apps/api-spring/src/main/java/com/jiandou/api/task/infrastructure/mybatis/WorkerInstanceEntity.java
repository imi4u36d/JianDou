package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_worker_instances")
public class WorkerInstanceEntity {

    @TableId("worker_instance_id")
    private String workerInstanceId;
    @TableField("worker_type")
    private String workerType;
    @TableField("queue_name")
    private String queueName;
    @TableField("host_name")
    private String hostName;
    @TableField("process_id")
    private Integer processId;
    private String status;
    @TableField("started_at")
    private OffsetDateTime startedAt;
    @TableField("last_heartbeat_at")
    private OffsetDateTime lastHeartbeatAt;
    @TableField("stopped_at")
    private OffsetDateTime stoppedAt;
    @TableField("metadata_json")
    private String metadataJson;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getWorkerInstanceId() {
        return workerInstanceId;
    }

    public void setWorkerInstanceId(String workerInstanceId) {
        this.workerInstanceId = workerInstanceId;
    }

    public String getWorkerType() {
        return workerType;
    }

    public void setWorkerType(String workerType) {
        this.workerType = workerType;
    }

    public String getQueueName() {
        return queueName;
    }

    public void setQueueName(String queueName) {
        this.queueName = queueName;
    }

    public String getHostName() {
        return hostName;
    }

    public void setHostName(String hostName) {
        this.hostName = hostName;
    }

    public Integer getProcessId() {
        return processId;
    }

    public void setProcessId(Integer processId) {
        this.processId = processId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public OffsetDateTime getLastHeartbeatAt() {
        return lastHeartbeatAt;
    }

    public void setLastHeartbeatAt(OffsetDateTime lastHeartbeatAt) {
        this.lastHeartbeatAt = lastHeartbeatAt;
    }

    public OffsetDateTime getStoppedAt() {
        return stoppedAt;
    }

    public void setStoppedAt(OffsetDateTime stoppedAt) {
        this.stoppedAt = stoppedAt;
    }

    public String getMetadataJson() {
        return metadataJson;
    }

    public void setMetadataJson(String metadataJson) {
        this.metadataJson = metadataJson;
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
