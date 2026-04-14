package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

class TaskStoryboardPlannerParsingTest {

    @Test
    void parsesContinuousTailFrameStoryboardTable() {
        MockEnvironment environment = new MockEnvironment()
            .withProperty("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "0")
            .withProperty("spring.config.additional-location", "file:src/test/resources/task-duration-config/");
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(environment));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.transcriptText = "";
        task.title = "demo";
        task.minDurationSeconds = 8;
        task.maxDurationSeconds = 8;

        String storyboardMarkdown = """
            Character Design

            - female, 24, black ponytail, black hair, beige trench coat, sharp eyes, slim build

            Scene Setting

            - rooftop at night, light rain, cold rim light, cinematic realism

            | Shot | Scene | First Frame Prompt | Last Frame Prompt | Motion | Camera Movement | Duration |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 01 | Rooftop at night | cinematic rainy rooftop at night, young woman in beige trench coat standing near the ledge, medium shot, cold rim light, ultra realistic, 4k | same rooftop, same woman raising her head toward the neon skyline | raises head | slow push in | 5-10 seconds |
            | 02 | Rooftop at night |  | same rooftop, same woman turning around toward the stairwell door | turns around | slow pan | 5 seconds |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> ranges = planner.extractStoryboardShotDurationRanges(storyboardMarkdown);
        List<int[]> normalized = planner.normalizeClipDurationPlan(
            "seedance-1.5-pro",
            planner.buildClipDurationPlan(task, 8, shotPlans.size(), storyboardMarkdown)
        );

        assertEquals(2, shotPlans.size());
        assertEquals("cinematic rainy rooftop at night, young woman in beige trench coat standing near the ledge, medium shot, cold rim light, ultra realistic, 4k", shotPlans.get(0).imagePrompt());
        assertEquals("", shotPlans.get(1).imagePrompt());
        assertTrue(shotPlans.get(0).videoPrompt().contains("same rooftop, same woman raising her head toward the neon skyline"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("动作延展：raises head"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("运镜：slow push in"));
        assertArrayEquals(new int[] {5, 10}, ranges.get(0));
        assertArrayEquals(new int[] {5, 5}, ranges.get(1));
        assertArrayEquals(new int[] {6, 6, 10}, normalized.get(0));
        assertArrayEquals(new int[] {6, 6, 6}, normalized.get(1));
    }

    @Test
    void legacySeedreamAndSeedanceColumnsFallbackToShotPlans() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 剧情摘要 | 景别角度 | 运镜 | Seedream提示词 | Seedance提示词 | 对白/声音 | 时长(秒) |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 01 | 开场 | 全景 | 推镜 | 女主站在街口。 | 她向前走两步，镜头推进。 | 风声 | 6 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);

        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).imagePrompt().contains("女主站在街口"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("动态延展"));
    }

    @Test
    void englishStoryboardTableIsParsedIntoExecutableClipPrompt() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | Shot | Scene | Time | Visual Description | Character Appearance | Action | Emotion | Camera Shot | Camera Movement | Lighting | Atmosphere | Duration |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 01 | Rooftop | Night | Rain-soaked rooftop, wet concrete reflecting neon, foreground railing, heroine in midground, skyline bokeh in background. | Black ponytail, beige wool coat, silver watch, pale skin. | She steps toward the edge and grips the railing. | Jaw tight, eyes cold, breathing restrained. | medium close-up | dolly in | cold rim light with neon spill | tense, cinematic, stormy | 6-10 seconds |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> ranges = planner.extractStoryboardShotDurationRanges(storyboardMarkdown);

        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).imagePrompt().contains("Rain-soaked rooftop"));
        assertTrue(shotPlans.get(0).imagePrompt().contains("Black ponytail"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("She steps toward the edge"));
        assertArrayEquals(new int[] {6, 10}, ranges.get(0));
    }

    @Test
    void aiShortDramaArchitectMatrixIsParsedIntoShotPlans() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 镜头参数 | 视觉描述 (AI Video Prompt) | 声音与对白 | 时长 | 衔接逻辑 (Continuity) |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | 001-1 | 中景 + 缓慢推镜 | 冷蓝色雨夜街口，路灯从左后方打出冷色轮廓光，便利店招牌作地标，[高马尾+黑色皮衣]的女主站在积水边，右手握着手机，抬眼看向街对面，电影感、湿地反光、空气里有雨丝。 | 女主： (压抑)“他真的回来了？” | 6s | 首镜建立环境锚点与角色锚点，供后续镜头继承。 |
            | 001-2 | 近景 + 静止 | 继承上一镜的环境色温与构图逻辑，[高马尾+黑色皮衣]的女主低头看手机屏幕，睫毛微颤，屏幕冷光映在脸侧，背景霓虹虚化。 | 旁白： “她终于等到那条消息。” | 4s | 通过视线延续和同侧光源承接上一镜动作。 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);
        List<int[]> ranges = planner.extractStoryboardShotDurationRanges(storyboardMarkdown);

        assertEquals(2, shotPlans.size());
        assertTrue(shotPlans.get(0).imagePrompt().contains("冷蓝色雨夜街口"));
        assertEquals("", shotPlans.get(1).imagePrompt());
        assertTrue(shotPlans.get(0).videoPrompt().contains("首镜建立环境锚点与角色锚点"));
        assertTrue(shotPlans.get(1).videoPrompt().contains("继承上一镜的环境色温与构图逻辑"));
        assertArrayEquals(new int[] {6, 6}, ranges.get(0));
        assertArrayEquals(new int[] {4, 4}, ranges.get(1));
    }

    @Test
    void scriptPromptTableUsesVisualColumnForImageAndCarriesDialogueAudioIntoVideoPrompt() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 剧情节点/场景 | 景别/镜头运动 | 视觉描述 (Visual Prompt) | 情绪/情感分析 | 对话/独白 | 音效/BGM | 建议时长 |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 001 | 开端·森林清晨 | 远景/缓慢推镜 | 晨曦照进森林，光点在草地上跳跃，女主站在薄雾里回头，空气清亮，日系手绘感。 | 惊惶里带着试探，情绪强度中等。 | 女主：“这...这是哪里？” | 轻风与鸟鸣，尾音延续到下一镜 | 6秒 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);

        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).imagePrompt().contains("晨曦照进森林"));
        assertTrue(!shotPlans.get(0).imagePrompt().contains("开端·森林清晨"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("惊惶里带着试探"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("可听见的人声对白：女主：“这...这是哪里？”"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("前0.5秒与后0.5秒保持无人声"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("音频设计：轻风与鸟鸣，尾音延续到下一镜"));
    }

    @Test
    void unlabeledDialogueColumnFallsBackToMonologueInstruction() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 剧情节点/场景 | 景别/镜头运动 | 视觉描述 (Visual Prompt) | 对话/独白 | 音效/BGM | 建议时长 |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 001 | 夜路 | 中景/静止 | 女主一个人站在路灯下，指尖发抖，呼吸不稳。 | 我不能回头。 | 夜风声轻推，尾音贴着呼吸声进入下一镜 | 4秒 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);

        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).videoPrompt().contains("可听见的人声独白：独白：我不能回头。"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("前0.5秒与后0.5秒保持无人声"));
    }

    @Test
    void sentimentAnalysisColumnAliasFeedsEmotionIntoPrompt() {
        TaskStoryboardPlanner planner = new TaskStoryboardPlanner(new ModelRuntimePropertiesResolver(new MockEnvironment()));
        TaskRecord task = new TaskRecord();
        task.creativePrompt = "demo";
        task.title = "demo";

        String storyboardMarkdown = """
            | 镜号 | 剧情节点/场景 | 景别/镜头运动 | 视觉描述 (Visual Prompt) | 情感分析 | 对话/独白 | 音效/BGM | 建议时长 |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 001 | 天台对峙 | 中景/缓慢推镜 | 女主站在天台边缘，霓虹反光落在湿润地面，呼吸急促。 | 强压愤怒下的试探，情绪强度高，潜台词是“你最好给我一个解释”。 | 女主：你终于肯出现了。 | 风声压低，尾音拖入下一镜 | 6秒 |
            """;

        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = planner.buildStoryboardShotPlans(task, storyboardMarkdown);

        assertEquals(1, shotPlans.size());
        assertTrue(shotPlans.get(0).videoPrompt().contains("强压愤怒下的试探"));
        assertTrue(shotPlans.get(0).videoPrompt().contains("可听见的人声对白：女主：你终于肯出现了。"));
    }
}
