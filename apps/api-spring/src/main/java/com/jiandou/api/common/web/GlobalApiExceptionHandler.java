package com.jiandou.api.common.web;

import com.jiandou.api.common.exception.ApiException;
import jakarta.servlet.http.HttpServletRequest;
import java.time.OffsetDateTime;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalApiExceptionHandler {

    /**
     * 统一处理业务异常，保证接口返回结构一致。
     */
    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiErrorResponse> handleApiException(ApiException ex, HttpServletRequest request) {
        ApiErrorResponse body = new ApiErrorResponse(
            ex.code(),
            ex.status().value(),
            ex.status().getReasonPhrase(),
            ex.getMessage(),
            request.getRequestURI(),
            OffsetDateTime.now()
        );
        return ResponseEntity.status(ex.status()).body(body);
    }

    /**
     * 统一收口参数校验和业务前置校验失败场景。
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiErrorResponse> handleIllegalArgument(IllegalArgumentException ex, HttpServletRequest request) {
        ApiErrorResponse body = new ApiErrorResponse(
            "bad_request",
            HttpStatus.BAD_REQUEST.value(),
            HttpStatus.BAD_REQUEST.getReasonPhrase(),
            ex.getMessage(),
            request.getRequestURI(),
            OffsetDateTime.now()
        );
        return ResponseEntity.badRequest().body(body);
    }
}
