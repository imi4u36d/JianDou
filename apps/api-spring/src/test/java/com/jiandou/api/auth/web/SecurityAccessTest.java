package com.jiandou.api.auth.web;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.cookie;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jiandou.api.auth.application.AdminIdentityService;
import com.jiandou.api.auth.application.AuthApplicationService;
import com.jiandou.api.auth.config.SecurityConfig;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.security.SessionUserValidationFilter;
import com.jiandou.api.auth.web.dto.AuthSessionResponse;
import com.jiandou.api.common.web.ApiErrorResponseWriter;
import com.jiandou.api.config.JiandouAppProperties;
import com.jiandou.api.config.JiandouStorageProperties;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.http.MediaType;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@WebMvcTest(controllers = {AuthController.class, AdminIdentityController.class})
@Import({SecurityConfig.class, SessionUserValidationFilter.class, ApiErrorResponseWriter.class, SecurityAccessTest.TestConfig.class})
class SecurityAccessTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AuthApplicationService authApplicationService;

    @MockBean
    private AdminIdentityService adminIdentityService;

    @MockBean
    private MybatisAuthRepository authRepository;

    @Test
    void authSessionEndpointIsPublic() throws Exception {
        when(authApplicationService.session(any())).thenReturn(new AuthSessionResponse(false, null));

        mockMvc.perform(get("/api/v2/auth/session"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.authenticated").value(false));
    }

    @Test
    void authSessionEndpointIssuesCsrfCookieAndHeader() throws Exception {
        when(authApplicationService.session(any())).thenReturn(new AuthSessionResponse(false, null));

        mockMvc.perform(get("/api/v2/auth/session"))
            .andExpect(status().isOk())
            .andExpect(cookie().exists("XSRF-TOKEN"))
            .andExpect(header().exists("X-XSRF-TOKEN"));
    }

    @Test
    void loginEndpointRejectsMissingCsrfToken() throws Exception {
        mockMvc.perform(post("/api/v2/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "tester",
                      "password": "secret123"
                    }
                    """))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("csrf_invalid"));
    }

    @Test
    void loginEndpointAcceptsValidCsrfToken() throws Exception {
        when(authApplicationService.session(any())).thenReturn(new AuthSessionResponse(false, null));
        when(authApplicationService.login(any(), any(), any())).thenReturn(new AuthSessionResponse(true, null));

        MvcResult csrfResult = mockMvc.perform(get("/api/v2/auth/session"))
            .andExpect(status().isOk())
            .andReturn();

        Cookie csrfCookie = csrfResult.getResponse().getCookie("XSRF-TOKEN");
        String csrfHeader = csrfResult.getResponse().getHeader("X-XSRF-TOKEN");

        mockMvc.perform(post("/api/v2/auth/login")
                .cookie(csrfCookie)
                .header("X-XSRF-TOKEN", csrfHeader)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "tester",
                      "password": "secret123"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.authenticated").value(true));
    }

    @Test
    void anonymousUserGetsUnauthorizedForAdminEndpoint() throws Exception {
        mockMvc.perform(get("/api/v2/admin/users"))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.code").value("unauthorized"));
    }

    @Test
    void normalUserGetsForbiddenForAdminEndpoint() throws Exception {
        mockMvc.perform(get("/api/v2/admin/users").with(user("tester").roles("USER")))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("admin_forbidden"));
    }

    @TestConfiguration
    static class TestConfig {

        @Bean
        JiandouAppProperties jiandouAppProperties() {
            JiandouAppProperties properties = new JiandouAppProperties();
            properties.setWebOrigin("http://localhost:5173");
            return properties;
        }

        @Bean
        JiandouStorageProperties jiandouStorageProperties() {
            return new JiandouStorageProperties();
        }
    }
}
