package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

/**
 * 任务工作节点Runner时长Normalization相关测试。
 */
class TaskWorkerRunnerDurationNormalizationTest {

    /**
     * 规范化片段时长规划PromotesUnsupportedOneSecondClips转为Supported时长。
     */
    @Test
    void normalizeClipDurationPlanPromotesUnsupportedOneSecondClipsToSupportedDuration() {
        MockEnvironment environment = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "0")
            .withProperty("spring.config.additional-location", "file:src/test/resources/task-duration-config/");
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(environment));

        List<int[]> normalized = planner.normalizeClipDurationPlan(
            "seedance-1.5-pro",
            List.of(new int[] {1, 1, 1})
        );

        assertEquals(1, normalized.size());
        assertArrayEquals(new int[] {6, 6, 6}, normalized.get(0));
    }

    /**
     * 规范化片段时长规划KeepsSupportedRangesAndChoosesClosestTarget。
     */
    @Test
    void normalizeClipDurationPlanKeepsSupportedRangesAndChoosesClosestTarget() {
        MockEnvironment environment = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "0")
            .withProperty("spring.config.additional-location", "file:src/test/resources/task-duration-config/");
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(environment));

        List<int[]> normalized = planner.normalizeClipDurationPlan(
            "seedance-1.5-pro",
            List.of(new int[] {7, 5, 11})
        );

        assertEquals(1, normalized.size());
        assertArrayEquals(new int[] {8, 6, 10}, normalized.get(0));
    }
}
