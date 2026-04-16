package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.jiandou.api.task.application.TaskStoryboardPlanner;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

/**
 * 任务分镜规划器Parsing相关测试。
 */
class TaskStoryboardPlannerParsingTest {

    /**
     * 处理parsesStrictMergedNarrative分镜Table。
     */
    @Test
    void parsesStrictMergedNarrativeStoryboardTable() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 景别/运镜 | 剧情画面与声音描述（长段） | 时长 |
            | :--- | :--- | :--- | :--- |
            | 001 | 中景/缓慢推近 | 雨夜码头的冷白灯下，黑色风衣的男人贴着生锈集装箱前行，右手一直按着耳机，呼吸急促但克制；镜头推进时他突然停住，侧头听见远处铁门震动，低声说“他们来了”，随后环境里只剩风声和脚步摩擦声。 | 10s |
            | 002 | 近景/手持跟随 | 镜头贴近他的侧脸，雨水沿着下颌滴落，他转身冲进狭窄通道，肩膀几次擦过墙面，动作急促但不失重心；这一段无人声，仅环境声，金属回响和急促脚步连续压迫画面。 | 10s |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> ranges = planner.extractStoryboardShotDurationRanges(storyboardMarkdown);

        assertEquals(2, shotPlans.size());
        assertTrue(shotPlans.get(0).imagePrompt().contains("雨夜码头"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("雨夜码头"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("运镜：缓慢推近"));
        assertTrue(shotPlans.get(1).videoPrompt().contains("无人声，仅环境声"));
        assertArrayEquals(new int[] {10, 10}, ranges.get(0));
        assertArrayEquals(new int[] {10, 10}, ranges.get(1));
    }

    /**
     * 处理supportsMergedDescriptionAliasColumn。
     */
    @Test
    void supportsMergedDescriptionAliasColumn() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 合并长段描述 | 时长 |
            | :--- | :--- | :--- |
            | 001 | 破旧仓库的顶灯忽明忽暗，女孩靠着木箱缓慢起身，目光在门缝和楼梯口之间反复游移；她没有说话，背景持续有远处警笛和屋顶滴水声。 | 10秒 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).videoPrompt().contains("破旧仓库"));
    }

    /**
     * 处理throwsWhenMergedNarrativeColumnMissing。
     */
    @Test
    void throwsWhenMergedNarrativeColumnMissing() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 景别/运镜 | 画面提示词 (Visual Prompt) | 时长 |
            | :--- | :--- | :--- | :--- |
            | 001 | 中景/固定 | 女主站在街口，霓虹反光。 | 10s |
            """;

        assertThrows(IllegalStateException.class, () -> planner.buildStoryboardShotPlans(task, storyboardMarkdown));
        assertThrows(IllegalStateException.class, () -> planner.buildStoryboardVideoPrompts(storyboardMarkdown));
    }

    /**
     * 规范化时长规划KeepsSupportedTenSecondClips。
     */
    @Test
    void normalizeDurationPlanKeepsSupportedTenSecondClips() {
        MockEnvironment environment = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "0")
            .withProperty("spring.config.additional-location", "file:src/test/resources/task-duration-config/");
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(environment));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";
        task.minDurationSeconds = 10;
        task.maxDurationSeconds = 10;

        String storyboardMarkdown = """
            | 镜号 | 景别/运镜 | 剧情画面与声音描述（长段） | 时长 |
            | :--- | :--- | :--- | :--- |
            | 001 | 中景/固定 | 夜色高架桥下，男主靠在栏杆上反复确认手机里的定位信息，远处车辆呼啸掠过。 | 10s |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> normalized = planner.normalizeClipDurationPlan(
            "seedance-1.5-pro",
            planner.buildClipDurationPlan(task, 10, shotPlans.size(), storyboardMarkdown)
        );

        assertEquals(1, normalized.size());
        assertArrayEquals(new int[] {10, 10, 10}, normalized.get(0));
    }

    /**
     * 处理clamps分镜Durations转为Five转为FifteenSeconds。
     */
    @Test
    void clampsStoryboardDurationsToFiveToFifteenSeconds() {
        MockEnvironment environment = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "0")
            .withProperty("spring.config.additional-location", "file:src/test/resources/task-duration-config/");
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(environment));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";
        task.minDurationSeconds = 1;
        task.maxDurationSeconds = 20;

        String storyboardMarkdown = """
            | 镜号 | 景别/运镜 | 剧情画面与声音描述（长段） | 时长 |
            | :--- | :--- | :--- | :--- |
            | 001 | 中景/固定 | 角色在雨夜门廊观察远处车灯，手扶栏杆，呼吸急促。 | 4s |
            | 002 | 近景/缓慢推近 | 他向前一步压低身体，眼神锁定巷口动静，环境回声渐强。 | 12s |
            """;

        List<int[]> ranges = planner.extractStoryboardShotDurationRanges(storyboardMarkdown);
        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> normalized = planner.normalizeClipDurationPlan(
            "seedance-1.5-pro",
            planner.buildClipDurationPlan(task, 10, shotPlans.size(), storyboardMarkdown)
        );

        assertArrayEquals(new int[] {5, 5}, ranges.get(0));
        assertArrayEquals(new int[] {12, 12}, ranges.get(1));
        assertArrayEquals(new int[] {6, 6, 6}, normalized.get(0));
        assertArrayEquals(new int[] {10, 10, 10}, normalized.get(1));
    }
}
