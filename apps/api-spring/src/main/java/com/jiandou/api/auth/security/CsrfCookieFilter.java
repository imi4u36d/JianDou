package com.jiandou.api.auth.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 确保 CSRF Cookie 被下发。
 */
public class CsrfCookieFilter extends OncePerRequestFilter {

    public static final String CSRF_HEADER_NAME = "X-XSRF-TOKEN";

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        CsrfToken csrfToken = resolveToken(request);
        if (csrfToken != null) {
            writeTokenHeader(response, csrfToken);
        }
        filterChain.doFilter(request, response);
        csrfToken = resolveToken(request);
        writeTokenHeader(response, csrfToken);
    }

    private CsrfToken resolveToken(HttpServletRequest request) {
        Object value = request.getAttribute(CsrfToken.class.getName());
        if (value instanceof CsrfToken csrfToken) {
            return csrfToken;
        }
        value = request.getAttribute("_csrf");
        if (value instanceof CsrfToken csrfToken) {
            return csrfToken;
        }
        return null;
    }

    private void writeTokenHeader(HttpServletResponse response, CsrfToken csrfToken) {
        if (csrfToken == null || response.isCommitted()) {
            return;
        }
        response.setHeader(CSRF_HEADER_NAME, csrfToken.getToken());
    }
}
