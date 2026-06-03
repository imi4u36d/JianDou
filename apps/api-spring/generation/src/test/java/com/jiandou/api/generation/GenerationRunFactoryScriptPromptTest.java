package com.jiandou.api.generation;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.jiandou.api.config.JiandouStorageProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.image.ImageModelProviderRegistry;
import com.jiandou.api.generation.orchestration.GenerationRunFactory;
import com.jiandou.api.generation.orchestration.GenerationRunSupport;
import com.jiandou.api.generation.orchestration.LocalGenerationRunStore;
import com.jiandou.api.generation.runtime.GenerationConfigPathLocator;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.PromptTemplateResolver;
import com.jiandou.api.generation.text.TextCompletionInvocation;
import com.jiandou.api.generation.text.TextModelInvocation;
import com.jiandou.api.generation.text.TextModelProvider;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import com.jiandou.api.generation.video.SeedanceVideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.generation.video.VideoProviderTransport;
import com.jiandou.api.media.LocalMediaArtifactService;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.env.MockEnvironment;

/**
 * 生成运行工厂脚本提示词相关测试。
 */
class GenerationRunFactoryScriptPromptTest {

    @TempDir
    Path tempDir;

    private static final String SCRIPT_SYSTEM_PROMPT = """
        ### AI 短剧分镜生成指令（严格执行版）
        表格必须严格使用以下表头：`| 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |`
        每个核心角色只能占一行
        人物定位 指角色在故事里的身份、关系、目标、当前处境或剧情功能
        不可变视觉锚点 只允许写身体、脸、发型、体型、固定着装和稳定穿戴配饰
        禁止写抱试卷、拿飞盘、手持手机、当前姿势、当前动作、场景物件、临时道具或剧情状态
        必须输出 Markdown 表格
        分镜内容描述必须尽可能详细
        运镜只能使用极简基础表达
        同一镜头的首帧与尾帧必须被视为同一 seed、同一场景坐标系下的连续画面
        从第二个镜头开始，首帧描述 (Start Frame) 必须直接继承上一镜头 尾帧描述 (End Frame) 的同一句核心画面
        每个镜头时长必须限制在 `5-12s`
        不能凭空添加原文没有的人声内容
        首尾帧描述和分镜内容描述都只能描述当前镜头内部已经发生或正在发生的内容
        首尾帧描述只允许写当前画面中实际可见且会影响构图的场景和布置
        首尾帧描述必须明确写出相同的场景坐标锚点与物件关系
        若当前帧中有多人同场，首尾帧描述必须交代他们共享的背景平面以及至少一个其他环境锚点
        若该镜头首尾帧发生在同一场景内，尾帧必须沿用与首帧相同的场景描述骨架、空间锚点和布置信息
        同一场景内的首尾帧区别只能主要体现在人物动作状态、视线、手部位置、道具被拿起/放下、局势推进结果上
        若首帧已经写出明确场景锚点或关键物件
        写尾帧时，先检查首帧中出现过的场景锚点、方位词、关键物件名词
        首尾帧描述建议严格按照这个句式组织
        场景布置只能写与当前镜头动作、人物调度、关键道具、空间关系直接相关的内容
        若某些场景信息在当前帧并不可见、只存在于镜头外、被遮挡、或需要靠常识补全，均不要写进首帧/尾帧描述
        当首帧描述或尾帧描述中出现角色名时，必须把该角色对应的外观锚点紧跟追加在角色名后，格式为 `角色名（外观锚点）`
        【空间方位与构图约束】
        建立全局坐标系：先统一整个镜头的空间框架
        定义镜头视角：必须明确镜头是“正视”“侧视”还是“俯视”
        定义背景层：背景元素（如窗户、墙壁、门）必须被定义为贯穿画面的连续平面或明确的左右分区
        定义深度层：必须明确前景（靠近镜头）、中景（人物活动区）、远景（背景）的层级关系
        共享背景原则：如果多人处于同一场景（如靠窗座位），必须明确他们是否共享同一背景平面
        环境锚点补全：除共同背景平面外，还必须写出与人物调度直接相关的其他环境锚点
        相对位置锚定：描述人物位置时，必须使用“画面左侧/右侧”加“背景参照物”的双重锚定
        无障碍原则：人物的移动路径（从 A 点到 B 点）必须避开固定的物理障碍（如桌子、墙壁）
        朝向逻辑：如果两人“相对而坐”，他们的面部朝向必须相对
        动作空间预留：在描述起身、转身等大幅度动作时，必须确认该方向有足够的物理空间
        首尾帧一致性检查：同一镜头内背景元素（门窗位置）不得发生位移或左右互换；尾帧的人物位置必须是首帧动作的自然延续，严禁瞬移
        | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
        """;

    /**
     * 创建脚本运行UsesRefactored分镜提示词Contract。
     */
    @Test
    void createScriptRunUsesRefactoredStoryboardPromptContract() {
        List<String> promptRows = List.of(
            "### AI 短剧分镜生成指令（严格执行版）",
            "表格必须严格使用以下表头：`| 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |`",
            "每个核心角色只能占一行",
            "人物定位 指角色在故事里的身份、关系、目标、当前处境或剧情功能",
            "不可变视觉锚点 只允许写身体、脸、发型、体型、固定着装和稳定穿戴配饰",
            "禁止写抱试卷、拿飞盘、手持手机、当前姿势、当前动作、场景物件、临时道具或剧情状态",
            "必须输出 Markdown 表格",
            "分镜内容描述必须尽可能详细",
            "运镜只能使用极简基础表达",
            "同一镜头的首帧与尾帧必须被视为同一 seed、同一场景坐标系下的连续画面",
            "从第二个镜头开始，首帧描述 (Start Frame) 必须直接继承上一镜头 尾帧描述 (End Frame) 的同一句核心画面",
            "每个镜头时长必须限制在 `5-12s`",
            "不能凭空添加原文没有的人声内容",
            "首尾帧描述和分镜内容描述都只能描述当前镜头内部已经发生或正在发生的内容",
            "首尾帧描述只允许写当前画面中实际可见且会影响构图的场景和布置",
            "首尾帧描述必须明确写出相同的场景坐标锚点与物件关系",
            "若当前帧中有多人同场，首尾帧描述必须交代他们共享的背景平面以及至少一个其他环境锚点",
            "若该镜头首尾帧发生在同一场景内，尾帧必须沿用与首帧相同的场景描述骨架、空间锚点和布置信息",
            "同一场景内的首尾帧区别只能主要体现在人物动作状态、视线、手部位置、道具被拿起/放下、局势推进结果上",
            "若首帧已经写出明确场景锚点或关键物件",
            "写尾帧时，先检查首帧中出现过的场景锚点、方位词、关键物件名词",
            "首尾帧描述建议严格按照这个句式组织",
            "场景布置只能写与当前镜头动作、人物调度、关键道具、空间关系直接相关的内容",
            "若某些场景信息在当前帧并不可见、只存在于镜头外、被遮挡、或需要靠常识补全，均不要写进首帧/尾帧描述",
            "当首帧描述或尾帧描述中出现角色名时，必须把该角色对应的外观锚点紧跟追加在角色名后，格式为 `角色名（外观锚点）`",
            "【空间方位与构图约束】",
            "建立全局坐标系：先统一整个镜头的空间框架",
            "定义镜头视角：必须明确镜头是“正视”“侧视”还是“俯视”",
            "定义背景层：背景元素（如窗户、墙壁、门）必须被定义为贯穿画面的连续平面或明确的左右分区",
            "定义深度层：必须明确前景（靠近镜头）、中景（人物活动区）、远景（背景）的层级关系",
            "共享背景原则：如果多人处于同一场景（如靠窗座位），必须明确他们是否共享同一背景平面",
            "环境锚点补全：除共同背景平面外，还必须写出与人物调度直接相关的其他环境锚点",
            "相对位置锚定：描述人物位置时，必须使用“画面左侧/右侧”加“背景参照物”的双重锚定",
            "无障碍原则：人物的移动路径（从 A 点到 B 点）必须避开固定的物理障碍（如桌子、墙壁）",
            "朝向逻辑：如果两人“相对而坐”，他们的面部朝向必须相对",
            "动作空间预留：在描述起身、转身等大幅度动作时，必须确认该方向有足够的物理空间",
            "首尾帧一致性检查：同一镜头内背景元素（门窗位置）不得发生位移或左右互换；尾帧的人物位置必须是首帧动作的自然延续，严禁瞬移",
            "| 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |"
        );
        String[] capturedSystemPrompt = new String[1];
        String[] capturedUserPrompt = new String[1];
        String[] capturedReviewSystemPrompt = new String[1];
        String[] capturedReviewUserPrompt = new String[1];
        int[] invocationCount = new int[1];
        TextModelProviderRegistry textModelProviderRegistry = registry(new TextModelProvider() {
            /**
             * 检查是否supports。
             * @param profile profile值
             * @return 是否满足条件
             */
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            /**
             * 处理generate。
             * @param profile profile值
             * @param invocation 调用值
             * @return 处理结果
             */
            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                TextCompletionInvocation textInvocation = (TextCompletionInvocation) invocation;
                invocationCount[0]++;
                if (invocationCount[0] == 1) {
                    capturedSystemPrompt[0] = textInvocation.systemPrompt();
                    capturedUserPrompt[0] = textInvocation.userPrompt();
                    return new TextModelResponse(
                        """
                            【角色定义信息】
                            - 林舒：外观锚点未明确。

                            【分镜脚本】
                            | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                            | :--- | :--- | :--- | :--- | :--- |
                            | 001 | 林舒站在桌边。 | 林舒转身。 | 林舒动作推进。 | 8s |
                            """,
                        "https://api.example.com/v1/responses",
                        "api.example.com",
                        10,
                        true,
                        "resp_script_draft",
                        Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                        Map.of("id", "resp_script_draft"),
                        200
                    );
                }
                capturedReviewSystemPrompt[0] = textInvocation.systemPrompt();
                capturedReviewUserPrompt[0] = textInvocation.userPrompt();
                return new TextModelResponse(
                    """
                        【角色定义信息】
                        - 林舒：外观锚点未明确。

                        【分镜脚本】
                        | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                        | :--- | :--- | :--- | :--- | :--- |
                        | 001 | 林舒站在桌子左侧，桌上放着文件和杯子，左侧是窗户，右侧是书架，她正低头看向文件。 | 林舒仍站在同一张桌子左侧，桌上仍放着文件和杯子，左侧是窗户，右侧是书架，她抬头转向门口。 | 林舒先低头翻看桌上的文件，听到门外动静后停手，抬头转向门口。 | 8s |
                        """,
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_script_review",
                    Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                    Map.of("id", "resp_script_review"),
                    200
                );
            }
        });
        GenerationRunFactory factory = createFactory(textModelProviderRegistry);

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", "女主在雨夜街头看见失踪多年的哥哥。"));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        Map<String, Object> run = factory.createScriptRun("run_script_prompt_1", request);

        for (String row : promptRows) {
            assertTrue(capturedSystemPrompt[0].contains(row));
        }
        assertFalse(capturedSystemPrompt[0].contains("首尾帧描述都必须保留上下文情境信息"));
        assertFalse(capturedSystemPrompt[0].contains("首尾帧描述都必须详细交代场景和布置"));
        assertFalse(capturedSystemPrompt[0].contains("下一拍衔接"));
        assertEquals(2, invocationCount[0]);
        assertTrue(capturedUserPrompt[0].contains("请严格遵循 system prompt 的输出格式与规则"));
        assertFalse(capturedUserPrompt[0].contains("【额外追加要求】"));
        assertTrue(capturedReviewSystemPrompt[0].contains("二次审校要求"));
        assertTrue(capturedReviewSystemPrompt[0].contains("遗漏共同背景平面/其他环境锚点"));
        assertTrue(capturedReviewSystemPrompt[0].contains("空间定位逻辑"));
        assertTrue(capturedReviewSystemPrompt[0].contains("建立全局坐标系"));
        assertTrue(capturedReviewSystemPrompt[0].contains("镜头视角（正视/侧视/俯视）"));
        assertTrue(capturedReviewSystemPrompt[0].contains("双重锚定"));
        assertTrue(capturedReviewSystemPrompt[0].contains("桌子、门、过道、墙角、书架等其他环境锚点"));
        assertTrue(capturedReviewUserPrompt[0].contains("当前分镜初稿"));
        assertTrue(capturedReviewUserPrompt[0].contains("二次检查时必须特别校验空间定位"));
        assertTrue(capturedReviewUserPrompt[0].contains("明确镜头视角（正视/侧视/俯视）、背景层和前景/中景/远景深度层"));
        assertTrue(capturedReviewUserPrompt[0].contains("是否写出桌子、门、过道、墙角、书架等其他环境锚点"));
        assertTrue(capturedReviewUserPrompt[0].contains("人物位置是否使用“画面左侧/右侧 + 背景参照物”的双重锚定"));
        assertTrue(capturedReviewUserPrompt[0].contains("尾帧人物位置是首帧动作的自然延续"));
        assertFalse(capturedReviewUserPrompt[0].contains("【额外追加要求】"));
        assertTrue(capturedReviewUserPrompt[0].contains("林舒站在桌边。"));
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertTrue(String.valueOf(result.get("scriptMarkdown")).contains("同一张桌子左侧"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertTrue(String.valueOf(metadata.get("draftScriptMarkdown")).contains("林舒站在桌边。"));
        assertFalse(metadata.containsKey("extraPrompt"));
        assertEquals(true, metadata.get("reviewApplied"));
        assertEquals(2, ((java.util.List<?>) metadata.get("providerInteractions")).size());
        assertTrue(String.valueOf(metadata.get("providerRequest")).contains("https://api.example.com/v1/responses"));
    }

    /**
     * 创建脚本运行FallsBack到初稿When审校结果无效。
     */
    @Test
    void createScriptRunFallsBackToDraftWhenReviewOutputInvalid() {
        int[] invocationCount = new int[1];
        TextModelProviderRegistry textModelProviderRegistry = registry(new TextModelProvider() {
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                invocationCount[0]++;
                if (invocationCount[0] == 1) {
                    return new TextModelResponse(
                        """
                            【角色定义信息】
                            - 林舒：外观锚点未明确。

                            【分镜脚本】
                            | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                            | :--- | :--- | :--- | :--- | :--- |
                            | 001 | 林舒站在桌子左侧，桌上放着文件和杯子，左侧是窗户，右侧是书架，她正低头看向文件。 | 林舒仍站在同一张桌子左侧，桌上仍放着文件和杯子，左侧是窗户，右侧是书架，她抬头转向门口。 | 林舒先低头翻看桌上的文件，听到门外动静后停手，抬头转向门口。 | 8s |
                            """,
                        "https://api.example.com/v1/responses",
                        "api.example.com",
                        10,
                        true,
                        "resp_script_draft",
                        Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                        Map.of("id", "resp_script_draft"),
                        200
                    );
                }
                return new TextModelResponse(
                    "审校后建议：请加强首尾帧一致性。",
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    12,
                    true,
                    "resp_script_review_invalid",
                    Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                    Map.of("id", "resp_script_review_invalid"),
                    200
                );
            }
        });
        GenerationRunFactory factory = createFactory(textModelProviderRegistry);

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", "女主在雨夜街头看见失踪多年的哥哥。"));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        Map<String, Object> run = factory.createScriptRun("run_script_prompt_4", request);

        assertEquals(2, invocationCount[0]);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertTrue(String.valueOf(result.get("scriptMarkdown")).contains("同一张桌子左侧"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals(false, metadata.get("reviewApplied"));
        assertEquals("resp_script_draft", metadata.get("finalResponseId"));
        assertEquals("resp_script_review_invalid", metadata.get("reviewResponseId"));
        assertEquals("review output missing character definitions", metadata.get("reviewFallbackReason"));
        assertEquals(2, ((java.util.List<?>) metadata.get("providerInteractions")).size());
    }

    @Test
    void createScriptRunFallsBackWhenReviewEchoesPromptTables() {
        int[] invocationCount = new int[1];
        TextModelProviderRegistry textModelProviderRegistry = registry(new TextModelProvider() {
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                invocationCount[0]++;
                if (invocationCount[0] == 1) {
                    return new TextModelResponse(
                        """
                            【角色定义信息】
                            - 林舒：外观锚点未明确。

                            【分镜脚本】
                            | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                            | :--- | :--- | :--- | :--- | :--- |
                            | 001 | 林舒站在桌子左侧，桌上放着文件和杯子，左侧是窗户，右侧是书架，她正低头看向文件。 | 林舒仍站在同一张桌子左侧，桌上仍放着文件和杯子，左侧是窗户，右侧是书架，她抬头转向门口。 | 林舒先低头翻看桌上的文件，听到门外动静后停手，抬头转向门口。 | 8s |
                            """,
                        "https://api.example.com/v1/responses",
                        "api.example.com",
                        10,
                        true,
                        "resp_script_draft",
                        Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                        Map.of("id", "resp_script_draft"),
                        200
                    );
                }
                return new TextModelResponse(
                    """
                        ### AI 短剧分镜生成指令（严格执行版）
                        表格必须严格使用以下表头：
                        | 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |
                        | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |

                        #### 二次审校要求

                        【角色定义信息】
                        - 按原文提炼核心角色。

                        【分镜脚本】
                        | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                        | :--- | :--- | :--- | :--- | :--- |

                        # 任务输入
                        女主在雨夜街头看见失踪多年的哥哥。
                        """,
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    12,
                    true,
                    "resp_script_review_echo",
                    Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                    Map.of("id", "resp_script_review_echo"),
                    200
                );
            }
        });
        GenerationRunFactory factory = createFactory(textModelProviderRegistry);

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", "女主在雨夜街头看见失踪多年的哥哥。"));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        Map<String, Object> run = factory.createScriptRun("run_script_prompt_echo", request);

        assertEquals(2, invocationCount[0]);
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertTrue(String.valueOf(result.get("scriptMarkdown")).contains("同一张桌子左侧"));
        assertFalse(String.valueOf(result.get("scriptMarkdown")).contains("# 任务输入"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals(false, metadata.get("reviewApplied"));
        assertEquals("resp_script_draft", metadata.get("finalResponseId"));
        assertEquals("resp_script_review_echo", metadata.get("reviewResponseId"));
        assertEquals("review output missing storyboard rows", metadata.get("reviewFallbackReason"));
    }

    @Test
    void createScriptAdjustRunUsesOriginalStoryboardAndOptionalRequirement() {
        String[] capturedSystemPrompt = new String[1];
        String[] capturedUserPrompt = new String[1];
        int[] invocationCount = new int[1];
        TextModelProviderRegistry textModelProviderRegistry = registry(new TextModelProvider() {
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                TextCompletionInvocation textInvocation = (TextCompletionInvocation) invocation;
                invocationCount[0]++;
                capturedSystemPrompt[0] = textInvocation.systemPrompt();
                capturedUserPrompt[0] = textInvocation.userPrompt();
                return new TextModelResponse(
                    """
                        【角色定义信息】
                        | 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |
                        | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
                        | 林舒 | 女性，28岁 | 调查者 | 杏眼，薄唇 | 黑色低马尾 | 中等身高 | 素色针织开衫 | 细框眼镜 | 黑色低马尾、细框眼镜、素色针织开衫 | 克制 | 低声短句 |

                        【分镜脚本】
                        | 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
                        | :--- | :--- | :--- | :--- | :--- |
                        | 001 | 林舒站在门口。 | 林舒走到书架旁。 | 林舒从门口走到书架旁。 | 8s |
                        """,
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_script_adjust",
                    Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                    Map.of("id", "resp_script_adjust"),
                    200
                );
            }
        });
        GenerationRunFactory factory = createFactory(textModelProviderRegistry);
        String sourceStoryboard = """
            【角色定义信息】
            - 林舒：外观锚点未明确。

            【分镜脚本】
            | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
            | :--- | :--- | :--- | :--- | :--- |
            | 001 | 林舒站在门口。 | 林舒走到书架旁。 | 林舒移动。 | 8s |
            """;

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script_adjust");
        request.put("input", Map.of(
            "text", "林舒进入废弃图书馆。",
            "scriptMarkdown", sourceStoryboard,
            "adjustmentPrompt", "补强角色三视图外观信息"
        ));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        Map<String, Object> run = factory.createScriptAdjustRun("run_script_adjust_1", request);

        assertEquals(1, invocationCount[0]);
        assertTrue(capturedSystemPrompt[0].contains("二次审校要求"));
        assertTrue(capturedUserPrompt[0].contains("# 原分镜脚本"));
        assertTrue(capturedUserPrompt[0].contains("补强角色三视图外观信息"));
        assertTrue(capturedUserPrompt[0].contains("林舒移动。"));
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertEquals("script_adjust", result.get("kind"));
        assertEquals("user_prompt", result.get("adjustmentMode"));
        assertTrue(String.valueOf(result.get("scriptMarkdown")).contains("细框眼镜"));
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) result.get("metadata");
        assertEquals("补强角色三视图外观信息", metadata.get("adjustmentPrompt"));
        assertEquals(1, ((java.util.List<?>) metadata.get("providerInteractions")).size());
    }

    @Test
    void createScriptAdjustRunUsesSelfReviewWhenRequirementBlank() {
        String[] capturedUserPrompt = new String[1];
        TextModelProviderRegistry textModelProviderRegistry = registry(new TextModelProvider() {
            @Override
            public boolean supports(ModelRuntimeProfile profile) {
                return true;
            }

            @Override
            public TextModelResponse generate(
                ModelRuntimeProfile profile,
                TextModelInvocation invocation
            ) {
                capturedUserPrompt[0] = ((TextCompletionInvocation) invocation).userPrompt();
                return new TextModelResponse(
                    """
                        【角色定义信息】
                        - 林舒：外观锚点未明确。

                        【分镜脚本】
                        | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
                        | :--- | :--- | :--- | :--- | :--- |
                        | 001 | 林舒站在门口。 | 林舒走到书架旁。 | 林舒从门口走到书架旁。 | 8s |
                        """,
                    "https://api.example.com/v1/responses",
                    "api.example.com",
                    10,
                    true,
                    "resp_script_adjust_self",
                    Map.of("endpoint", "https://api.example.com/v1/responses", "body", Map.of("model", "gpt-text")),
                    Map.of("id", "resp_script_adjust_self"),
                    200
                );
            }
        });
        GenerationRunFactory factory = createFactory(textModelProviderRegistry);
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script_adjust");
        request.put("input", Map.of(
            "scriptMarkdown", """
                【角色定义信息】
                - 林舒：外观锚点未明确。

                【分镜脚本】
                | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
                | :--- | :--- | :--- | :--- | :--- |
                | 001 | 林舒站在门口。 | 林舒走到书架旁。 | 林舒移动。 | 8s |
                """
        ));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));

        Map<String, Object> run = factory.createScriptAdjustRun("run_script_adjust_2", request);

        assertTrue(capturedUserPrompt[0].contains("用户没有输入额外调整要求"));
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) run.get("result");
        assertEquals("self_review", result.get("adjustmentMode"));
    }

    /**
     * 创建脚本运行ThrowsWhen输入Missing文本。
     */
    @Test
    void createScriptRunThrowsWhenInputMissingText() {
        GenerationRunFactory factory = createFactory(registry());
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        assertThrows(IllegalArgumentException.class, () -> factory.createScriptRun("run_script_prompt_2", request));
    }

    /**
     * 创建脚本运行ThrowsWhen输入文本空白。
     */
    @Test
    void createScriptRunThrowsWhenInputTextBlank() {
        GenerationRunFactory factory = createFactory(registry());
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("input", Map.of("text", ""));
        request.put("model", Map.of("textAnalysisModel", "gpt-text"));
        request.put("options", Map.of("visualStyle", "电影写实"));

        assertThrows(IllegalArgumentException.class, () -> factory.createScriptRun("run_script_prompt_3", request));
    }

    /**
     * 创建工厂。
     * @param textModelProviderRegistry 文本模型 provider 注册表值
     * @return 处理结果
     */
    private GenerationRunFactory createFactory(TextModelProviderRegistry textModelProviderRegistry) {
        ModelRuntimeProfile textProfile = new ModelRuntimeProfile(
            "openai",
            "gpt-text",
            "k",
            "https://api.example.com/v1",
            60,
            0.2,
            2048,
            "test"
        );
        ModelRuntimePropertiesResolver modelResolver = new ModelRuntimePropertiesResolver(new MockEnvironment()) {
            /**
             * 处理解析文本Profile。
             * @param requestedModel requested模型值
             * @return 处理结果
             */
            @Override
            public ModelRuntimeProfile resolveTextProfile(String requestedModel) {
                return textProfile;
            }

            /**
             * 处理值。
             * @param section section值
             * @param key key值
             * @param fallback 兜底值
             * @return 处理结果
             */
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
            /**
             * 处理系统提示词。
             * @param promptName 提示词Name值
             * @param key key值
             * @return 处理结果
             */
            @Override
            public String systemPrompt(String promptName, String key) {
                return SCRIPT_SYSTEM_PROMPT;
            }
        };
        LocalMediaArtifactService localMediaArtifactService = new LocalMediaArtifactService(storageProperties(tempDir), "ffmpeg");
        GenerationRunSupport support = new GenerationRunSupport(localMediaArtifactService, textModelProviderRegistry);
        ImageModelProviderRegistry imageModelProviderRegistry = new ImageModelProviderRegistry(java.util.List.of());
        VideoProviderTransport videoProviderTransport = new VideoProviderTransport(new ObjectMapper());
        VideoModelProviderRegistry videoModelProviderRegistry = new VideoModelProviderRegistry(java.util.List.of(
            new SeedanceVideoModelProvider(videoProviderTransport)
        ));
        return new GenerationRunFactory(
            modelResolver,
            promptTemplateResolver,
            textModelProviderRegistry,
            imageModelProviderRegistry,
            videoModelProviderRegistry,
            support
        );
    }

    private TextModelProviderRegistry registry(TextModelProvider... providers) {
        return new TextModelProviderRegistry(java.util.Arrays.asList(providers));
    }

    private JiandouStorageProperties storageProperties(Path rootDir) {
        JiandouStorageProperties properties = new JiandouStorageProperties();
        properties.setRootDir(rootDir.toString());
        return properties;
    }
}
