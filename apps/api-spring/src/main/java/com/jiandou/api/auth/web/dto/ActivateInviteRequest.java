package com.jiandou.api.auth.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 邀请码激活请求。
 * @param code 邀请码
 * @param username 用户名
 * @param displayName 显示名
 * @param password 密码
 */
public record ActivateInviteRequest(
    @NotBlank(message = "邀请码不能为空")
    @Size(max = 64, message = "邀请码长度不能超过 64 个字符")
    String code,
    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名长度不能超过 64 个字符")
    String username,
    @NotBlank(message = "显示名不能为空")
    @Size(max = 128, message = "显示名长度不能超过 128 个字符")
    String displayName,
    @NotBlank(message = "密码不能为空")
    @Size(min = 8, max = 72, message = "密码长度需在 8 到 72 个字符之间")
    String password
) {
}
