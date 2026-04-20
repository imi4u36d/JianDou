package com.jiandou.api.workflow.infrastructure;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;

public final class WorkflowJsonSupport {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private WorkflowJsonSupport() {
    }

    public static String write(Object value) {
        try {
            return OBJECT_MAPPER.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to serialize json payload", ex);
        }
    }

    public static Map<String, Object> readMap(String value) {
        if (value == null || value.isBlank()) {
            return Map.of();
        }
        try {
            return OBJECT_MAPPER.readValue(value, new TypeReference<>() {});
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse json map", ex);
        }
    }

    public static List<Map<String, Object>> readMapList(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        try {
            return OBJECT_MAPPER.readValue(value, new TypeReference<>() {});
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse json map list", ex);
        }
    }

    public static List<String> readStringList(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        try {
            return OBJECT_MAPPER.readValue(value, new TypeReference<>() {});
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse json string list", ex);
        }
    }
}
