package com.jiandou.api.auth.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.auth.domain.UserRole;
import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.auth.web.dto.AuthSessionResponse;
import com.jiandou.api.auth.web.dto.LoginRequest;
import com.jiandou.api.common.exception.ApiException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.context.SecurityContextRepository;

class AuthApplicationServiceTest {

    @Test
    void loginCreatesSessionAndReturnsAuthenticatedUser() {
        MybatisAuthRepository repository = mock(MybatisAuthRepository.class);
        PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);
        SecurityContextRepository securityContextRepository = mock(SecurityContextRepository.class);
        AuthApplicationService service = new AuthApplicationService(repository, passwordEncoder, securityContextRepository);
        SysUserEntity user = activeUser();
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();

        when(repository.findUserByUsername("tester")).thenReturn(user);
        when(repository.findUserById(1L)).thenReturn(user);
        when(passwordEncoder.matches("secret123", "encoded-password")).thenReturn(true);

        AuthSessionResponse result = service.login(new LoginRequest("tester", "secret123"), request, response);

        assertTrue(result.authenticated());
        assertEquals("tester", result.user().username());
        verify(repository).updateLastLoginAt(eq(1L), any());
        verify(securityContextRepository).saveContext(any(), eq(request), eq(response));
    }

    @Test
    void loginRejectsDisabledUser() {
        MybatisAuthRepository repository = mock(MybatisAuthRepository.class);
        PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);
        SecurityContextRepository securityContextRepository = mock(SecurityContextRepository.class);
        AuthApplicationService service = new AuthApplicationService(repository, passwordEncoder, securityContextRepository);
        SysUserEntity user = activeUser();
        user.setStatus(UserStatus.DISABLED.value());

        when(repository.findUserByUsername("tester")).thenReturn(user);
        when(passwordEncoder.matches("secret123", "encoded-password")).thenReturn(true);

        ApiException exception = assertThrows(
            ApiException.class,
            () -> service.login(new LoginRequest("tester", "secret123"), new MockHttpServletRequest(), new MockHttpServletResponse())
        );

        assertEquals(403, exception.status().value());
        assertEquals("account_disabled", exception.code());
    }

    @Test
    void sessionReturnsAnonymousShapeForUnauthenticatedRequest() {
        AuthApplicationService service = new AuthApplicationService(
            mock(MybatisAuthRepository.class),
            mock(PasswordEncoder.class),
            mock(SecurityContextRepository.class)
        );

        AuthSessionResponse result = service.session(null);

        assertFalse(result.authenticated());
        assertEquals(null, result.user());
    }

    private SysUserEntity activeUser() {
        SysUserEntity user = new SysUserEntity();
        user.setId(1L);
        user.setUsername("tester");
        user.setDisplayName("Tester");
        user.setPasswordHash("encoded-password");
        user.setRole(UserRole.USER.value());
        user.setStatus(UserStatus.ACTIVE.value());
        return user;
    }
}
