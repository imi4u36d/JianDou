package com.jiandou.api.task;

import org.springframework.stereotype.Component;

@Component
final class TaskWorkerJoinStageService {

    private final JoinOutputService joinOutputService;

    TaskWorkerJoinStageService(JoinOutputService joinOutputService) {
        this.joinOutputService = joinOutputService;
    }

    void scheduleJoin(TaskRecord task) {
        if (task == null || task.id == null || task.id.isBlank()) {
            return;
        }
        int endClipIndex = maxVideoClipIndex(task);
        if (endClipIndex > 1) {
            joinOutputService.scheduleJoin(task.id, endClipIndex);
        }
    }

    private int maxVideoClipIndex(TaskRecord task) {
        int max = 0;
        for (java.util.Map<String, Object> output : task.outputsView()) {
            if (!"video".equalsIgnoreCase(stringValue(output.get("resultType")))) {
                continue;
            }
            max = Math.max(max, intValue(output.get("clipIndex"), 0));
        }
        return max;
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }
}
