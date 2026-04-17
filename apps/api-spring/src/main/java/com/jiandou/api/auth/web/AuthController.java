package com.jiandou.api.auth.web;

import com.jiandou.api.auth.application.AuthApplicationService;
import com.jiandou.api.auth.web.dto.ActivateInviteRequest;
import com.jiandou.api.auth.web.dto.AuthSessionResponse;
import com.jiandou.api.auth.web.dto.LoginRequest;
import com.jiandou.api.config.ApiPathConstants;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证控制器。
 */
@RestController
@RequestMapping(ApiPathConstants.AUTH)
public class AuthController {

    private final AuthApplicationService authApplicationService;

    public AuthController(AuthApplicationService authApplicationService) {
        this.authApplicationService = authApplicationService;
    }

    /**
     * 返回当前会话。
     * @param authentication 当前认证
     * @return 处理结果
     */
    @GetMapping("/session")
    public AuthSessionResponse session(Authentication authentication) {
        return authApplicationService.session(authentication);
    }

    /**
     * 登录。
     * @param request 登录请求
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     * @return 处理结果
     */
    @PostMapping("/login")
    public AuthSessionResponse login(
        @Valid @RequestBody LoginRequest request,
        HttpServletRequest httpRequest,
        HttpServletResponse httpResponse
    ) {
        return authApplicationService.login(request, httpRequest, httpResponse);
    }

    /**
     * 退出登录。
     * @param authentication 当前认证
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     * @return 处理结果
     */
    @PostMapping("/logout")
    public Map<String, Object> logout(
        Authentication authentication,
        HttpServletRequest httpRequest,
        HttpServletResponse httpResponse
    ) {
        authApplicationService.logout(authentication, httpRequest, httpResponse);
        return Map.of("success", true);
    }

    /**
     * 激活邀请码并自动登录。
     * @param request 激活请求
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     * @return 处理结果
     */
    @PostMapping("/activate-invite")
    public AuthSessionResponse activateInvite(
        @Valid @RequestBody ActivateInviteRequest request,
        HttpServletRequest httpRequest,
        HttpServletResponse httpResponse
    ) {
        return authApplicationService.activateInvite(request, httpRequest, httpResponse);
    }
}
