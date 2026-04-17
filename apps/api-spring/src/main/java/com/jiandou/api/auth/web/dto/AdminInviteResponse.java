package com.jiandou.api.auth.web.dto;

import java.time.OffsetDateTime;

/**
 * 管理端邀请码响应。
 * @param id 主键ID
 * @param code 邀请码
 * @param role 角色
 * @param status 状态
 * @param expiresAt 过期时间
 * @param createdBy 创建人
 * @param usedBy 使用人
 * @param usedAt 使用时间
 * @param createdAt 创建时间
 * @param updatedAt 更新时间
 */
public record AdminInviteResponse(
    Long id,
    String code,
    String role,
    String status,
    OffsetDateTime expiresAt,
    AdminInviteActorResponse createdBy,
    AdminInviteActorResponse usedBy,
    OffsetDateTime usedAt,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
}
