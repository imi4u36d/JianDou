package com.jiandou.api.admin.dto;

/**
 * 管理端模型配置草稿校验响应体。
 * @param valid 是否通过校验
 * @param snapshot 校验后的快照值
 * @return 处理结果
 */
public record AdminModelConfigValidationResponse(
    boolean valid,
    AdminModelConfigResponse snapshot
) {
}
