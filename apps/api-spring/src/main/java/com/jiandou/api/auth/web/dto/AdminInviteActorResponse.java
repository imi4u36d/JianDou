package com.jiandou.api.auth.web.dto;

/**
 * 邀请码关联用户响应。
 * @param id 主键ID
 * @param username 用户名
 * @param displayName 显示名
 */
public record AdminInviteActorResponse(
    Long id,
    String username,
    String displayName
) {
}
