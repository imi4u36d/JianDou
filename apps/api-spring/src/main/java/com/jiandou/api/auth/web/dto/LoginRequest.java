package com.jiandou.api.auth.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 登录请求。
 * @param username 用户名
 * @param password 密码
 */
public record LoginRequest(
    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名长度不能超过 64 个字符")
    String username,
    @NotBlank(message = "密码不能为空")
    @Size(max = 72, message = "密码长度不能超过 72 个字符")
    String password
) {
}
