package com.jiandou.api.common.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

class ApiExceptionTest {

    @Test
    void constructorsExposeStatusCodeMessageAndCause() {
        RuntimeException cause = new RuntimeException("root");
        ApiException withoutCause = new ApiException(HttpStatus.BAD_REQUEST, "bad_request", "bad");
        ApiException withCause = new ApiException(HttpStatus.CONFLICT, "conflict", "boom", cause);

        assertEquals(HttpStatus.BAD_REQUEST, withoutCause.status());
        assertEquals("bad_request", withoutCause.code());
        assertEquals("bad", withoutCause.getMessage());
        assertEquals(HttpStatus.CONFLICT, withCause.status());
        assertEquals("conflict", withCause.code());
        assertEquals("boom", withCause.getMessage());
        assertSame(cause, withCause.getCause());
    }
}
