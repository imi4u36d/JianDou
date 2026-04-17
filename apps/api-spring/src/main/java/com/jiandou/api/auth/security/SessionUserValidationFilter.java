package com.jiandou.api.auth.security;

import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.common.web.ApiErrorResponseWriter;
import com.jiandou.api.config.ApiPathConstants;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 每次请求校验 Session 用户是否仍然有效。
 */
@Component
public class SessionUserValidationFilter extends OncePerRequestFilter {

    private final MybatisAuthRepository authRepository;
    private final ApiErrorResponseWriter errorResponseWriter;

    public SessionUserValidationFilter(
        MybatisAuthRepository authRepository,
        ApiErrorResponseWriter errorResponseWriter
    ) {
        this.authRepository = authRepository;
        this.errorResponseWriter = errorResponseWriter;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith(ApiPathConstants.API_V2);
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
            || !authentication.isAuthenticated()
            || authentication instanceof AnonymousAuthenticationToken
            || !(authentication.getPrincipal() instanceof CurrentUserPrincipal principal)) {
            filterChain.doFilter(request, response);
            return;
        }
        SysUserEntity currentUser = authRepository.findUserById(principal.userId());
        if (currentUser == null || !UserStatus.ACTIVE.value().equals(currentUser.getStatus())) {
            new SecurityContextLogoutHandler().logout(request, response, authentication);
            errorResponseWriter.write(
                request,
                response,
                HttpStatus.UNAUTHORIZED,
                "session_invalid",
                "登录状态已失效，请重新登录"
            );
            return;
        }
        filterChain.doFilter(request, response);
    }
}
