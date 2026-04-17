package com.jiandou.api.auth.web.dto;

/**
 * 当前登录用户响应。
 * @param id 主键ID
 * @param username 用户名
 * @param displayName 显示名
 * @param role 角色
 */
public record AuthenticatedUserResponse(
    Long id,
    String username,
    String displayName,
    String role
) {
}
