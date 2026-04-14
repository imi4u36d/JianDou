package com.jiandou.api.task.infrastructure.mybatis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;

final class MybatisJsonSupport {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private MybatisJsonSupport() {
    }

    static String write(Object value) {
        try {
            return OBJECT_MAPPER.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to serialize json payload", ex);
        }
    }

    static Map<String, Object> readMap(String value) {
        if (value == null || value.isBlank()) {
            return Map.of();
        }
        try {
            return OBJECT_MAPPER.readValue(value, new TypeReference<>() {});
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse json map", ex);
        }
    }

    static List<String> readStringList(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        try {
            return OBJECT_MAPPER.readValue(value, new TypeReference<>() {});
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse json list", ex);
        }
    }
}
