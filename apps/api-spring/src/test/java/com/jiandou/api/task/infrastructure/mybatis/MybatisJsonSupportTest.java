package com.jiandou.api.task.infrastructure.mybatis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MybatisJsonSupportTest {

    @Test
    void writeAndReadHelpersRoundTripJsonValues() {
        String json = MybatisJsonSupport.write(Map.of("taskId", "task_1"));

        assertTrue(json.contains("task_1"));
        assertEquals(Map.of("taskId", "task_1"), MybatisJsonSupport.readMap(json));
        assertEquals(List.of("a", "b"), MybatisJsonSupport.readStringList("[\"a\",\"b\"]"));
        assertEquals(Map.of(), MybatisJsonSupport.readMap(" "));
        assertEquals(List.of(), MybatisJsonSupport.readStringList(null));
    }

    @Test
    void invalidJsonThrowsIllegalArgumentException() {
        assertThrows(IllegalArgumentException.class, () -> MybatisJsonSupport.readMap("{bad"));
        assertThrows(IllegalArgumentException.class, () -> MybatisJsonSupport.readStringList("[bad"));
    }
}
