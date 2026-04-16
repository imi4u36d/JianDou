package com.jiandou.api.task.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

class TaskExceptionsTest {

    @Test
    void taskExceptionsExposeExpectedState() {
        TaskExecutionAbortedException aborted = new TaskExecutionAbortedException("PAUSED", "stopped");
        TaskNotFoundException notFound = new TaskNotFoundException("task_1");

        assertEquals("PAUSED", aborted.taskStatus());
        assertEquals("stopped", aborted.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, notFound.status());
        assertEquals("task_not_found", notFound.code());
        assertEquals("task not found: task_1", notFound.getMessage());
    }
}
