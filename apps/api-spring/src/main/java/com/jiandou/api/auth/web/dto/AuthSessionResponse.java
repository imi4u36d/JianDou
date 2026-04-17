package com.jiandou.api.auth.web.dto;

/**
 * Session 状态响应。
 * @param authenticated 是否已登录
 * @param user 当前用户
 */
public record AuthSessionResponse(
    boolean authenticated,
    AuthenticatedUserResponse user
) {
}
