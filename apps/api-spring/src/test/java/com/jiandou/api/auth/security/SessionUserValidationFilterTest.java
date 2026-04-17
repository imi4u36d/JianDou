package com.jiandou.api.auth.security;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.jiandou.api.auth.domain.UserRole;
import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.common.web.ApiErrorResponseWriter;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

class SessionUserValidationFilterTest {

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void disabledUserSessionReturnsUnauthorizedOnNextRequest() throws Exception {
        MybatisAuthRepository repository = mock(MybatisAuthRepository.class);
        ApiErrorResponseWriter writer = new ApiErrorResponseWriter(new ObjectMapper().registerModule(new JavaTimeModule()));
        SessionUserValidationFilter filter = new SessionUserValidationFilter(repository, writer);
        SysUserEntity principalUser = user(UserStatus.ACTIVE);
        SysUserEntity repositoryUser = user(UserStatus.DISABLED);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v2/admin/users");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chainInvoked = new AtomicBoolean(false);

        when(repository.findUserById(1L)).thenReturn(repositoryUser);
        SecurityContextHolder.getContext().setAuthentication(
            UsernamePasswordAuthenticationToken.authenticated(
                CurrentUserPrincipal.from(principalUser),
                null,
                CurrentUserPrincipal.from(principalUser).getAuthorities()
            )
        );

        filter.doFilter(request, response, (servletRequest, servletResponse) -> chainInvoked.set(true));

        assertFalse(chainInvoked.get());
        assertEquals(401, response.getStatus());
        assertTrue(response.getContentAsString().contains("session_invalid"));
    }

    private SysUserEntity user(UserStatus status) {
        SysUserEntity user = new SysUserEntity();
        user.setId(1L);
        user.setUsername("tester");
        user.setDisplayName("Tester");
        user.setRole(UserRole.ADMIN.value());
        user.setStatus(status.value());
        return user;
    }
}
