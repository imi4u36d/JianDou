package com.jiandou.api.auth.web.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.OffsetDateTime;

/**
 * 创建邀请码请求。
 * @param role 角色
 * @param expiresAt 过期时间
 */
public record CreateInviteRequest(
    @NotBlank(message = "角色不能为空")
    String role,
    OffsetDateTime expiresAt
) {
}
