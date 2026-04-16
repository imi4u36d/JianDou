package com.jiandou.api.common.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.jiandou.api.task.exception.TaskNotFoundException;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;

class GlobalApiExceptionHandlerTest {

    private final GlobalApiExceptionHandler handler = new GlobalApiExceptionHandler();

    @Test
    void handleApiExceptionUsesBusinessStatusAndCode() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v2/tasks/task_1");

        var response = handler.handleApiException(new TaskNotFoundException("task_1"), request);

        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("task_not_found", response.getBody().code());
        assertEquals(404, response.getBody().status());
        assertEquals("Not Found", response.getBody().error());
        assertEquals("task not found: task_1", response.getBody().message());
        assertEquals("/api/v2/tasks/task_1", response.getBody().path());
        assertNotNull(response.getBody().timestamp());
    }

    @Test
    void handleIllegalArgumentMapsToBadRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v2/uploads/texts");

        var response = handler.handleIllegalArgument(new IllegalArgumentException("bad input"), request);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("bad_request", response.getBody().code());
        assertEquals(400, response.getBody().status());
        assertEquals("Bad Request", response.getBody().error());
        assertEquals("bad input", response.getBody().message());
        assertEquals("/api/v2/uploads/texts", response.getBody().path());
        assertNotNull(response.getBody().timestamp());
    }
}
