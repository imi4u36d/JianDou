package com.jiandou.api.workflow.application;

import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.config.JiandouAppProperties;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.workflow.WorkflowConstants;
import com.jiandou.api.workflow.infrastructure.WorkflowJsonSupport;
import com.jiandou.api.workflow.infrastructure.mybatis.MaterialAssetTagEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class WorkflowMockDataBootstrap {

    private static final Logger log = LoggerFactory.getLogger(WorkflowMockDataBootstrap.class);

    private final WorkflowRepository workflowRepository;
    private final MybatisAuthRepository authRepository;
    private final LocalMediaArtifactService localMediaArtifactService;
    private final JiandouAppProperties appProperties;

    public WorkflowMockDataBootstrap(
        WorkflowRepository workflowRepository,
        MybatisAuthRepository authRepository,
        LocalMediaArtifactService localMediaArtifactService,
        JiandouAppProperties appProperties
    ) {
        this.workflowRepository = workflowRepository;
        this.authRepository = authRepository;
        this.localMediaArtifactService = localMediaArtifactService;
        this.appProperties = appProperties;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void seedMockWorkflows() {
        if (!isDevelopmentEnv()) {
            return;
        }
        SysUserEntity owner = resolveSeedOwner();
        if (owner == null || owner.getId() == null) {
            log.info("skip workflow mock bootstrap: no available user");
            return;
        }
        try {
            seedTeaCampaignWorkflow(owner);
        } catch (Exception ex) {
            log.warn("seed workflow mock failed: wf_mock_tea_campaign {}", ex.getMessage());
        }
        try {
            seedCampingWorkflow(owner);
        } catch (Exception ex) {
            log.warn("seed workflow mock failed: wf_mock_camping_ad {}", ex.getMessage());
        }
    }

    private void seedTeaCampaignWorkflow(SysUserEntity owner) {
        String workflowId = "wf_mock_tea_campaign";
        OffsetDateTime baseTime = OffsetDateTime.now(ZoneOffset.UTC).minusDays(2);
        int[] dimensions = dimensions("9:16");

        List<Map<String, Object>> storyboardV1Clips = List.of(
            clip(1, "镜头一", "茶盒在木桌上展开，蒸汽缓慢升起。", "推镜靠近茶盒与嫩芽。", "东方茶室、晨雾、木纹桌面、春茶包装、柔和天光", "茶盒打开，嫩芽与蒸汽一起被晨光照亮，微距质感，广告级静帧", 4),
            clip(2, "镜头二", "手部取茶入盏，茶叶在半空舒展。", "手持跟拍，强调叶片层次和下落轨迹。", "手部特写、茶叶飞散、暖金色逆光、慢动作", "茶叶在暖金逆光里旋转下落，手部动作克制稳定，质感广告片", 5),
            clip(3, "镜头三", "成品茶汤在杯中形成清亮涟漪。", "低角度拉近茶汤表面，收在品牌标语。", "玻璃杯、通透茶汤、清亮反射、品牌收束", "清亮茶汤在杯中荡开细密涟漪，最终停在品牌标语上，干净高级", 5)
        );
        List<Map<String, Object>> storyboardV2Clips = List.of(
            clip(1, "镜头一", "品牌礼盒在晨雾茶席中缓缓展开，茶叶与品牌印章同时入镜。", "从俯视滑入近景，先见整体气氛，再停在包装细节。", "国风茶席、雾气、礼盒开箱、浅金压纹、晨光漫反射", "晨雾茶席中的春茶礼盒缓缓展开，浅金压纹在晨光里闪动，镜头顺滑推进，东方高级感", 4),
            clip(2, "镜头二", "嫩芽被投入白瓷盖碗，热气裹住茶香。", "特写跟随手部动作，保留热气层次和叶片展开细节。", "白瓷盖碗、嫩芽、热气、手部动作、层次分明", "嫩芽落入白瓷盖碗的一瞬间被热气包裹，叶片舒展，画面克制而精致", 5),
            clip(3, "镜头三", "茶汤与品牌文案同框，形成收束画面。", "定机慢推，茶汤高光与品牌文案最终定格。", "通透茶汤、轻微波纹、品牌文案、简洁背景", "通透茶汤在轻微波纹中稳定下来，品牌文案浮现，形成高级电商短片收束", 5)
        );

        StageWorkflowEntity workflow = workflowEntity(
            workflowId,
            owner,
            "明前春茶上新",
            "为电商首页生成一支 15 秒竖屏春茶上新短片，重点突出礼盒、嫩芽与茶汤通透感。",
            "东方写意，高级质感，镜头节奏平稳，适合品牌上新短视频。",
            "9:16",
            "new-chinese",
            "gpt-5.1",
            "gpt-4.1-mini",
            "flux-1.1-pro",
            "kling-v1-6",
            "720p",
            20260418,
            4,
            5,
            WorkflowConstants.STATUS_READY,
            WorkflowConstants.STAGE_VIDEO,
            "sv_mock_tea_storyboard_v2",
            "",
            null,
            "",
            baseTime,
            baseTime.plusHours(6),
            Map.of(
                "mock", true,
                "mode", "stage-workflow",
                "scenario", "tea-campaign"
            )
        );
        workflowRepository.saveWorkflow(workflow);

        TextSeed teaStoryboardV1 = createStoryboardSeed(
            workflow,
            "storyboard-v1.md",
            1,
            false,
            4,
            "镜头节奏稳定，但包装主体还不够突出",
            "sv_mock_tea_storyboard_v1",
            "asset_mock_tea_storyboard_v1",
            baseTime.plusMinutes(10),
            storyboardV1Clips
        );
        TextSeed teaStoryboardV2 = createStoryboardSeed(
            workflow,
            "storyboard-v2.md",
            2,
            true,
            5,
            "整体更适合电商上新主视觉，已选中继续",
            "sv_mock_tea_storyboard_v2",
            "asset_mock_tea_storyboard_v2",
            baseTime.plusMinutes(20),
            storyboardV2Clips
        );
        saveTextSeed(teaStoryboardV1, workflow, List.of("茶饮", "国风", "上新"));
        saveTextSeed(teaStoryboardV2, workflow, List.of("茶饮", "国风", "精选"));

        KeyframeSeed teaClip1KeyframeV1 = createKeyframeSeed(
            workflow,
            teaStoryboardV2.version(),
            1,
            1,
            false,
            4,
            "雾气层次不错，但礼盒压纹还可以更清晰",
            "sv_mock_tea_clip1_keyframe_v1",
            "asset_mock_tea_clip1_keyframe_v1",
            baseTime.plusMinutes(40),
            dimensions[0],
            dimensions[1],
            "礼盒开场",
            "Flux 方案 A",
            "镜头一：强调礼盒开箱、浅金压纹和晨雾层次。"
        );
        KeyframeSeed teaClip1KeyframeV2 = createKeyframeSeed(
            workflow,
            teaStoryboardV2.version(),
            1,
            2,
            true,
            5,
            "包装主体明确，适合作为后续视频首帧",
            "sv_mock_tea_clip1_keyframe_v2",
            "asset_mock_tea_clip1_keyframe_v2",
            baseTime.plusMinutes(55),
            dimensions[0],
            dimensions[1],
            "礼盒开场",
            "Flux 方案 B",
            "镜头一：晨雾里的礼盒开箱，主体更聚焦，适合作为首帧。"
        );
        KeyframeSeed teaClip2KeyframeV1 = createKeyframeSeed(
            workflow,
            teaStoryboardV2.version(),
            2,
            1,
            true,
            4,
            "手部动作自然，热气层次可继续沿用",
            "sv_mock_tea_clip2_keyframe_v1",
            "asset_mock_tea_clip2_keyframe_v1",
            baseTime.plusMinutes(70),
            dimensions[0],
            dimensions[1],
            "投入嫩芽",
            "Flux 方案 A",
            "镜头二：白瓷盖碗、嫩芽、热气与手部动作形成层次。"
        );
        KeyframeSeed teaClip3KeyframeV1 = createKeyframeSeed(
            workflow,
            teaStoryboardV2.version(),
            3,
            1,
            true,
            5,
            "收束画面干净，可直接进入视频阶段",
            "sv_mock_tea_clip3_keyframe_v1",
            "asset_mock_tea_clip3_keyframe_v1",
            baseTime.plusMinutes(82),
            dimensions[0],
            dimensions[1],
            "品牌收束",
            "Flux 方案 A",
            "镜头三：通透茶汤和品牌文案一同出现，画面简洁稳定。"
        );
        saveKeyframeSeed(teaClip1KeyframeV1, workflow, List.of("茶饮", "首帧", "候选"));
        saveKeyframeSeed(teaClip1KeyframeV2, workflow, List.of("茶饮", "首帧", "已选"));
        saveKeyframeSeed(teaClip2KeyframeV1, workflow, List.of("茶饮", "手部特写"));
        saveKeyframeSeed(teaClip3KeyframeV1, workflow, List.of("茶饮", "品牌收束"));

        try {
            VideoSeed teaClip1VideoV1 = createVideoSeed(
                workflow,
                teaClip1KeyframeV2,
                storyboardV2Clips.get(0),
                1,
                1,
                true,
                5,
                "开场礼盒主体稳定，可直接用于 join",
                "sv_mock_tea_clip1_video_v1",
                "asset_mock_tea_clip1_video_v1",
                baseTime.plusMinutes(120)
            );
            VideoSeed teaClip2VideoV1 = createVideoSeed(
                workflow,
                teaClip2KeyframeV1,
                storyboardV2Clips.get(1),
                2,
                1,
                false,
                3,
                "动作太平，可以保留作备选",
                "sv_mock_tea_clip2_video_v1",
                "asset_mock_tea_clip2_video_v1",
                baseTime.plusMinutes(135)
            );
            VideoSeed teaClip2VideoV2 = createVideoSeed(
                workflow,
                teaClip2KeyframeV1,
                storyboardV2Clips.get(1),
                2,
                2,
                true,
                5,
                "热气和叶片展开更自然，已选中",
                "sv_mock_tea_clip2_video_v2",
                "asset_mock_tea_clip2_video_v2",
                baseTime.plusMinutes(148)
            );
            VideoSeed teaClip3VideoV1 = createVideoSeed(
                workflow,
                teaClip3KeyframeV1,
                storyboardV2Clips.get(2),
                3,
                1,
                true,
                4,
                "结尾收束明确，可直接拼接",
                "sv_mock_tea_clip3_video_v1",
                "asset_mock_tea_clip3_video_v1",
                baseTime.plusMinutes(162)
            );
            saveVideoSeed(teaClip1VideoV1, workflow, List.of("茶饮", "成片候选"));
            saveVideoSeed(teaClip2VideoV1, workflow, List.of("茶饮", "备选视频"));
            saveVideoSeed(teaClip2VideoV2, workflow, List.of("茶饮", "已选视频"));
            saveVideoSeed(teaClip3VideoV1, workflow, List.of("茶饮", "收束镜头"));

            LocalMediaArtifactService.StoredArtifact joinedArtifact = localMediaArtifactService.concatVideos(
                workflowRelativeDir(workflowId) + "/joined",
                "join-3.mp4",
                List.of(
                    teaClip1VideoV1.asset().getPublicUrl(),
                    teaClip2VideoV2.asset().getPublicUrl(),
                    teaClip3VideoV1.asset().getPublicUrl()
                )
            );
            MaterialAssetEntity joinAsset = assetEntity(
                "asset_mock_tea_join_v1",
                workflow,
                WorkflowConstants.STAGE_JOINED,
                3,
                1,
                true,
                5,
                "当前选中镜头已自动拼接为成片",
                "video",
                "明前春茶上新 拼接结果",
                "mock",
                workflow.getVideoModel(),
                "video/mp4",
                joinedArtifact.publicUrl(),
                sumDurations(List.of(teaClip1VideoV1.asset(), teaClip2VideoV2.asset(), teaClip3VideoV1.asset())),
                0,
                0,
                true,
                baseTime.plusMinutes(175),
                Map.of(
                    "mock", true,
                    "clipIndices", List.of(1, 2, 3),
                    "sourceUrls", List.of(
                        teaClip1VideoV1.asset().getPublicUrl(),
                        teaClip2VideoV2.asset().getPublicUrl(),
                        teaClip3VideoV1.asset().getPublicUrl()
                    )
                )
            );
            workflowRepository.saveMaterialAsset(joinAsset);
            saveTags(joinAsset, workflow, List.of("茶饮", "成片", "可下载"));

            workflow.setFinalJoinAssetId(joinAsset.getMaterialAssetId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
            workflow.setStatus(WorkflowConstants.STATUS_COMPLETED);
            workflow.setEffectRating(5);
            workflow.setEffectRatingNote("当前 mock 数据用于验证阶段工作流和素材库联动");
            workflow.setRatedAt(baseTime.plusMinutes(180));
            workflow.setUpdateTime(baseTime.plusMinutes(180));
        } catch (Exception ex) {
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
            workflow.setFinalJoinAssetId("");
            workflow.setUpdateTime(baseTime.plusMinutes(170));
            log.warn("skip tea workflow video/join mock bootstrap: {}", ex.getMessage());
        }

        workflowRepository.saveWorkflow(workflow);
    }

    private void seedCampingWorkflow(SysUserEntity owner) {
        String workflowId = "wf_mock_camping_ad";
        OffsetDateTime baseTime = OffsetDateTime.now(ZoneOffset.UTC).minusHours(18);
        int[] dimensions = dimensions("16:9");

        List<Map<String, Object>> storyboardClips = List.of(
            clip(1, "镜头一", "露营箱与折叠桌从后备箱中被拉出。", "广角横移，强调户外氛围和装备体积感。", "露营地、后备箱、装备陈列、清晨逆光", "广角镜头横移掠过露营地和后备箱装备，户外氛围鲜明，广告片质感", 4),
            clip(2, "镜头二", "便携炉具点火，水壶开始冒出热气。", "中景定机，突出功能细节和热气反馈。", "炉具、水壶、点火、热气、金属质感", "便携炉具点火后水壶热气升起，强调装备功能和可靠性", 5),
            clip(3, "镜头三", "人物落座，品牌 Slogan 收在山谷远景。", "拉远收束，形成品牌记忆点。", "人物、山谷、天幕、收束文案、远景", "人物坐下看向山谷远景，品牌文案自然出现，形成广告结尾", 4)
        );

        StageWorkflowEntity workflow = workflowEntity(
            workflowId,
            owner,
            "城市露营装备广告",
            "生成一支 15 秒横屏露营装备广告片，突出装备便携、点火反馈和户外场景感。",
            "自然户外、真实材质、强调装备功能反馈。",
            "16:9",
            "outdoor-commercial",
            "gpt-5.1-mini",
            "gpt-4.1-mini",
            "flux-1.1-dev",
            "kling-v1-6",
            "720p",
            20260419,
            4,
            5,
            WorkflowConstants.STATUS_READY,
            WorkflowConstants.STAGE_VIDEO,
            "sv_mock_camping_storyboard_v1",
            "",
            null,
            "",
            baseTime,
            baseTime.plusHours(3),
            Map.of(
                "mock", true,
                "mode", "stage-workflow",
                "scenario", "camping-commercial"
            )
        );
        workflowRepository.saveWorkflow(workflow);

        TextSeed campingStoryboard = createStoryboardSeed(
            workflow,
            "storyboard-v1.md",
            1,
            true,
            4,
            "镜头结构清楚，等待继续补关键帧和视频",
            "sv_mock_camping_storyboard_v1",
            "asset_mock_camping_storyboard_v1",
            baseTime.plusMinutes(8),
            storyboardClips
        );
        saveTextSeed(campingStoryboard, workflow, List.of("露营", "横版", "装备"));

        KeyframeSeed campingClip1KeyframeV1 = createKeyframeSeed(
            workflow,
            campingStoryboard.version(),
            1,
            1,
            false,
            3,
            "场景信息完整，但品牌露出偏弱",
            "sv_mock_camping_clip1_keyframe_v1",
            "asset_mock_camping_clip1_keyframe_v1",
            baseTime.plusMinutes(30),
            dimensions[0],
            dimensions[1],
            "后备箱展开",
            "Flux 方案 A",
            "镜头一：装备从后备箱展开，突出户外氛围。"
        );
        KeyframeSeed campingClip1KeyframeV2 = createKeyframeSeed(
            workflow,
            campingStoryboard.version(),
            1,
            2,
            true,
            5,
            "装备主体明确，适合作为当前镜头已选关键帧",
            "sv_mock_camping_clip1_keyframe_v2",
            "asset_mock_camping_clip1_keyframe_v2",
            baseTime.plusMinutes(44),
            dimensions[0],
            dimensions[1],
            "后备箱展开",
            "Flux 方案 B",
            "镜头一：装备与露营地更清晰，画面更适合继续生成视频。"
        );
        KeyframeSeed campingClip2KeyframeV1 = createKeyframeSeed(
            workflow,
            campingStoryboard.version(),
            2,
            1,
            true,
            4,
            "火焰反馈明确，已作为当前镜头基准",
            "sv_mock_camping_clip2_keyframe_v1",
            "asset_mock_camping_clip2_keyframe_v1",
            baseTime.plusMinutes(58),
            dimensions[0],
            dimensions[1],
            "炉具点火",
            "Flux 方案 A",
            "镜头二：炉具点火和热气反馈是画面重点。"
        );
        saveKeyframeSeed(campingClip1KeyframeV1, workflow, List.of("露营", "候选"));
        saveKeyframeSeed(campingClip1KeyframeV2, workflow, List.of("露营", "已选"));
        saveKeyframeSeed(campingClip2KeyframeV1, workflow, List.of("露营", "炉具"));

        try {
            VideoSeed campingClip1VideoV1 = createVideoSeed(
                workflow,
                campingClip1KeyframeV2,
                storyboardClips.get(0),
                1,
                1,
                true,
                4,
                "镜头一已有可用视频，等待后续镜头继续补齐",
                "sv_mock_camping_clip1_video_v1",
                "asset_mock_camping_clip1_video_v1",
                baseTime.plusMinutes(95)
            );
            saveVideoSeed(campingClip1VideoV1, workflow, List.of("露营", "阶段中"));
            workflow.setUpdateTime(baseTime.plusMinutes(96));
        } catch (Exception ex) {
            log.warn("skip camping workflow video mock bootstrap: {}", ex.getMessage());
        }

        workflowRepository.saveWorkflow(workflow);
    }

    private TextSeed createStoryboardSeed(
        StageWorkflowEntity workflow,
        String fileName,
        int versionNo,
        boolean selected,
        Integer rating,
        String ratingNote,
        String versionId,
        String assetId,
        OffsetDateTime time,
        List<Map<String, Object>> clips
    ) {
        String markdown = buildStoryboardMarkdown(workflow.getTitle(), clips);
        LocalMediaArtifactService.TextArtifact artifact = localMediaArtifactService.writeText(
            workflowRelativeDir(workflow.getWorkflowId()) + "/storyboards",
            fileName,
            markdown
        );
        MaterialAssetEntity asset = assetEntity(
            assetId,
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            0,
            versionNo,
            selected,
            rating,
            ratingNote,
            "text",
            workflow.getTitle() + " 分镜脚本 V" + versionNo,
            "mock",
            workflow.getTextAnalysisModel(),
            artifact.mimeType(),
            artifact.publicUrl(),
            0.0,
            0,
            0,
            false,
            time,
            Map.of(
                "mock", true,
                "scriptMarkdown", markdown,
                "clipCount", clips.size()
            )
        );
        StageVersionEntity version = versionEntity(
            versionId,
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            0,
            versionNo,
            "分镜脚本 V" + versionNo,
            selected,
            rating,
            ratingNote,
            "",
            "",
            asset,
            time,
            Map.of(
                "title", workflow.getTitle(),
                "transcriptLength", workflow.getTranscriptText().length(),
                "globalPrompt", workflow.getGlobalPrompt()
            ),
            Map.of(
                "scriptMarkdown", markdown,
                "clips", clips,
                "clipCount", clips.size(),
                "previewText", markdown.length() > 220 ? markdown.substring(0, 220) : markdown
            ),
            Map.of(
                "mock", true,
                "provider", "bootstrap",
                "model", workflow.getTextAnalysisModel()
            )
        );
        return new TextSeed(asset, version);
    }

    private KeyframeSeed createKeyframeSeed(
        StageWorkflowEntity workflow,
        StageVersionEntity parentStoryboardVersion,
        int clipIndex,
        int versionNo,
        boolean selected,
        Integer rating,
        String ratingNote,
        String versionId,
        String assetId,
        OffsetDateTime time,
        int width,
        int height,
        String title,
        String subtitle,
        String bodyText
    ) {
        LocalMediaArtifactService.ImageArtifact artifact = localMediaArtifactService.writePromptCard(
            workflowRelativeDir(workflow.getWorkflowId()) + "/keyframes",
            "clip" + clipIndex + "-v" + versionNo + ".png",
            width,
            height,
            title,
            subtitle,
            bodyText
        );
        MaterialAssetEntity asset = assetEntity(
            assetId,
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            selected,
            rating,
            ratingNote,
            "image",
            workflow.getTitle() + " 关键帧 #" + clipIndex + " V" + versionNo,
            "mock",
            workflow.getImageModel(),
            artifact.mimeType(),
            artifact.publicUrl(),
            0.0,
            artifact.width(),
            artifact.height(),
            false,
            time,
            Map.of(
                "mock", true,
                "frameRole", "first",
                "clipIndex", clipIndex
            )
        );
        StageVersionEntity version = versionEntity(
            versionId,
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            "关键帧 #" + clipIndex + " V" + versionNo,
            selected,
            rating,
            ratingNote,
            parentStoryboardVersion.getStageVersionId(),
            "",
            asset,
            time,
            Map.of(
                "clipIndex", clipIndex,
                "imageModel", workflow.getImageModel()
            ),
            Map.of(
                "clipIndex", clipIndex,
                "fileUrl", artifact.publicUrl(),
                "width", artifact.width(),
                "height", artifact.height()
            ),
            Map.of(
                "mock", true,
                "provider", "bootstrap",
                "model", workflow.getImageModel()
            )
        );
        return new KeyframeSeed(artifact, asset, version);
    }

    private VideoSeed createVideoSeed(
        StageWorkflowEntity workflow,
        KeyframeSeed keyframeSeed,
        Map<String, Object> clip,
        int clipIndex,
        int versionNo,
        boolean selected,
        Integer rating,
        String ratingNote,
        String versionId,
        String assetId,
        OffsetDateTime time
    ) {
        int[] dimensions = dimensions(workflow.getAspectRatio());
        int durationSeconds = intValue(clip.get("targetDurationSeconds"), workflow.getMaxDurationSeconds() == null ? 4 : workflow.getMaxDurationSeconds());
        LocalMediaArtifactService.VideoArtifact artifact = localMediaArtifactService.writeSilentVideo(
            workflowRelativeDir(workflow.getWorkflowId()) + "/videos",
            "clip" + clipIndex + "-v" + versionNo + ".mp4",
            dimensions[0],
            dimensions[1],
            durationSeconds,
            keyframeSeed.imageArtifact()
        );
        MaterialAssetEntity asset = assetEntity(
            assetId,
            workflow,
            WorkflowConstants.STAGE_VIDEO,
            clipIndex,
            versionNo,
            selected,
            rating,
            ratingNote,
            "video",
            workflow.getTitle() + " 视频 #" + clipIndex + " V" + versionNo,
            "mock",
            workflow.getVideoModel(),
            artifact.mimeType(),
            artifact.publicUrl(),
            (double) artifact.durationSeconds(),
            artifact.width(),
            artifact.height(),
            true,
            time,
            Map.of(
                "mock", true,
                "clip", clip,
                "firstFrameUrl", keyframeSeed.asset().getPublicUrl(),
                "lastFrameUrl", keyframeSeed.asset().getPublicUrl()
            )
        );
        StageVersionEntity version = versionEntity(
            versionId,
            workflow,
            WorkflowConstants.STAGE_VIDEO,
            clipIndex,
            versionNo,
            "视频 #" + clipIndex + " V" + versionNo,
            selected,
            rating,
            ratingNote,
            keyframeSeed.version().getStageVersionId(),
            keyframeSeed.asset().getMaterialAssetId(),
            asset,
            time,
            Map.of(
                "clipIndex", clipIndex,
                "videoPrompt", stringValue(clip.get("videoPrompt")),
                "keyframeAssetId", keyframeSeed.asset().getMaterialAssetId()
            ),
            Map.of(
                "clip", clip,
                "fileUrl", artifact.publicUrl(),
                "durationSeconds", artifact.durationSeconds(),
                "lastFrameUrl", keyframeSeed.asset().getPublicUrl()
            ),
            Map.of(
                "mock", true,
                "provider", "bootstrap",
                "model", workflow.getVideoModel()
            )
        );
        return new VideoSeed(asset, version);
    }

    private void saveTextSeed(TextSeed seed, StageWorkflowEntity workflow, List<String> customTags) {
        workflowRepository.saveMaterialAsset(seed.asset());
        workflowRepository.saveStageVersion(seed.version());
        saveTags(seed.asset(), workflow, customTags);
    }

    private void saveKeyframeSeed(KeyframeSeed seed, StageWorkflowEntity workflow, List<String> customTags) {
        workflowRepository.saveMaterialAsset(seed.asset());
        workflowRepository.saveStageVersion(seed.version());
        saveTags(seed.asset(), workflow, customTags);
    }

    private void saveVideoSeed(VideoSeed seed, StageWorkflowEntity workflow, List<String> customTags) {
        workflowRepository.saveMaterialAsset(seed.asset());
        workflowRepository.saveStageVersion(seed.version());
        saveTags(seed.asset(), workflow, customTags);
    }

    private void saveTags(MaterialAssetEntity asset, StageWorkflowEntity workflow, List<String> customTags) {
        List<MaterialAssetTagEntity> tags = new ArrayList<>();
        addSystemTag(tags, asset.getMaterialAssetId(), "stageType", asset.getStageType());
        addSystemTag(tags, asset.getMaterialAssetId(), "mediaType", asset.getMediaType());
        addSystemTag(tags, asset.getMaterialAssetId(), "model", asset.getOriginModel());
        addSystemTag(tags, asset.getMaterialAssetId(), "clipIndex", String.valueOf(intValue(asset.getClipIndex(), 0)));
        addSystemTag(tags, asset.getMaterialAssetId(), "selected", intValue(asset.getSelectedForNext(), 0) == 1 ? "selected" : "unselected");
        if (workflow != null) {
            addSystemTag(tags, asset.getMaterialAssetId(), "style", workflow.getStylePreset());
            addSystemTag(tags, asset.getMaterialAssetId(), "aspectRatio", workflow.getAspectRatio());
        }
        if (asset.getUserRating() != null) {
            addSystemTag(tags, asset.getMaterialAssetId(), "ratingBucket", asset.getUserRating() + "star");
        }
        for (String tagValue : normalizeCustomTags(customTags)) {
            MaterialAssetTagEntity tag = new MaterialAssetTagEntity();
            tag.setAssetTagId(randomTagId());
            tag.setMaterialAssetId(asset.getMaterialAssetId());
            tag.setTagType("custom");
            tag.setTagKey("custom");
            tag.setTagValue(tagValue);
            tag.setIsDeleted(0);
            tags.add(tag);
        }
        workflowRepository.saveMaterialAssetTags(asset.getMaterialAssetId(), tags);
    }

    private void addSystemTag(List<MaterialAssetTagEntity> tags, String assetId, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        MaterialAssetTagEntity tag = new MaterialAssetTagEntity();
        tag.setAssetTagId(randomTagId());
        tag.setMaterialAssetId(assetId);
        tag.setTagType("system");
        tag.setTagKey(key);
        tag.setTagValue(value);
        tag.setIsDeleted(0);
        tags.add(tag);
    }

    private StageWorkflowEntity workflowEntity(
        String workflowId,
        SysUserEntity owner,
        String title,
        String transcriptText,
        String globalPrompt,
        String aspectRatio,
        String stylePreset,
        String textAnalysisModel,
        String visionModel,
        String imageModel,
        String videoModel,
        String videoSize,
        Integer seed,
        Integer minDurationSeconds,
        Integer maxDurationSeconds,
        String status,
        String currentStage,
        String selectedStoryboardVersionId,
        String finalJoinAssetId,
        Integer effectRating,
        String effectRatingNote,
        OffsetDateTime createTime,
        OffsetDateTime updateTime,
        Map<String, Object> metadata
    ) {
        StageWorkflowEntity workflow = new StageWorkflowEntity();
        workflow.setWorkflowId(workflowId);
        workflow.setOwnerUserId(owner.getId());
        workflow.setTitle(title);
        workflow.setTranscriptText(transcriptText);
        workflow.setGlobalPrompt(globalPrompt);
        workflow.setAspectRatio(aspectRatio);
        workflow.setStylePreset(stylePreset);
        workflow.setTextAnalysisModel(textAnalysisModel);
        workflow.setVisionModel(visionModel);
        workflow.setImageModel(imageModel);
        workflow.setVideoModel(videoModel);
        workflow.setVideoSize(videoSize);
        workflow.setTaskSeed(seed);
        workflow.setMinDurationSeconds(minDurationSeconds);
        workflow.setMaxDurationSeconds(maxDurationSeconds);
        workflow.setStatus(status);
        workflow.setCurrentStage(currentStage);
        workflow.setSelectedStoryboardVersionId(selectedStoryboardVersionId);
        workflow.setFinalJoinAssetId(finalJoinAssetId);
        workflow.setEffectRating(effectRating);
        workflow.setEffectRatingNote(effectRatingNote == null ? "" : effectRatingNote);
        workflow.setMetadataJson(WorkflowJsonSupport.write(metadata));
        workflow.setCreateTime(createTime);
        workflow.setUpdateTime(updateTime);
        workflow.setIsDeleted(0);
        return workflow;
    }

    private StageVersionEntity versionEntity(
        String versionId,
        StageWorkflowEntity workflow,
        String stageType,
        int clipIndex,
        int versionNo,
        String title,
        boolean selected,
        Integer rating,
        String ratingNote,
        String parentVersionId,
        String sourceMaterialAssetId,
        MaterialAssetEntity asset,
        OffsetDateTime time,
        Map<String, Object> inputSummary,
        Map<String, Object> outputSummary,
        Map<String, Object> modelSummary
    ) {
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId(versionId);
        version.setWorkflowId(workflow.getWorkflowId());
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(stageType);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle(title);
        version.setStatus("SUCCEEDED");
        version.setSelected(selected ? 1 : 0);
        version.setRating(rating);
        version.setRatingNote(ratingNote == null ? "" : ratingNote);
        version.setRatedAt(rating == null ? null : time);
        version.setParentVersionId(parentVersionId == null ? "" : parentVersionId);
        version.setSourceMaterialAssetId(sourceMaterialAssetId == null ? "" : sourceMaterialAssetId);
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(asset.getPublicUrl());
        version.setDownloadUrl(asset.getPublicUrl());
        version.setInputSummaryJson(WorkflowJsonSupport.write(inputSummary));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(modelSummary));
        version.setCreateTime(time);
        version.setUpdateTime(time);
        version.setIsDeleted(0);
        return version;
    }

    private MaterialAssetEntity assetEntity(
        String assetId,
        StageWorkflowEntity workflow,
        String stageType,
        int clipIndex,
        int versionNo,
        boolean selectedForNext,
        Integer rating,
        String ratingNote,
        String mediaType,
        String title,
        String originProvider,
        String originModel,
        String mimeType,
        String publicUrl,
        double durationSeconds,
        int width,
        int height,
        boolean hasAudio,
        OffsetDateTime time,
        Map<String, Object> metadata
    ) {
        MaterialAssetEntity asset = new MaterialAssetEntity();
        asset.setMaterialAssetId(assetId);
        asset.setOwnerUserId(workflow.getOwnerUserId());
        asset.setTaskId("");
        asset.setWorkflowId(workflow.getWorkflowId());
        asset.setSourceTaskId("");
        asset.setSourceMaterialId("");
        asset.setAssetRole(stageType);
        asset.setStageType(stageType);
        asset.setClipIndex(clipIndex);
        asset.setVersionNo(versionNo);
        asset.setSelectedForNext(selectedForNext ? 1 : 0);
        asset.setUserRating(rating);
        asset.setRatingNote(ratingNote == null ? "" : ratingNote);
        asset.setMediaType(mediaType);
        asset.setTitle(title);
        asset.setOriginProvider(originProvider);
        asset.setOriginModel(originModel);
        asset.setRemoteTaskId("");
        asset.setRemoteAssetId("");
        asset.setOriginalFileName(fileNameFromUrl(publicUrl));
        asset.setStoredFileName(fileNameFromUrl(publicUrl));
        asset.setFileExt(fileExt(publicUrl));
        asset.setStorageProvider("local");
        asset.setMimeType(mimeType);
        asset.setSizeBytes(fileSize(publicUrl));
        asset.setSha256("");
        asset.setDurationSeconds(durationSeconds);
        asset.setWidth(width);
        asset.setHeight(height);
        asset.setHasAudio(hasAudio ? 1 : 0);
        asset.setLocalStoragePath(localMediaArtifactService.resolveAbsolutePath(publicUrl));
        asset.setLocalFilePath(localMediaArtifactService.resolveAbsolutePath(publicUrl));
        asset.setPublicUrl(publicUrl);
        asset.setThirdPartyUrl("");
        asset.setRemoteUrl("");
        asset.setMetadataJson(WorkflowJsonSupport.write(metadata));
        asset.setCapturedAt(time);
        asset.setTimezoneOffsetMinutes(480);
        asset.setCreateTime(time);
        asset.setUpdateTime(time);
        asset.setIsDeleted(0);
        return asset;
    }

    private List<String> normalizeCustomTags(List<String> values) {
        if (values == null || values.isEmpty()) {
            return List.of();
        }
        List<String> normalized = new ArrayList<>();
        for (String value : values) {
            String item = value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
            if (!item.isBlank() && !normalized.contains(item)) {
                normalized.add(item);
            }
        }
        return normalized;
    }

    private SysUserEntity resolveSeedOwner() {
        List<SysUserEntity> users = authRepository.listUsers();
        for (SysUserEntity user : users) {
            if ("ADMIN".equalsIgnoreCase(user.getRole()) && "ACTIVE".equalsIgnoreCase(user.getStatus())) {
                return user;
            }
        }
        for (SysUserEntity user : users) {
            if ("ADMIN".equalsIgnoreCase(user.getRole())) {
                return user;
            }
        }
        return users.isEmpty() ? null : users.get(0);
    }

    private boolean isDevelopmentEnv() {
        String env = appProperties.getEnv();
        if (env == null || env.isBlank()) {
            return true;
        }
        return "dev".equalsIgnoreCase(env.trim()) || "local".equalsIgnoreCase(env.trim());
    }

    private String workflowRelativeDir(String workflowId) {
        return "mock/workflows/" + workflowId;
    }

    private int[] dimensions(String aspectRatio) {
        if ("16:9".equalsIgnoreCase(aspectRatio)) {
            return new int[] {1280, 720};
        }
        return new int[] {720, 1280};
    }

    private Map<String, Object> clip(
        int clipIndex,
        String shotLabel,
        String scene,
        String cameraMovement,
        String imagePrompt,
        String videoPrompt,
        int durationSeconds
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("clipIndex", clipIndex);
        row.put("shotLabel", shotLabel);
        row.put("scene", scene);
        row.put("firstFramePrompt", imagePrompt);
        row.put("lastFramePrompt", scene);
        row.put("motion", "slow and stable");
        row.put("cameraMovement", cameraMovement);
        row.put("durationHint", durationSeconds + "s");
        row.put("imagePrompt", imagePrompt);
        row.put("videoPrompt", videoPrompt);
        row.put("targetDurationSeconds", durationSeconds);
        row.put("minDurationSeconds", Math.max(3, durationSeconds - 1));
        row.put("maxDurationSeconds", durationSeconds);
        return row;
    }

    private String buildStoryboardMarkdown(String workflowTitle, List<Map<String, Object>> clips) {
        StringBuilder builder = new StringBuilder();
        builder.append("# ").append(workflowTitle).append(" 分镜稿").append("\n\n");
        for (Map<String, Object> clip : clips) {
            builder.append("## ").append(stringValue(clip.get("shotLabel"))).append(" / Clip ").append(intValue(clip.get("clipIndex"), 0)).append("\n");
            builder.append("- 场景：").append(stringValue(clip.get("scene"))).append("\n");
            builder.append("- 运镜：").append(stringValue(clip.get("cameraMovement"))).append("\n");
            builder.append("- 关键帧提示词：").append(stringValue(clip.get("imagePrompt"))).append("\n");
            builder.append("- 视频提示词：").append(stringValue(clip.get("videoPrompt"))).append("\n");
            builder.append("- 时长建议：").append(stringValue(clip.get("durationHint"))).append("\n\n");
        }
        return builder.toString();
    }

    private double sumDurations(List<MaterialAssetEntity> assets) {
        double total = 0.0;
        for (MaterialAssetEntity asset : assets) {
            total += asset.getDurationSeconds() == null ? 0.0 : asset.getDurationSeconds();
        }
        return total;
    }

    private long fileSize(String publicUrl) {
        String path = localMediaArtifactService.resolveAbsolutePath(publicUrl);
        if (path == null || path.isBlank()) {
            return 0L;
        }
        try {
            return java.nio.file.Files.size(java.nio.file.Path.of(path));
        } catch (Exception ex) {
            return 0L;
        }
    }

    private String fileNameFromUrl(String publicUrl) {
        String value = stringValue(publicUrl);
        int index = value.lastIndexOf('/');
        return index >= 0 ? value.substring(index + 1) : value;
    }

    private String fileExt(String publicUrl) {
        String fileName = fileNameFromUrl(publicUrl);
        int index = fileName.lastIndexOf('.');
        return index >= 0 ? fileName.substring(index + 1) : "";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return value == null ? defaultValue : Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return defaultValue;
        }
    }

    private String randomTagId() {
        return "atag_" + UUID.randomUUID().toString().replace("-", "");
    }

    private record TextSeed(MaterialAssetEntity asset, StageVersionEntity version) {
    }

    private record KeyframeSeed(
        LocalMediaArtifactService.ImageArtifact imageArtifact,
        MaterialAssetEntity asset,
        StageVersionEntity version
    ) {
    }

    private record VideoSeed(MaterialAssetEntity asset, StageVersionEntity version) {
    }
}
