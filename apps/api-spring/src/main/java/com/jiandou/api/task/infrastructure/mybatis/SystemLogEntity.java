package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_system_logs")
public class SystemLogEntity {

    @TableId("system_log_id")
    private String systemLogId;
    @TableField("task_id")
    private String taskId;
    @TableField("trace_id")
    private String traceId;
    private String module;
    private String stage;
    private String event;
    private String level;
    private String message;
    @TableField("payload_json")
    private String payloadJson;
    private String source;
    @TableField("service_name")
    private String serviceName;
    @TableField("host_name")
    private String hostName;
    @TableField("logged_at")
    private OffsetDateTime loggedAt;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getSystemLogId() { return systemLogId; }
    public void setSystemLogId(String systemLogId) { this.systemLogId = systemLogId; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getModule() { return module; }
    public void setModule(String module) { this.module = module; }
    public String getStage() { return stage; }
    public void setStage(String stage) { this.stage = stage; }
    public String getEvent() { return event; }
    public void setEvent(String event) { this.event = event; }
    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getPayloadJson() { return payloadJson; }
    public void setPayloadJson(String payloadJson) { this.payloadJson = payloadJson; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public String getServiceName() { return serviceName; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }
    public String getHostName() { return hostName; }
    public void setHostName(String hostName) { this.hostName = hostName; }
    public OffsetDateTime getLoggedAt() { return loggedAt; }
    public void setLoggedAt(OffsetDateTime loggedAt) { this.loggedAt = loggedAt; }
    public Integer getTimezoneOffsetMinutes() { return timezoneOffsetMinutes; }
    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) { this.timezoneOffsetMinutes = timezoneOffsetMinutes; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
