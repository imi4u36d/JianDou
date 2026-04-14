package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

class GenerationRunFactoryScriptPromptTest {

    @TempDir
    Path tempDir;

    @Test
    void createScriptRunUsesRefactoredStoryboardPromptContract() {
        ModelRuntimeProfile textProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-text",
            "",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return textProfile;
            }

            @Override
            public String value(String section, String key, String fallback) {
                return fallback;
            }
        };
        PromptTemplateResolver promptTemplateResolver = new PromptTemplateResolver(
            new MockEnvironment(),
            modelResolver,
            new GenerationConfigPathLocator(new MockEnvironment())
        ) {
            @Override
            public String systemPrompt(String promptName, String key) {
                return "";
            }
        };
        String[] capturedSystemPrompt = new String[1];
        String[] capturedUserPrompt = new String[1];
        CompatibleTextModelClient textModelClient = new CompatibleTextModelClient(new ObjectMapper(), java.util.List.of()) {
            @Override
            public TextModelResponse generateText(
                ModelRuntimeProfile profile,
                String systemPrompt,
                String userPrompt,
                double temperature,
                int maxTokens
            ) {
                capturedSystemPrompt[0] = systemPrompt;
                capturedUserPrompt[0] = userPrompt;
                return new TextModelResponse(
                    "# 分镜脚本\n\n| 镜号 | 场景 | 景别角度 | 运镜 | 人物外观 | 动作 | 情绪 | 光线 | 氛围 | 首帧提示词 | 尾帧提示词 | 统一提示词 | 动态与运镜 | 时长 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| 1 | 场景 | 中景 | static | 角色 | 抬头 | 警觉 | 夜间侧光 | 压迫 | 首帧 | 尾帧 | 统一画面 | 抬头并停住 | 6 |",
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_script_1"
                );
            }
        };
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(tempDir.toString(), "ffmpeg");
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, modelResolver, textModelClient);
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelClient,
            new RemoteMediaGenerationClient(new ObjectMapper()),
            support
        );

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", "女主在雨夜街头看见失踪多年的哥哥。"));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        factory.createScriptRun("run_script_prompt_1", request);

        assertTrue(capturedSystemPrompt[0].contains("### 🤖 AI 短剧脚本专家指令 (System Prompt)"));
        assertTrue(capturedSystemPrompt[0].contains("对话还原优先"));
        assertTrue(capturedSystemPrompt[0].contains("对话情感分析"));
        assertTrue(capturedSystemPrompt[0].contains("对白时序缓冲"));
        assertTrue(capturedSystemPrompt[0].contains("物理合理性"));
        assertTrue(capturedSystemPrompt[0].contains("不写旁白、画外音或解说配音"));
        assertTrue(capturedSystemPrompt[0].contains("音效/BGM 建议"));
        assertTrue(capturedSystemPrompt[0].contains("前 0.5 秒和后 0.5 秒"));
        assertTrue(capturedSystemPrompt[0].contains("每一句都必须写成“角色名：台词”或“独白：台词”"));
        assertTrue(capturedSystemPrompt[0].contains("情绪/情感分析"));
        assertTrue(capturedSystemPrompt[0].contains("| 镜号 | 剧情节点/场景 | 景别 | 视觉描述 (Visual Prompt) | 情绪/情感分析 | 对话/独白 | 音效/BGM | 建议时长 |"));
        assertTrue(capturedUserPrompt[0].contains("请输出可直接进入分镜解析流程的 markdown"));
    }

    @Test
    void createScriptRunFallbackStillProducesParsableStoryboardTable() {
        ModelRuntimeProfile textProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-text",
            "",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return textProfile;
            }

            @Override
            public String value(String section, String key, String fallback) {
                return fallback;
            }
        };
        PromptTemplateResolver promptTemplateResolver = new PromptTemplateResolver(
            new MockEnvironment(),
            modelResolver,
            new GenerationConfigPathLocator(new MockEnvironment())
        ) {
            @Override
            public String systemPrompt(String promptName, String key) {
                return "";
            }
        };
        CompatibleTextModelClient textModelClient = new CompatibleTextModelClient(new ObjectMapper(), java.util.List.of());
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(tempDir.toString(), "ffmpeg");
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, modelResolver, textModelClient);
        GenerationRunFactory factory = new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelClient,
            new RemoteMediaGenerationClient(new ObjectMapper()),
            support
        );

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", ""));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        Map<String, Object> run = factory.createScriptRun("run_script_prompt_2", request);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        String scriptMarkdown = String.valueOf(result.get("scriptMarkdown"));

        assertTrue(scriptMarkdown.contains("| 镜号 | 剧情节点/场景 | 景别/镜头运动 | 视觉描述 (Visual Prompt) | 情绪/情感分析 | 对话/独白 | 音效/BGM | 建议时长 |"));
        assertTrue(scriptMarkdown.contains("| 001 | 开场建立人物与环境 |"));
        assertTrue(scriptMarkdown.contains("前0.5秒先铺环境底噪"));
    }
}
