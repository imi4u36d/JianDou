package com.jiandou.api.auth.application;

import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.auth.security.CurrentUserPrincipal;
import com.jiandou.api.auth.web.dto.ActivateInviteRequest;
import com.jiandou.api.auth.web.dto.AuthSessionResponse;
import com.jiandou.api.auth.web.dto.AuthenticatedUserResponse;
import com.jiandou.api.auth.web.dto.LoginRequest;
import com.jiandou.api.common.exception.ApiException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.time.OffsetDateTime;
import java.util.regex.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.stereotype.Service;

/**
 * 认证应用服务。
 */
@Service
public class AuthApplicationService {

    private static final Pattern USERNAME_PATTERN = Pattern.compile("^[a-zA-Z0-9._-]{3,32}$");

    private final MybatisAuthRepository authRepository;
    private final PasswordEncoder passwordEncoder;
    private final SecurityContextRepository securityContextRepository;

    public AuthApplicationService(
        MybatisAuthRepository authRepository,
        PasswordEncoder passwordEncoder,
        SecurityContextRepository securityContextRepository
    ) {
        this.authRepository = authRepository;
        this.passwordEncoder = passwordEncoder;
        this.securityContextRepository = securityContextRepository;
    }

    /**
     * 返回当前会话。
     * @param authentication 认证信息
     * @return 处理结果
     */
    public AuthSessionResponse session(Authentication authentication) {
        if (authentication == null
            || !authentication.isAuthenticated()
            || authentication instanceof AnonymousAuthenticationToken
            || !(authentication.getPrincipal() instanceof CurrentUserPrincipal principal)) {
            return new AuthSessionResponse(false, null);
        }
        SysUserEntity user = authRepository.findUserById(principal.userId());
        if (user == null || !UserStatus.ACTIVE.value().equals(user.getStatus())) {
            return new AuthSessionResponse(false, null);
        }
        return new AuthSessionResponse(true, toUserResponse(user));
    }

    /**
     * 执行登录。
     * @param request 登录请求
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     * @return 处理结果
     */
    public AuthSessionResponse login(LoginRequest request, HttpServletRequest httpRequest, HttpServletResponse httpResponse) {
        String username = validateUsername(request.username());
        String password = validatePassword(request.password());
        SysUserEntity user = authRepository.findUserByUsername(username);
        if (user == null || !passwordEncoder.matches(password, user.getPasswordHash())) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "invalid_credentials", "用户名或密码错误");
        }
        ensureActiveUser(user);
        return establishSession(user, httpRequest, httpResponse);
    }

    /**
     * 激活邀请码并自动登录。
     * @param request 激活请求
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     * @return 处理结果
     */
    public AuthSessionResponse activateInvite(
        ActivateInviteRequest request,
        HttpServletRequest httpRequest,
        HttpServletResponse httpResponse
    ) {
        String code = validateInviteCode(request.code());
        String username = validateUsername(request.username());
        String displayName = validateDisplayName(request.displayName());
        String password = validatePassword(request.password());
        SysUserEntity user = authRepository.activateInvite(code, username, displayName, passwordEncoder.encode(password));
        return establishSession(user, httpRequest, httpResponse);
    }

    /**
     * 执行退出登录。
     * @param authentication 当前认证
     * @param httpRequest servlet 请求
     * @param httpResponse servlet 响应
     */
    public void logout(Authentication authentication, HttpServletRequest httpRequest, HttpServletResponse httpResponse) {
        new SecurityContextLogoutHandler().logout(httpRequest, httpResponse, authentication);
    }

    /**
     * 校验用户名格式。
     * @param username 用户名
     * @return 处理结果
     */
    public static String validateUsername(String username) {
        String normalized = MybatisAuthRepository.normalizeUsername(username);
        if (!USERNAME_PATTERN.matcher(normalized).matches()) {
            throw new ApiException(
                HttpStatus.BAD_REQUEST,
                "invalid_username",
                "用户名需为 3 到 32 位，仅支持字母、数字、点、下划线和中划线"
            );
        }
        return normalized;
    }

    /**
     * 校验显示名。
     * @param displayName 显示名
     * @return 处理结果
     */
    public static String validateDisplayName(String displayName) {
        String normalized = displayName == null ? "" : displayName.trim();
        if (normalized.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid_display_name", "显示名不能为空");
        }
        if (normalized.length() > 128) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid_display_name", "显示名长度不能超过 128 个字符");
        }
        return normalized;
    }

    /**
     * 校验密码。
     * @param password 密码
     * @return 处理结果
     */
    public static String validatePassword(String password) {
        String normalized = password == null ? "" : password.trim();
        if (normalized.length() < 8 || normalized.length() > 72) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid_password", "密码长度需在 8 到 72 个字符之间");
        }
        return normalized;
    }

    /**
     * 校验邀请码。
     * @param code 邀请码
     * @return 处理结果
     */
    public static String validateInviteCode(String code) {
        String normalized = MybatisAuthRepository.normalizeInviteCode(code);
        if (normalized.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid_invite_code", "邀请码不能为空");
        }
        return normalized;
    }

    private void ensureActiveUser(SysUserEntity user) {
        if (!UserStatus.ACTIVE.value().equals(user.getStatus())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "account_disabled", "账号已被禁用");
        }
    }

    private AuthSessionResponse establishSession(
        SysUserEntity user,
        HttpServletRequest httpRequest,
        HttpServletResponse httpResponse
    ) {
        SecurityContextHolder.clearContext();
        HttpSession existingSession = httpRequest.getSession(false);
        if (existingSession != null) {
            existingSession.invalidate();
        }
        httpRequest.getSession(true);
        OffsetDateTime loginTime = OffsetDateTime.now();
        CurrentUserPrincipal principal = CurrentUserPrincipal.from(user);
        Authentication authentication = UsernamePasswordAuthenticationToken.authenticated(
            principal,
            null,
            principal.getAuthorities()
        );
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(authentication);
        SecurityContextHolder.setContext(context);
        securityContextRepository.saveContext(context, httpRequest, httpResponse);
        authRepository.updateLastLoginAt(user.getId(), loginTime);
        SysUserEntity refreshed = authRepository.findUserById(user.getId());
        return new AuthSessionResponse(true, toUserResponse(refreshed == null ? user : refreshed));
    }

    private AuthenticatedUserResponse toUserResponse(SysUserEntity user) {
        return new AuthenticatedUserResponse(
            user.getId(),
            user.getUsername(),
            user.getDisplayName(),
            user.getRole()
        );
    }
}
