package com.jiandou.api.task.runtime;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskResultTypes;
import org.springframework.stereotype.Component;

/**
 * 任务工作节点拼接阶段服务。
 */
@Component
class TaskWorkerJoinStageService {

    private final JoinOutputService joinOutputService;

    TaskWorkerJoinStageService(JoinOutputService joinOutputService) {
        this.joinOutputService = joinOutputService;
    }

    /**
     * 处理调度拼接。
     * @param task 要处理的任务对象
     */
    void scheduleJoin(TaskRecord task) {
        if (task == null || task.id() == null || task.id().isBlank()) {
            return;
        }
        int endClipIndex = maxVideoClipIndex(task);
        if (endClipIndex > 1) {
            joinOutputService.scheduleJoin(task.id(), endClipIndex);
        }
    }

    /**
     * 处理最大视频片段索引。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private int maxVideoClipIndex(TaskRecord task) {
        int max = 0;
        for (java.util.Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.get("resultType"))) {
                continue;
            }
            max = Math.max(max, intValue(output.get("clipIndex"), 0));
        }
        return max;
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param defaultValue 默认值
     * @return 处理结果
     */
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
