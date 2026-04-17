package com.jiandou.api.common.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.OffsetDateTime;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

/**
 * 统一写出 API 错误响应。
 */
@Component
public class ApiErrorResponseWriter {

    private final ObjectMapper objectMapper;

    public ApiErrorResponseWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * 输出错误响应。
     * @param request 请求
     * @param response 响应
     * @param status HTTP 状态
     * @param code 错误码
     * @param message 错误消息
     */
    public void write(
        HttpServletRequest request,
        HttpServletResponse response,
        HttpStatus status,
        String code,
        String message
    ) throws IOException {
        if (response.isCommitted()) {
            return;
        }
        response.setStatus(status.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json");
        ApiErrorResponse body = new ApiErrorResponse(
            code,
            status.value(),
            status.getReasonPhrase(),
            message,
            request.getRequestURI(),
            OffsetDateTime.now()
        );
        objectMapper.writeValue(response.getWriter(), body);
    }
}
