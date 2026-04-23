package com.jiandou.api.workflow.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anySet;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.auth.security.CurrentUserPrincipal;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.workflow.WorkflowConstants;
import com.jiandou.api.workflow.infrastructure.WorkflowJsonSupport;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

class WorkflowApplicationServiceTest {

    private static final long USER_ID = 100L;

    private WorkflowRepository workflowRepository;
    private GenerationApplicationService generationApplicationService;
    private TaskStoryboardPlanner storyboardPlanner;
    private LocalMediaArtifactService localMediaArtifactService;
    private WorkflowApplicationService service;

    private Map<String, StageWorkflowEntity> workflows;
    private Map<String, StageVersionEntity> versions;
    private Map<String, MaterialAssetEntity> assets;

    @BeforeEach
    void setUp() {
        workflowRepository = mock(WorkflowRepository.class);
        generationApplicationService = mock(GenerationApplicationService.class);
        storyboardPlanner = mock(TaskStoryboardPlanner.class);
        localMediaArtifactService = mock(LocalMediaArtifactService.class);
        service = new WorkflowApplicationService(workflowRepository, generationApplicationService, storyboardPlanner, localMediaArtifactService);

        workflows = new LinkedHashMap<>();
        versions = new LinkedHashMap<>();
        assets = new LinkedHashMap<>();

        CurrentUserPrincipal principal = new CurrentUserPrincipal(USER_ID, "tester", "Tester", "ADMIN", "ACTIVE");
        SecurityContextHolder.getContext().setAuthentication(
            new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities())
        );

        when(localMediaArtifactService.resolveAbsolutePath(anyString())).thenAnswer(invocation -> invocation.getArgument(0));
        when(workflowRepository.findWorkflow(anyString(), anyLong())).thenAnswer(invocation -> {
            StageWorkflowEntity workflow = workflows.get(invocation.getArgument(0));
            return workflow == null || intValue(workflow.getIsDeleted(), 0) == 1 ? null : workflow;
        });
        when(workflowRepository.findStageVersion(anyString(), anyString())).thenAnswer(invocation -> findStageVersion(invocation.getArgument(0), invocation.getArgument(1)));
        when(workflowRepository.listStageVersions(anyString())).thenAnswer(invocation -> listStageVersions(invocation.getArgument(0)));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of());
        when(workflowRepository.nextStageVersionNo(anyString(), anyString(), anyInt())).thenAnswer(invocation -> nextVersionNo(
            invocation.getArgument(0),
            invocation.getArgument(1),
            invocation.getArgument(2)
        ));
        when(workflowRepository.findMaterialAsset(anyString(), anyLong())).thenAnswer(invocation -> {
            MaterialAssetEntity asset = assets.get(invocation.getArgument(0));
            return asset == null || intValue(asset.getIsDeleted(), 0) == 1 ? null : asset;
        });
        when(workflowRepository.findMaterialAssetsByIds(anySet(), anyLong())).thenAnswer(invocation -> findMaterialAssets(invocation.getArgument(0)));
        when(workflowRepository.listMaterialAssets(anyLong())).thenAnswer(invocation -> new ArrayList<>(assets.values()));
        when(workflowRepository.listTags(anyString())).thenReturn(List.of());
        when(workflowRepository.listTagsByAssetIds(anyCollection())).thenReturn(Map.of());
        doNothing().when(workflowRepository).saveMaterialAssetTags(anyString(), any());
        doNothing().when(workflowRepository).saveSystemLog(anyString(), anyString(), anyString(), anyString(), anyString(), anyString(), any());
        doNothing().when(workflowRepository).saveModelCall(anyString(), any());
        doAnswer(invocation -> {
            String workflowId = invocation.getArgument(0);
            String stageType = invocation.getArgument(1);
            int clipIndex = invocation.getArgument(2);
            String versionId = invocation.getArgument(3);
            for (StageVersionEntity entity : versions.values()) {
                if (workflowId.equals(entity.getWorkflowId())
                    && stageType.equals(entity.getStageType())
                    && clipIndex == intValue(entity.getClipIndex(), 0)) {
                    entity.setSelected(entity.getStageVersionId().equals(versionId) ? 1 : 0);
                }
            }
            return null;
        }).when(workflowRepository).markSelectedStageVersion(anyString(), anyString(), anyInt(), anyString());
        doAnswer(invocation -> {
            String workflowId = invocation.getArgument(0);
            String stageType = invocation.getArgument(1);
            Object clipIndex = invocation.getArgument(2);
            for (StageVersionEntity entity : versions.values()) {
                if (!workflowId.equals(entity.getWorkflowId()) || !stageType.equals(entity.getStageType())) {
                    continue;
                }
                if (clipIndex != null && intValue(entity.getClipIndex(), 0) != intValue(clipIndex, 0)) {
                    continue;
                }
                entity.setSelected(0);
            }
            return null;
        }).when(workflowRepository).clearSelectedStageVersions(anyString(), anyString(), any());

        doAnswer(invocation -> {
            StageWorkflowEntity entity = invocation.getArgument(0);
            workflows.put(entity.getWorkflowId(), entity);
            return null;
        }).when(workflowRepository).saveWorkflow(any());
        doAnswer(invocation -> {
            StageVersionEntity entity = invocation.getArgument(0);
            versions.put(entity.getStageVersionId(), entity);
            return null;
        }).when(workflowRepository).saveStageVersion(any());
        doAnswer(invocation -> {
            MaterialAssetEntity entity = invocation.getArgument(0);
            assets.put(entity.getMaterialAssetId(), entity);
            return null;
        }).when(workflowRepository).saveMaterialAsset(any());
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void generateKeyframeForFirstClipStoresStartAndEndFrames() {
        StageWorkflowEntity workflow = workflow("wf_1");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_start", "https://cdn.example.com/clip1-first.png"),
            imageRun("run_end", "https://cdn.example.com/clip1-last.png")
        );

        Map<String, Object> detail = service.generateKeyframe("wf_1", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, org.mockito.Mockito.times(2)).createRun(requestCaptor.capture());
        List<Map<String, Object>> requests = requestCaptor.getAllValues();
        assertEquals("first", mapValue(requests.get(0).get("input")).get("frameRole"));
        assertEquals("last", mapValue(requests.get(1).get("input")).get("frameRole"));
        assertEquals("https://cdn.example.com/clip1-first.png", mapValue(requests.get(1).get("input")).get("referenceImageUrl"));

        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getOutputSummaryJson());
        assertEquals("https://cdn.example.com/clip1-first.png", outputSummary.get("firstFrameUrl"));
        assertEquals("https://cdn.example.com/clip1-last.png", outputSummary.get("lastFrameUrl"));
        assertEquals("https://cdn.example.com/clip1-first.png", outputSummary.get("firstFrameRemoteUrl"));
        assertEquals("https://cdn.example.com/clip1-last.png", outputSummary.get("lastFrameRemoteUrl"));
        assertEquals(2, listValue(outputSummary.get("generatedFrames")).size());

        List<Map<String, Object>> clipSlots = listValue(detail.get("clipSlots"));
        assertFalse(clipSlots.isEmpty());
        Map<String, Object> clipSlot = clipSlots.get(0);
        assertEquals("镜头开场，角色推门进入废弃图书馆。", clipSlot.get("startFrame"));
        assertEquals("角色停在门口，回望黑暗书架。", clipSlot.get("endFrame"));
        assertNotNull(clipSlot.get("actionPath"));
        assertNotNull(clipSlot.get("continuity"));
    }

    @Test
    void generateFirstClipCreatesMissingCharacterSheetsBeforeClipKeyframe() {
        StageWorkflowEntity workflow = workflow("wf_character");
        workflow.setGlobalPrompt("新海诚动漫风，空气透视明显，光影清透。");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition(
                "林舒",
                "鬓角垂落一缕碎发，身着素色针织开衫与深色长裤",
                "女性，约28岁。外观锚点：鬓角垂落一缕碎发，身着素色针织开衫与深色长裤。行为特征：情绪内敛克制。说话风格：语气平静略带自嘲。"
            ),
            new TaskStoryboardPlanner.CharacterDefinition(
                "周泽",
                "穿着深灰休闲西装外套，内搭素色衬衫",
                "男性，约29岁。外观锚点：穿着深灰休闲西装外套，内搭素色衬衫。行为特征：主动开口但声音干涩。说话风格：低沉缓慢。"
            )
        ));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_sheet_1", "https://cdn.example.com/character-1.png"),
            imageRun("run_sheet_2", "https://cdn.example.com/character-2.png"),
            imageRun("run_start", "https://cdn.example.com/clip1-first.png"),
            imageRun("run_end", "https://cdn.example.com/clip1-last.png")
        );

        Map<String, Object> detail = service.generateKeyframe("wf_character", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, org.mockito.Mockito.times(4)).createRun(requestCaptor.capture());
        List<Map<String, Object>> requests = requestCaptor.getAllValues();
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("角色完整定义：女性，约28岁"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("三视图设定图"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("完整的从头到脚全身像"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("不得出现任何文字"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("背景必须是纯白色背景"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("三视图设定图"));
        assertTrue(String.valueOf(mapValue(requests.get(2).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertEquals("first", mapValue(requests.get(2).get("input")).get("frameRole"));
        assertTrue(String.valueOf(mapValue(requests.get(3).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertEquals("last", mapValue(requests.get(3).get("input")).get("frameRole"));

        List<StageVersionEntity> keyframeVersions = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .toList();
        assertEquals(3, keyframeVersions.size());
        assertTrue(keyframeVersions.stream().anyMatch(item -> intValue(item.getClipIndex(), 0) == 1001));
        assertTrue(keyframeVersions.stream().anyMatch(item -> intValue(item.getClipIndex(), 0) == 1002));

        List<Map<String, Object>> characterSheets = listValue(detail.get("characterSheets"));
        assertEquals(2, characterSheets.size());
        assertEquals("林舒", characterSheets.get(0).get("characterName"));
        assertFalse(listValue(characterSheets.get(0).get("versions")).isEmpty());
    }

    @Test
    void generateVideoPrefersPreviousSelectedVideoLastFrameUrl() {
        StageWorkflowEntity workflow = workflow("wf_2");
        workflow.setGlobalPrompt("新海诚动漫风，空气透视明显，光影清透。");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story_2", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        versions.put("sv_video_1", videoVersion(workflow.getWorkflowId(), 1, "asset_video_1", "https://cdn.example.com/clip1.mp4", "https://cdn.example.com/video-last.png"));
        versions.put("sv_key_2", keyframeVersion(workflow.getWorkflowId(), 2, "asset_key_2", "https://cdn.example.com/clip2-last.png"));
        assets.put("asset_video_1", asset(workflow.getWorkflowId(), "asset_video_1", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/clip1.mp4", "video/mp4"));
        assets.put("asset_key_2", asset(workflow.getWorkflowId(), "asset_key_2", WorkflowConstants.STAGE_KEYFRAME, 2, "https://cdn.example.com/clip2-last.png", "image/png"));

        when(generationApplicationService.createRun(any())).thenReturn(videoRun(
            "run_video_2",
            "https://cdn.example.com/clip2.mp4",
            "https://cdn.example.com/video-last.png",
            "https://cdn.example.com/clip2-last.png",
            "https://cdn.example.com/generated-last.png"
        ));

        service.generateVideo("wf_2", 2);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("https://cdn.example.com/video-last.png", input.get("firstFrameUrl"));
        assertEquals("https://cdn.example.com/clip2-last.png", input.get("lastFrameUrl"));
        assertTrue(String.valueOf(input.get("prompt")).contains("全局画风要求：新海诚动漫风"));

        StageVersionEntity videoVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()) && item.getClipIndex() == 2)
            .findFirst()
            .orElseThrow();
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(videoVersion.getOutputSummaryJson());
        assertEquals("https://cdn.example.com/video-last.png", outputSummary.get("firstFrameUrl"));
        assertEquals("https://cdn.example.com/clip2-last.png", outputSummary.get("requestedLastFrameUrl"));
        assertEquals("https://cdn.example.com/generated-last.png", outputSummary.get("lastFrameUrl"));
    }

    @Test
    void generateVideoUsesRemoteKeyframeFrameUrlsWhenOnlyLocalUrlsAreStored() {
        StageWorkflowEntity workflow = workflow("wf_remote_frames");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        StageVersionEntity keyframeVersion = keyframeVersion(workflow.getWorkflowId(), 1, "asset_key_remote", "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png");
        keyframeVersion.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "firstFrameUrl", "/storage/workflows/wf_remote_frames/keyframes/clip1-first.png",
            "startFrameUrl", "/storage/workflows/wf_remote_frames/keyframes/clip1-first.png",
            "lastFrameUrl", "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png",
            "endFrameUrl", "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png",
            "fileUrl", "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png"
        )));
        keyframeVersion.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "startFrameRunId", "run_start_legacy",
            "endFrameRunId", "run_end_legacy"
        )));
        versions.put(keyframeVersion.getStageVersionId(), keyframeVersion);
        assets.put("asset_key_remote", asset(workflow.getWorkflowId(), "asset_key_remote", WorkflowConstants.STAGE_KEYFRAME, 1, "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png", "image/png"));

        when(generationApplicationService.getRun("run_start_legacy")).thenReturn(imageRun(
            "run_start_legacy",
            "/storage/workflows/wf_remote_frames/keyframes/clip1-first.png",
            "https://cdn.example.com/clip1-first-remote.png"
        ));
        when(generationApplicationService.getRun("run_end_legacy")).thenReturn(imageRun(
            "run_end_legacy",
            "/storage/workflows/wf_remote_frames/keyframes/clip1-last.png",
            "https://cdn.example.com/clip1-last-remote.png"
        ));
        when(generationApplicationService.createRun(any())).thenReturn(videoRun(
            "run_video_remote",
            "https://cdn.example.com/clip1.mp4",
            "https://cdn.example.com/clip1-first-remote.png",
            "https://cdn.example.com/clip1-last-remote.png",
            "https://cdn.example.com/clip1-generated-last.png"
        ));

        service.generateVideo("wf_remote_frames", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("https://cdn.example.com/clip1-first-remote.png", input.get("firstFrameUrl"));
        assertEquals("https://cdn.example.com/clip1-last-remote.png", input.get("lastFrameUrl"));
    }

    @Test
    void workflowDetailResolvesSecondClipStartFrameFromCurrentPreviousSelection() {
        StageWorkflowEntity workflow = workflow("wf_detail_sync");
        workflow.setSelectedStoryboardVersionId("sv_story");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        versions.put("sv_video_1", videoVersion(workflow.getWorkflowId(), 1, "asset_video_1", "https://cdn.example.com/clip1.mp4", "https://cdn.example.com/video-last.png"));
        versions.put("sv_key_2", keyframeVersion(workflow.getWorkflowId(), 2, "asset_key_2", "https://cdn.example.com/clip2-last.png"));
        assets.put("asset_video_1", asset(workflow.getWorkflowId(), "asset_video_1", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/clip1.mp4", "video/mp4"));
        assets.put("asset_key_2", asset(workflow.getWorkflowId(), "asset_key_2", WorkflowConstants.STAGE_KEYFRAME, 2, "https://cdn.example.com/clip2-last.png", "image/png"));

        Map<String, Object> detail = service.getWorkflow("wf_detail_sync");

        List<Map<String, Object>> clipSlots = listValue(detail.get("clipSlots"));
        Map<String, Object> secondClip = clipSlots.stream()
            .filter(item -> intValue(item.get("clipIndex"), 0) == 2)
            .findFirst()
            .orElseThrow();
        Map<String, Object> keyframeVersion = listValue(secondClip.get("keyframeVersions")).get(0);
        Map<String, Object> outputSummary = mapValue(keyframeVersion.get("outputSummary"));
        assertEquals("https://cdn.example.com/video-last.png", outputSummary.get("firstFrameUrl"));
        assertEquals("https://cdn.example.com/video-last.png", outputSummary.get("startFrameUrl"));
        assertEquals(true, outputSummary.get("continuityResolvedFromCurrentSelection"));
    }

    @Test
    void generateStoryboardLogsFailureWhenTextModelCallThrows() {
        StageWorkflowEntity workflow = workflow("wf_story_fail");
        workflow.setSelectedStoryboardVersionId("");
        workflows.put(workflow.getWorkflowId(), workflow);
        when(generationApplicationService.createRun(any())).thenThrow(new IllegalStateException("text model response is empty"));

        IllegalStateException exception = assertThrows(IllegalStateException.class, () -> service.generateStoryboard("wf_story_fail"));

        assertEquals("text model response is empty", exception.getMessage());
        verify(workflowRepository, times(2)).saveSystemLog(
            org.mockito.ArgumentMatchers.eq("wf_story_fail"),
            org.mockito.ArgumentMatchers.eq("workflow"),
            org.mockito.ArgumentMatchers.eq(WorkflowConstants.STAGE_STORYBOARD),
            anyString(),
            anyString(),
            anyString(),
            any()
        );
        verify(workflowRepository).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_story_fail"), any());
    }

    @Test
    void generateStoryboardPersistsModelCallForDebugging() {
        StageWorkflowEntity workflow = workflow("wf_story_ok");
        workflow.setSelectedStoryboardVersionId("");
        workflows.put(workflow.getWorkflowId(), workflow);
        when(generationApplicationService.createRun(any())).thenReturn(scriptRun(
            "run_story_1",
            generatedStoryboardMarkdown(),
            "https://cdn.example.com/storyboard-v1.md"
        ));

        service.generateStoryboard("wf_story_ok");

        ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_story_ok"), captor.capture());
        Map<String, Object> modelCall = captor.getValue();
        assertEquals("script", modelCall.get("callKind"));
        assertEquals(WorkflowConstants.STAGE_STORYBOARD, modelCall.get("stage"));
        assertEquals("workflow.storyboard.generate", modelCall.get("operation"));
        assertEquals(true, modelCall.get("success"));
        assertEquals("qwen", modelCall.get("provider"));
        assertEquals("qwen3.6-plus", modelCall.get("requestedModel"));
        assertEquals("qwen3.6-plus", modelCall.get("providerModel"));
        assertEquals("run_story_1", modelCall.get("requestId"));
        assertFalse(mapValue(modelCall.get("requestPayload")).isEmpty());
        assertFalse(mapValue(modelCall.get("responsePayload")).isEmpty());
    }

    @Test
    void selectCharacterSheetKeepsWorkflowInKeyframeStage() {
        StageWorkflowEntity workflow = workflow("wf_select_sheet");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition("林舒", "鬓角垂落一缕碎发，身着素色针织开衫与深色长裤")
        ));
        versions.put("sv_sheet_1", characterSheetVersion(workflow.getWorkflowId(), 1001, "sv_story", "asset_sheet_1", "林舒", false));
        versions.put("sv_sheet_2", characterSheetVersion(workflow.getWorkflowId(), 1001, "sv_story", "asset_sheet_2", "林舒", true));
        assets.put("asset_sheet_1", asset(workflow.getWorkflowId(), "asset_sheet_1", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/character-sheet-1.png", "image/png"));
        assets.put("asset_sheet_2", asset(workflow.getWorkflowId(), "asset_sheet_2", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/character-sheet-2.png", "image/png"));

        Map<String, Object> detail = service.selectKeyframe("wf_select_sheet", 1001, "sv_sheet_2");

        assertEquals(WorkflowConstants.STAGE_KEYFRAME, workflows.get("wf_select_sheet").getCurrentStage());
        List<Map<String, Object>> characterSheets = listValue(detail.get("characterSheets"));
        List<Map<String, Object>> sheetVersions = listValue(characterSheets.get(0).get("versions"));
        assertTrue(sheetVersions.stream().anyMatch(item -> "sv_sheet_2".equals(item.get("id")) && Boolean.TRUE.equals(item.get("selected"))));
    }

    @Test
    void deleteWorkflowMarksWorkflowVersionsAndAssetsDeleted() {
        StageWorkflowEntity workflow = workflow("wf_delete");
        workflow.setFinalJoinAssetId("asset_join_delete");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story_delete", customStoryboardVersion(workflow.getWorkflowId(), "sv_story_delete", 1, true, storyboardClips()));
        versions.put("sv_key_delete", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_delete", 1, 1, "sv_story_delete", "asset_key_delete", true));
        versions.put("sv_video_delete", customVideoVersion(workflow.getWorkflowId(), "sv_video_delete", 1, 1, "sv_key_delete", "asset_video_delete", true));
        assets.put("asset_key_delete", asset(workflow.getWorkflowId(), "asset_key_delete", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-delete.png", "image/png"));
        assets.put("asset_video_delete", asset(workflow.getWorkflowId(), "asset_video_delete", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-delete.mp4", "video/mp4"));
        assets.put("asset_join_delete", asset(workflow.getWorkflowId(), "asset_join_delete", WorkflowConstants.STAGE_JOINED, 0, "https://cdn.example.com/join-delete.mp4", "video/mp4"));

        Map<String, Object> result = service.deleteWorkflow("wf_delete");

        assertEquals("wf_delete", result.get("workflowId"));
        assertEquals(true, result.get("deleted"));
        assertEquals(1, workflows.get("wf_delete").getIsDeleted());
        assertEquals(1, versions.get("sv_story_delete").getIsDeleted());
        assertEquals(1, versions.get("sv_key_delete").getIsDeleted());
        assertEquals(1, versions.get("sv_video_delete").getIsDeleted());
        assertEquals(1, assets.get("asset_key_delete").getIsDeleted());
        assertEquals(1, assets.get("asset_video_delete").getIsDeleted());
        assertEquals(1, assets.get("asset_join_delete").getIsDeleted());
    }

    @Test
    void deleteSelectedStoryboardFallsBackAndClearsDownstreamSelections() {
        StageWorkflowEntity workflow = workflow("wf_delete_storyboard");
        workflow.setSelectedStoryboardVersionId("sv_story_new");
        workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
        workflow.setStatus(WorkflowConstants.STATUS_COMPLETED);
        workflow.setFinalJoinAssetId("asset_join_storyboard");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story_old", customStoryboardVersion(workflow.getWorkflowId(), "sv_story_old", 1, false, storyboardClips()));
        versions.put("sv_story_new", customStoryboardVersion(workflow.getWorkflowId(), "sv_story_new", 2, true, storyboardClips()));
        versions.put("sv_key_old", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_old", 1, 1, "sv_story_old", "asset_key_old", false));
        versions.put("sv_key_new", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_new", 1, 2, "sv_story_new", "asset_key_new", true));
        versions.put("sv_video_old", customVideoVersion(workflow.getWorkflowId(), "sv_video_old", 1, 1, "sv_key_old", "asset_video_old", false));
        versions.put("sv_video_new", customVideoVersion(workflow.getWorkflowId(), "sv_video_new", 1, 2, "sv_key_new", "asset_video_new", true));
        assets.put("asset_key_old", asset(workflow.getWorkflowId(), "asset_key_old", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-old.png", "image/png"));
        assets.put("asset_key_new", asset(workflow.getWorkflowId(), "asset_key_new", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-new.png", "image/png"));
        assets.put("asset_video_old", asset(workflow.getWorkflowId(), "asset_video_old", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-old.mp4", "video/mp4"));
        assets.put("asset_video_new", asset(workflow.getWorkflowId(), "asset_video_new", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-new.mp4", "video/mp4"));
        assets.put("asset_join_storyboard", asset(workflow.getWorkflowId(), "asset_join_storyboard", WorkflowConstants.STAGE_JOINED, 0, "https://cdn.example.com/join-storyboard.mp4", "video/mp4"));

        Map<String, Object> detail = service.deleteStageVersion("wf_delete_storyboard", "sv_story_new");

        assertEquals("sv_story_old", workflows.get("wf_delete_storyboard").getSelectedStoryboardVersionId());
        assertEquals("", workflows.get("wf_delete_storyboard").getFinalJoinAssetId());
        assertEquals(WorkflowConstants.STAGE_KEYFRAME, workflows.get("wf_delete_storyboard").getCurrentStage());
        assertEquals(WorkflowConstants.STATUS_READY, workflows.get("wf_delete_storyboard").getStatus());
        assertEquals(1, versions.get("sv_story_new").getIsDeleted());
        assertEquals(1, versions.get("sv_key_new").getIsDeleted());
        assertEquals(1, versions.get("sv_video_new").getIsDeleted());
        assertEquals(0, versions.get("sv_key_old").getSelected());
        assertEquals(0, versions.get("sv_video_old").getSelected());
        assertEquals(0, assets.get("asset_join_storyboard").getSelectedForNext());
        assertEquals("sv_story_old", detail.get("selectedStoryboardVersionId"));
    }

    @Test
    void deleteSelectedKeyframePromotesRemainingKeyframeAndClearsClipVideos() {
        StageWorkflowEntity workflow = workflow("wf_delete_keyframe");
        workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
        workflow.setStatus(WorkflowConstants.STATUS_COMPLETED);
        workflow.setFinalJoinAssetId("asset_join_keyframe");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), List.of(storyboardClips().get(0))));
        versions.put("sv_key_1a", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_1a", 1, 1, "sv_story", "asset_key_1a", false));
        versions.put("sv_key_1b", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_1b", 1, 2, "sv_story", "asset_key_1b", true));
        versions.put("sv_video_1a", customVideoVersion(workflow.getWorkflowId(), "sv_video_1a", 1, 1, "sv_key_1a", "asset_video_1a", false));
        versions.put("sv_video_1b", customVideoVersion(workflow.getWorkflowId(), "sv_video_1b", 1, 2, "sv_key_1b", "asset_video_1b", true));
        assets.put("asset_key_1a", asset(workflow.getWorkflowId(), "asset_key_1a", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-1a.png", "image/png"));
        assets.put("asset_key_1b", asset(workflow.getWorkflowId(), "asset_key_1b", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-1b.png", "image/png"));
        assets.put("asset_video_1a", asset(workflow.getWorkflowId(), "asset_video_1a", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-1a.mp4", "video/mp4"));
        assets.put("asset_video_1b", asset(workflow.getWorkflowId(), "asset_video_1b", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-1b.mp4", "video/mp4"));
        assets.put("asset_join_keyframe", asset(workflow.getWorkflowId(), "asset_join_keyframe", WorkflowConstants.STAGE_JOINED, 0, "https://cdn.example.com/join-keyframe.mp4", "video/mp4"));

        service.deleteStageVersion("wf_delete_keyframe", "sv_key_1b");

        assertEquals(1, versions.get("sv_key_1a").getSelected());
        assertEquals(1, versions.get("sv_key_1b").getIsDeleted());
        assertEquals(1, versions.get("sv_video_1b").getIsDeleted());
        assertEquals(0, versions.get("sv_video_1a").getSelected());
        assertEquals("", workflows.get("wf_delete_keyframe").getFinalJoinAssetId());
        assertEquals(WorkflowConstants.STAGE_VIDEO, workflows.get("wf_delete_keyframe").getCurrentStage());
        assertEquals(WorkflowConstants.STATUS_READY, workflows.get("wf_delete_keyframe").getStatus());
    }

    private StageWorkflowEntity workflow(String workflowId) {
        StageWorkflowEntity workflow = new StageWorkflowEntity();
        workflow.setWorkflowId(workflowId);
        workflow.setOwnerUserId(USER_ID);
        workflow.setTitle("demo");
        workflow.setTranscriptText("");
        workflow.setGlobalPrompt("");
        workflow.setAspectRatio("9:16");
        workflow.setStylePreset("cinematic");
        workflow.setTextAnalysisModel("text-model");
        workflow.setVisionModel("vision-model");
        workflow.setImageModel("image-model");
        workflow.setVideoModel("video-model");
        workflow.setVideoSize("720*1280");
        workflow.setMinDurationSeconds(5);
        workflow.setMaxDurationSeconds(5);
        workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflow.setSelectedStoryboardVersionId(workflowId.equals("wf_2") ? "sv_story_2" : "sv_story");
        workflow.setFinalJoinAssetId("");
        workflow.setMetadataJson(WorkflowJsonSupport.write(Map.of()));
        workflow.setIsDeleted(0);
        return workflow;
    }

    private StageVersionEntity storyboardVersion(String workflowId, List<Map<String, Object>> clips) {
        return storyboardVersion(workflowId, clips, "");
    }

    private StageVersionEntity storyboardVersion(String workflowId, List<Map<String, Object>> clips, String scriptMarkdown) {
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId(workflowId.equals("wf_2") ? "sv_story_2" : "sv_story");
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(USER_ID);
        version.setStageType(WorkflowConstants.STAGE_STORYBOARD);
        version.setClipIndex(0);
        version.setVersionNo(1);
        version.setTitle("storyboard");
        version.setStatus("SUCCEEDED");
        version.setSelected(1);
        version.setMaterialAssetId("");
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "clips", clips,
            "clipCount", clips.size(),
            "scriptMarkdown", scriptMarkdown
        )));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setIsDeleted(0);
        return version;
    }

    private StageVersionEntity customStoryboardVersion(String workflowId, String versionId, int versionNo, boolean selected, List<Map<String, Object>> clips) {
        StageVersionEntity version = storyboardVersion(workflowId, clips);
        version.setStageVersionId(versionId);
        version.setVersionNo(versionNo);
        version.setSelected(selected ? 1 : 0);
        return version;
    }

    private StageVersionEntity characterSheetVersion(
        String workflowId,
        int clipIndex,
        String parentVersionId,
        String assetId,
        String characterName,
        boolean selected
    ) {
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId(selected ? "sv_sheet_2" : "sv_sheet_1");
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(USER_ID);
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(selected ? 2 : 1);
        version.setTitle(characterName + " 三视图 V" + (selected ? 2 : 1));
        version.setStatus("SUCCEEDED");
        version.setSelected(selected ? 1 : 0);
        version.setParentVersionId(parentVersionId);
        version.setMaterialAssetId(assetId);
        version.setDownloadUrl("https://cdn.example.com/" + assetId + ".png");
        version.setPreviewUrl("https://cdn.example.com/" + assetId + ".png");
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "variantKind", "character_sheet",
            "characterName", characterName
        )));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "variantKind", "character_sheet",
            "characterName", characterName,
            "sheetUrl", "https://cdn.example.com/" + assetId + ".png",
            "fileUrl", "https://cdn.example.com/" + assetId + ".png"
        )));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setIsDeleted(0);
        return version;
    }

    private StageVersionEntity keyframeVersion(String workflowId, int clipIndex, String assetId, String lastFrameUrl) {
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_key_" + clipIndex);
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(USER_ID);
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(1);
        version.setTitle("keyframe");
        version.setStatus("SUCCEEDED");
        version.setSelected(1);
        version.setParentVersionId(workflowId.equals("wf_2") ? "sv_story_2" : "sv_story");
        version.setMaterialAssetId(assetId);
        version.setDownloadUrl(lastFrameUrl);
        version.setPreviewUrl(lastFrameUrl);
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "firstFrameUrl", "https://cdn.example.com/inherited-start.png",
            "startFrameUrl", "https://cdn.example.com/inherited-start.png",
            "lastFrameUrl", lastFrameUrl,
            "endFrameUrl", lastFrameUrl,
            "fileUrl", lastFrameUrl
        )));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setIsDeleted(0);
        return version;
    }

    private StageVersionEntity customKeyframeVersion(
        String workflowId,
        String versionId,
        int clipIndex,
        int versionNo,
        String parentVersionId,
        String assetId,
        boolean selected
    ) {
        StageVersionEntity version = keyframeVersion(workflowId, clipIndex, assetId, "https://cdn.example.com/" + assetId + ".png");
        version.setStageVersionId(versionId);
        version.setVersionNo(versionNo);
        version.setParentVersionId(parentVersionId);
        version.setSelected(selected ? 1 : 0);
        version.setPreviewUrl("https://cdn.example.com/" + assetId + ".png");
        version.setDownloadUrl("https://cdn.example.com/" + assetId + ".png");
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "firstFrameUrl", "https://cdn.example.com/" + assetId + "-first.png",
            "startFrameUrl", "https://cdn.example.com/" + assetId + "-first.png",
            "lastFrameUrl", "https://cdn.example.com/" + assetId + ".png",
            "endFrameUrl", "https://cdn.example.com/" + assetId + ".png",
            "fileUrl", "https://cdn.example.com/" + assetId + ".png"
        )));
        return version;
    }

    private StageVersionEntity videoVersion(String workflowId, int clipIndex, String assetId, String fileUrl, String lastFrameUrl) {
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_video_" + clipIndex);
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(USER_ID);
        version.setStageType(WorkflowConstants.STAGE_VIDEO);
        version.setClipIndex(clipIndex);
        version.setVersionNo(1);
        version.setTitle("video");
        version.setStatus("SUCCEEDED");
        version.setSelected(1);
        version.setMaterialAssetId(assetId);
        version.setDownloadUrl(fileUrl);
        version.setPreviewUrl(fileUrl);
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "fileUrl", fileUrl,
            "firstFrameUrl", "https://cdn.example.com/video-first.png",
            "lastFrameUrl", lastFrameUrl
        )));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of()));
        version.setIsDeleted(0);
        return version;
    }

    private StageVersionEntity customVideoVersion(
        String workflowId,
        String versionId,
        int clipIndex,
        int versionNo,
        String parentVersionId,
        String assetId,
        boolean selected
    ) {
        StageVersionEntity version = videoVersion(
            workflowId,
            clipIndex,
            assetId,
            "https://cdn.example.com/" + assetId + ".mp4",
            "https://cdn.example.com/" + assetId + "-last.png"
        );
        version.setStageVersionId(versionId);
        version.setVersionNo(versionNo);
        version.setParentVersionId(parentVersionId);
        version.setSelected(selected ? 1 : 0);
        return version;
    }

    private MaterialAssetEntity asset(String workflowId, String assetId, String stageType, int clipIndex, String fileUrl, String mimeType) {
        MaterialAssetEntity asset = new MaterialAssetEntity();
        asset.setMaterialAssetId(assetId);
        asset.setOwnerUserId(USER_ID);
        asset.setWorkflowId(workflowId);
        asset.setStageType(stageType);
        asset.setAssetRole(stageType);
        asset.setClipIndex(clipIndex);
        asset.setVersionNo(1);
        asset.setMediaType(WorkflowConstants.STAGE_VIDEO.equals(stageType) ? "video" : "image");
        asset.setTitle(stageType + "-" + clipIndex);
        asset.setMimeType(mimeType);
        asset.setPublicUrl(fileUrl);
        asset.setRemoteUrl(fileUrl);
        asset.setMetadataJson(WorkflowJsonSupport.write(Map.of()));
        asset.setSelectedForNext(1);
        asset.setIsDeleted(0);
        return asset;
    }

    private List<Map<String, Object>> storyboardClips() {
        return List.of(
            new LinkedHashMap<>(Map.of(
                "clipIndex", 1,
                "shotLabel", "01",
                "scene", "图书馆门口",
                "firstFramePrompt", "镜头开场，角色推门进入废弃图书馆。",
                "lastFramePrompt", "角色停在门口，回望黑暗书架。",
                "motion", "镜头跟随推门动作后拉到人物半身",
                "cameraMovement", "push out",
                "durationHint", "5s",
                "imagePrompt", "镜头开场，角色推门进入废弃图书馆。",
                "videoPrompt", "角色停在门口，回望黑暗书架。"
            )),
            new LinkedHashMap<>(Map.of(
                "clipIndex", 2,
                "shotLabel", "02",
                "scene", "图书馆内部",
                "firstFramePrompt", "镜头承接门口定格，角色迈步进入书架之间。",
                "lastFramePrompt", "角色停在破旧书架前，抬头看见掉落尘埃。",
                "motion", "人物向前两步，镜头轻微平移",
                "cameraMovement", "slow pan",
                "durationHint", "5s",
                "imagePrompt", "",
                "videoPrompt", "角色停在破旧书架前，抬头看见掉落尘埃。"
            ))
        );
    }

    private String storyboardMarkdownWithCharacters() {
        return """
            【角色定义信息】
            - 林舒：女性，约28岁。外观锚点：鬓角垂落一缕碎发，身着素色针织开衫与深色长裤。行为特征：情绪内敛克制。
            - 周泽：男性，约29岁。外观锚点：穿着深灰休闲西装外套，内搭素色衬衫。行为特征：主动开口但声音干涩。

            【分镜脚本】
            | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
            | :--- | :--- | :--- | :--- | :--- |
            | 001 | 镜头开场，角色推门进入废弃图书馆。 | 角色停在门口，回望黑暗书架。 | 镜头跟随推门动作后拉到人物半身。 | 5s |
            """;
    }

    private String generatedStoryboardMarkdown() {
        return """
            【分镜脚本】
            | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
            | :--- | :--- | :--- | :--- | :--- |
            | 001 | 镜头开场，角色推门进入废弃图书馆。 | 角色停在门口，回望黑暗书架。 | 镜头跟随推门动作后拉到人物半身。 | 5s |
            """;
    }

    private Map<String, Object> imageRun(String runId, String fileUrl) {
        return imageRun(runId, fileUrl, fileUrl);
    }

    private Map<String, Object> imageRun(String runId, String fileUrl, String remoteSourceUrl) {
        return Map.of(
            "id", runId,
            "result", Map.of(
                "outputUrl", fileUrl,
                "mimeType", "image/png",
                "width", 720,
                "height", 1280,
                "modelInfo", Map.of("providerModel", "image-model"),
                "metadata", Map.of(
                    "fileUrl", fileUrl,
                    "remoteSourceUrl", remoteSourceUrl,
                    "taskId", runId + "_task"
                )
            )
        );
    }

    private Map<String, Object> scriptRun(String runId, String scriptMarkdown, String markdownUrl) {
        return Map.of(
            "id", runId,
            "kind", "script",
            "status", "succeeded",
            "result", Map.of(
                "scriptMarkdown", scriptMarkdown,
                "markdownUrl", markdownUrl,
                "mimeType", "text/markdown",
                "latencyMs", 321,
                "modelInfo", Map.of(
                    "provider", "qwen",
                    "providerModel", "qwen3.6-plus",
                    "requestedModel", "qwen3.6-plus",
                    "resolvedModel", "qwen3.6-plus",
                    "modelName", "qwen3.6-plus",
                    "endpointHost", "dashscope.aliyuncs.com"
                )
            )
        );
    }

    private Map<String, Object> videoRun(String runId, String fileUrl, String firstFrameUrl, String requestedLastFrameUrl, String lastFrameUrl) {
        return Map.of(
            "id", runId,
            "status", "succeeded",
            "result", Map.of(
                "outputUrl", fileUrl,
                "mimeType", "video/mp4",
                "durationSeconds", 5.0,
                "width", 720,
                "height", 1280,
                "hasAudio", true,
                "modelInfo", Map.of("providerModel", "video-model"),
                "metadata", Map.of(
                    "fileUrl", fileUrl,
                    "remoteSourceUrl", fileUrl,
                    "taskId", runId + "_task",
                    "firstFrameUrl", firstFrameUrl,
                    "requestedLastFrameUrl", requestedLastFrameUrl,
                    "lastFrameUrl", lastFrameUrl
                )
            )
        );
    }

    private StageVersionEntity findStageVersion(String workflowId, String versionId) {
        StageVersionEntity version = versions.get(versionId);
        if (version == null) {
            return null;
        }
        return workflowId.equals(version.getWorkflowId()) ? version : null;
    }

    private List<StageVersionEntity> listStageVersions(String workflowId) {
        return versions.values().stream()
            .filter(item -> workflowId.equals(item.getWorkflowId()))
            .filter(item -> intValue(item.getIsDeleted(), 0) == 0)
            .sorted(Comparator.comparing(StageVersionEntity::getStageType)
                .thenComparing(item -> item.getClipIndex() == null ? 0 : item.getClipIndex())
                .thenComparing(item -> item.getVersionNo() == null ? 0 : -item.getVersionNo()))
            .toList();
    }

    private int nextVersionNo(String workflowId, String stageType, int clipIndex) {
        return listStageVersions(workflowId).stream()
            .filter(item -> stageType.equals(item.getStageType()) && clipIndex == (item.getClipIndex() == null ? 0 : item.getClipIndex()))
            .map(item -> item.getVersionNo() == null ? 0 : item.getVersionNo())
            .max(Integer::compareTo)
            .orElse(0) + 1;
    }

    private Map<String, MaterialAssetEntity> findMaterialAssets(Collection<String> assetIds) {
        Map<String, MaterialAssetEntity> resolved = new LinkedHashMap<>();
        for (Object assetId : assetIds) {
            MaterialAssetEntity asset = assets.get(String.valueOf(assetId));
            if (asset != null && intValue(asset.getIsDeleted(), 0) == 0) {
                resolved.put(asset.getMaterialAssetId(), asset);
            }
        }
        return resolved;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listValue(Object value) {
        return value instanceof List<?> list ? (List<Map<String, Object>>) list : List.of();
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value));
            } catch (NumberFormatException ignored) {
            }
        }
        return fallback;
    }
}
