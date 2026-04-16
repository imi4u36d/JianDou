package com.jiandou.api.task.infrastructure.mybatis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.OffsetDateTime;
import org.junit.jupiter.api.Test;

class TaskMybatisValueSupportTest {

    @Test
    void valueHelpersConvertAndDefaultInputs() {
        OffsetDateTime now = OffsetDateTime.parse("2026-04-16T00:00:00Z");

        assertEquals("1", TaskMybatisValueSupport.stringValue(1));
        assertEquals(7, TaskMybatisValueSupport.intValue("7", 0));
        assertEquals(3, TaskMybatisValueSupport.intValue(null, 3));
        assertEquals(0, TaskMybatisValueSupport.defaultInt(null));
        assertEquals(5, TaskMybatisValueSupport.defaultInt(5));
        assertEquals(now.toString(), TaskMybatisValueSupport.format(now));
        assertNull(TaskMybatisValueSupport.format(null));
        assertEquals(0L, TaskMybatisValueSupport.defaultLong(null));
        assertEquals(9L, TaskMybatisValueSupport.defaultLong(9L));
        assertEquals(0.0, TaskMybatisValueSupport.defaultDouble(null));
        assertEquals(1.5, TaskMybatisValueSupport.defaultDouble(1.5));
        assertEquals(now, TaskMybatisValueSupport.offsetValue(now.toString()));
        assertNull(TaskMybatisValueSupport.offsetValue(" "));
        assertTrue(TaskMybatisValueSupport.boolValue("yes"));
        assertTrue(TaskMybatisValueSupport.boolValue(1));
        assertFalse(TaskMybatisValueSupport.boolValue("no"));
        assertEquals(8L, TaskMybatisValueSupport.longValue("8", 0L));
        assertEquals(4L, TaskMybatisValueSupport.longValue(null, 4L));
        assertEquals(2.5, TaskMybatisValueSupport.doubleValue("2.5", 0.0));
        assertEquals(1.25, TaskMybatisValueSupport.doubleValue(null, 1.25));
    }
}
