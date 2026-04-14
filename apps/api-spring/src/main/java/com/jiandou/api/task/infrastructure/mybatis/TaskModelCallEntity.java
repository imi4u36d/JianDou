package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.OffsetDateTime;

@TableName("biz_task_model_calls")
public class TaskModelCallEntity {

    @TableId("task_model_call_id")
    private String taskModelCallId;
    @TableField("task_id")
    private String taskId;
    @TableField("call_kind")
    private String callKind;
    private String stage;
    private String operation;
    private String provider;
    @TableField("provider_model")
    private String providerModel;
    @TableField("requested_model")
    private String requestedModel;
    @TableField("resolved_model")
    private String resolvedModel;
    @TableField("model_name")
    private String modelName;
    @TableField("model_alias")
    private String modelAlias;
    @TableField("endpoint_host")
    private String endpointHost;
    @TableField("request_id")
    private String requestId;
    @TableField("request_payload_json")
    private String requestPayloadJson;
    @TableField("response_payload_json")
    private String responsePayloadJson;
    @TableField("http_status")
    private Integer httpStatus;
    @TableField("response_status_code")
    private Integer responseStatusCode;
    private Integer success;
    @TableField("error_code")
    private String errorCode;
    @TableField("error_message")
    private String errorMessage;
    @TableField("latency_ms")
    private Integer latencyMs;
    @TableField("duration_ms")
    private Integer durationMs;
    @TableField("input_tokens")
    private Integer inputTokens;
    @TableField("output_tokens")
    private Integer outputTokens;
    @TableField("started_at")
    private OffsetDateTime startedAt;
    @TableField("finished_at")
    private OffsetDateTime finishedAt;
    @TableField("timezone_offset_minutes")
    private Integer timezoneOffsetMinutes;
    @TableField("create_time")
    private OffsetDateTime createTime;
    @TableField("update_time")
    private OffsetDateTime updateTime;
    @TableField("is_deleted")
    private Integer isDeleted;

    public String getTaskModelCallId() { return taskModelCallId; }
    public void setTaskModelCallId(String taskModelCallId) { this.taskModelCallId = taskModelCallId; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getCallKind() { return callKind; }
    public void setCallKind(String callKind) { this.callKind = callKind; }
    public String getStage() { return stage; }
    public void setStage(String stage) { this.stage = stage; }
    public String getOperation() { return operation; }
    public void setOperation(String operation) { this.operation = operation; }
    public String getProvider() { return provider; }
    public void setProvider(String provider) { this.provider = provider; }
    public String getProviderModel() { return providerModel; }
    public void setProviderModel(String providerModel) { this.providerModel = providerModel; }
    public String getRequestedModel() { return requestedModel; }
    public void setRequestedModel(String requestedModel) { this.requestedModel = requestedModel; }
    public String getResolvedModel() { return resolvedModel; }
    public void setResolvedModel(String resolvedModel) { this.resolvedModel = resolvedModel; }
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }
    public String getModelAlias() { return modelAlias; }
    public void setModelAlias(String modelAlias) { this.modelAlias = modelAlias; }
    public String getEndpointHost() { return endpointHost; }
    public void setEndpointHost(String endpointHost) { this.endpointHost = endpointHost; }
    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getRequestPayloadJson() { return requestPayloadJson; }
    public void setRequestPayloadJson(String requestPayloadJson) { this.requestPayloadJson = requestPayloadJson; }
    public String getResponsePayloadJson() { return responsePayloadJson; }
    public void setResponsePayloadJson(String responsePayloadJson) { this.responsePayloadJson = responsePayloadJson; }
    public Integer getHttpStatus() { return httpStatus; }
    public void setHttpStatus(Integer httpStatus) { this.httpStatus = httpStatus; }
    public Integer getResponseStatusCode() { return responseStatusCode; }
    public void setResponseStatusCode(Integer responseStatusCode) { this.responseStatusCode = responseStatusCode; }
    public Integer getSuccess() { return success; }
    public void setSuccess(Integer success) { this.success = success; }
    public String getErrorCode() { return errorCode; }
    public void setErrorCode(String errorCode) { this.errorCode = errorCode; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public Integer getLatencyMs() { return latencyMs; }
    public void setLatencyMs(Integer latencyMs) { this.latencyMs = latencyMs; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public Integer getInputTokens() { return inputTokens; }
    public void setInputTokens(Integer inputTokens) { this.inputTokens = inputTokens; }
    public Integer getOutputTokens() { return outputTokens; }
    public void setOutputTokens(Integer outputTokens) { this.outputTokens = outputTokens; }
    public OffsetDateTime getStartedAt() { return startedAt; }
    public void setStartedAt(OffsetDateTime startedAt) { this.startedAt = startedAt; }
    public OffsetDateTime getFinishedAt() { return finishedAt; }
    public void setFinishedAt(OffsetDateTime finishedAt) { this.finishedAt = finishedAt; }
    public Integer getTimezoneOffsetMinutes() { return timezoneOffsetMinutes; }
    public void setTimezoneOffsetMinutes(Integer timezoneOffsetMinutes) { this.timezoneOffsetMinutes = timezoneOffsetMinutes; }
    public OffsetDateTime getCreateTime() { return createTime; }
    public void setCreateTime(OffsetDateTime createTime) { this.createTime = createTime; }
    public OffsetDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(OffsetDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getIsDeleted() { return isDeleted; }
    public void setIsDeleted(Integer isDeleted) { this.isDeleted = isDeleted; }
}
