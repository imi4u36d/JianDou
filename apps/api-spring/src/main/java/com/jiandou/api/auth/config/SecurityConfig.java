package com.jiandou.api.auth.config;

import com.jiandou.api.auth.domain.UserRole;
import com.jiandou.api.auth.security.CsrfCookieFilter;
import com.jiandou.api.auth.security.SessionUserValidationFilter;
import com.jiandou.api.common.web.ApiErrorResponseWriter;
import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.config.JiandouAppProperties;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.boot.web.servlet.server.CookieSameSiteSupplier;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.csrf.InvalidCsrfTokenException;
import org.springframework.security.web.csrf.MissingCsrfTokenException;
import java.util.List;

/**
 * Spring Security 配置。
 */
@Configuration
public class SecurityConfig {

    /**
     * 处理密码编码器。
     * @return 处理结果
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * 处理 SecurityContext 仓储。
     * @return 处理结果
     */
    @Bean
    public SecurityContextRepository securityContextRepository() {
        return new HttpSessionSecurityContextRepository();
    }

    /**
     * 处理 CSRF Token 仓储。
     * @return 处理结果
     */
    @Bean
    public CookieCsrfTokenRepository csrfTokenRepository(JiandouAppProperties appProperties) {
        CookieCsrfTokenRepository repository = CookieCsrfTokenRepository.withHttpOnlyFalse();
        repository.setCookiePath("/");
        repository.setHeaderName("X-XSRF-TOKEN");
        repository.setSecure(appProperties.isCookieSecure());
        repository.setCookieCustomizer((builder) -> builder.sameSite(appProperties.resolveCookieSameSite()));
        return repository;
    }

    @Bean
    public CookieSameSiteSupplier applicationCookieSameSiteSupplier(JiandouAppProperties appProperties) {
        CookieSameSiteSupplier supplier = appProperties.isCookieSecure()
            ? CookieSameSiteSupplier.ofNone()
            : CookieSameSiteSupplier.ofLax();
        return supplier.whenHasNameMatching("^(JSESSIONID|XSRF-TOKEN)$");
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource(JiandouAppProperties appProperties) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(appProperties.resolveWebOrigins());
        configuration.setAllowedMethods(List.of("*"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setExposedHeaders(List.of(CsrfCookieFilter.CSRF_HEADER_NAME));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(1800L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration(ApiPathConstants.API_V2_PATTERN, configuration);
        source.registerCorsConfiguration(ApiPathConstants.STORAGE_PATTERN, configuration);
        return source;
    }

    /**
     * 处理过滤链。
     * @param http http 值
     * @param securityContextRepository context 仓储
     * @param csrfTokenRepository csrf 仓储
     * @param validationFilter session 校验过滤器
     * @param errorResponseWriter 错误输出器
     * @return 处理结果
     * @throws Exception 异常值
     */
    @Bean
    public SecurityFilterChain securityFilterChain(
        HttpSecurity http,
        SecurityContextRepository securityContextRepository,
        CookieCsrfTokenRepository csrfTokenRepository,
        SessionUserValidationFilter validationFilter,
        ApiErrorResponseWriter errorResponseWriter
    ) throws Exception {
        CsrfTokenRequestAttributeHandler csrfRequestHandler = new CsrfTokenRequestAttributeHandler();
        csrfRequestHandler.setCsrfRequestAttributeName("_csrf");
        http
            .cors(Customizer.withDefaults())
            .csrf(csrf -> csrf
                .csrfTokenRepository(csrfTokenRepository)
                .csrfTokenRequestHandler(csrfRequestHandler)
            )
            .securityContext(securityContext -> securityContext.securityContextRepository(securityContextRepository))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
            .authorizeHttpRequests(authorize -> authorize
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .requestMatchers(
                    ApiPathConstants.HEALTH,
                    ApiPathConstants.AUTH_SESSION,
                    ApiPathConstants.AUTH_LOGIN,
                    ApiPathConstants.AUTH_ACTIVATE_INVITE
                ).permitAll()
                .requestMatchers(ApiPathConstants.ADMIN_PATTERN).hasRole(UserRole.ADMIN.value())
                .requestMatchers(ApiPathConstants.API_V2_PATTERN).authenticated()
                .anyRequest().permitAll()
            )
            .exceptionHandling(exceptionHandling -> exceptionHandling
                .authenticationEntryPoint((request, response, ex) -> errorResponseWriter.write(
                    request,
                    response,
                    HttpStatus.UNAUTHORIZED,
                    "unauthorized",
                    "请先登录"
                ))
                .accessDeniedHandler((request, response, ex) -> errorResponseWriter.write(
                    request,
                    response,
                    HttpStatus.FORBIDDEN,
                    resolveAccessDeniedCode(request, ex),
                    resolveAccessDeniedMessage(request, ex)
                ))
            )
            .formLogin(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable)
            .logout(AbstractHttpConfigurer::disable);
        http.addFilterAfter(validationFilter, SecurityContextHolderFilter.class);
        http.addFilterAfter(new CsrfCookieFilter(), CsrfFilter.class);
        return http.build();
    }

    private String resolveAccessDeniedCode(HttpServletRequest request, Exception ex) {
        if (isCsrfException(ex)) {
            return "csrf_invalid";
        }
        return request.getRequestURI().startsWith(ApiPathConstants.ADMIN) ? "admin_forbidden" : "forbidden";
    }

    private String resolveAccessDeniedMessage(HttpServletRequest request, Exception ex) {
        if (isCsrfException(ex)) {
            return "请求校验失败，请刷新页面后重试";
        }
        return request.getRequestURI().startsWith(ApiPathConstants.ADMIN) ? "仅管理员可访问该资源" : "无权限访问该资源";
    }

    private boolean isCsrfException(Exception ex) {
        return ex instanceof MissingCsrfTokenException || ex instanceof InvalidCsrfTokenException;
    }
}
