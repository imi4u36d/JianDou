package com.jiandou.api.workflow.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anySet;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.auth.security.CurrentUserPrincipal;
import com.jiandou.api.common.exception.ApiException;
import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.workflow.WorkflowConstants;
import com.jiandou.api.workflow.infrastructure.WorkflowJsonSupport;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import com.jiandou.api.workflow.web.dto.CreateMaterialGenerationRequest;
import com.jiandou.api.workflow.web.dto.SelectCharacterSheetAssetRequest;
import com.jiandou.api.workflow.web.dto.UpdateWorkflowSettingsRequest;
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
    private JiandouStorageProperties storageProperties;
    private ModelRuntimePropertiesResolver modelResolver;
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
        storageProperties = new JiandouStorageProperties();
        modelResolver = mock(ModelRuntimePropertiesResolver.class);
        service = new WorkflowApplicationService(
            workflowRepository,
            generationApplicationService,
            storyboardPlanner,
            localMediaArtifactService,
            storageProperties,
            modelResolver
        );

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
        when(modelResolver.supportsSeed(anyString())).thenReturn(true);
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
        when(workflowRepository.listMaterialAssetsPage(anyLong(), anyInt(), anyInt())).thenAnswer(invocation -> {
            int offset = invocation.getArgument(1);
            int limit = invocation.getArgument(2);
            List<MaterialAssetEntity> all = new ArrayList<>(assets.values());
            int fromIndex = Math.min(Math.max(0, offset), all.size());
            int toIndex = Math.min(fromIndex + Math.max(1, limit), all.size());
            return all.subList(fromIndex, toIndex);
        });
        when(workflowRepository.countMaterialAssets(anyLong())).thenAnswer(invocation -> (long) assets.values().stream()
            .filter(asset -> intValue(asset.getIsDeleted(), 0) == 0)
            .count());
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
    void createWorkflowUsesDefaultDurationRangeWhenAutomatic() {
        Map<String, Object> detail = service.createWorkflow(new com.jiandou.api.workflow.web.dto.CreateWorkflowRequest(
            "demo workflow",
            "正文",
            "9:16",
            "cinematic",
            "text-model",
            "image-model",
            "video-model",
            "720*1280",
            null,
            null,
            null,
            "auto",
            null,
            null
        ));

        StageWorkflowEntity created = workflows.get(detail.get("id"));
        assertNotNull(created);
        assertEquals("auto", created.getDurationMode());
        assertEquals(5, created.getMinDurationSeconds());
        assertEquals(12, created.getMaxDurationSeconds());
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
        assertNotNull(mapValue(requests.get(0).get("input")).get("seed"));
        assertEquals(mapValue(requests.get(0).get("input")).get("seed"), mapValue(requests.get(1).get("input")).get("seed"));
        assertEquals("https://cdn.example.com/clip1-first.png", mapValue(requests.get(1).get("input")).get("referenceImageUrl"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("必须严格沿用参考图已经确定的同一场景"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("尾帧只允许在参考首帧基础上推进人物动作状态"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("参考首帧描述：镜头开场，角色推门进入废弃图书馆。"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("场景锁定基准：镜头开场，角色推门进入废弃图书馆。"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("场景锚点：图书馆门口"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("尾帧目标：角色停在门口，回望黑暗书架。"));
        assertFalse(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("镜头过程："));

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
    void generateKeyframeKeepsSuccessfulFrameWhenOtherFrameFails() {
        StageWorkflowEntity workflow = workflow("wf_partial_keyframe");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_start_partial", "https://cdn.example.com/clip1-first-partial.png")
        ).thenThrow(new GenerationProviderException("tail provider timeout"));

        Map<String, Object> detail = service.generateKeyframe("wf_partial_keyframe", 1);

        verify(generationApplicationService, times(2)).createRun(any());
        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        assertEquals("PARTIAL", keyframeVersion.getStatus());
        assertEquals(0, keyframeVersion.getSelected());
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getOutputSummaryJson());
        assertEquals("https://cdn.example.com/clip1-first-partial.png", outputSummary.get("firstFrameUrl"));
        assertEquals("", outputSummary.get("lastFrameUrl"));
        assertEquals(1, listValue(outputSummary.get("generatedFrames")).size());
        List<Map<String, Object>> frameFailures = listValue(outputSummary.get("frameFailures"));
        assertEquals(1, frameFailures.size());
        assertEquals("last", frameFailures.get(0).get("frameRole"));
        assertTrue(String.valueOf(frameFailures.get(0).get("errorMessage")).contains("tail provider timeout"));

        List<Map<String, Object>> clipSlots = listValue(detail.get("clipSlots"));
        Map<String, Object> keyframeRow = listValue(clipSlots.get(0).get("keyframeVersions")).get(0);
        Map<String, Object> rowOutputSummary = mapValue(keyframeRow.get("outputSummary"));
        assertEquals("https://cdn.example.com/clip1-first-partial.png", rowOutputSummary.get("firstFrameUrl"));
        assertEquals(1, listValue(rowOutputSummary.get("frameFailures")).size());
    }

    @Test
    void generateKeyframeOmitsSeedWhenImageModelDoesNotSupportSeed() {
        StageWorkflowEntity workflow = workflow("wf_gpt_image_no_seed");
        workflow.setImageModel("gpt-image-2");
        workflow.setKeyframeSeed(12345);
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        when(modelResolver.supportsSeed("gpt-image-2")).thenReturn(false);
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_start_no_seed", "https://cdn.example.com/clip1-first-no-seed.png"),
            imageRun("run_end_no_seed", "https://cdn.example.com/clip1-last-no-seed.png")
        );

        service.generateKeyframe("wf_gpt_image_no_seed", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(2)).createRun(requestCaptor.capture());
        for (Map<String, Object> request : requestCaptor.getAllValues()) {
            assertFalse(mapValue(request.get("input")).containsKey("seed"));
        }
        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        Map<String, Object> inputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getInputSummaryJson());
        assertFalse(inputSummary.containsKey("seed"));
    }

    @Test
    void generateKeyframeUsesPublicUrlForBase64StartFrameReference() {
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        StageWorkflowEntity workflow = workflow("wf_base64_keyframe");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun(
                "run_start_base64",
                "/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png",
                "https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png"
            ),
            imageRun(
                "run_end_base64",
                "/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-last-v1.png",
                "https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-last-v1.png"
            )
        );

        service.generateKeyframe("wf_base64_keyframe", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(2)).createRun(requestCaptor.capture());
        Map<String, Object> tailInput = mapValue(requestCaptor.getAllValues().get(1).get("input"));
        assertEquals(
            "https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png",
            tailInput.get("referenceImageUrl")
        );
        assertEquals(
            List.of("https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png"),
            listValue(tailInput.get("referenceImageUrls"))
        );

        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getOutputSummaryJson());
        assertEquals("/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png", outputSummary.get("firstFrameUrl"));
        assertEquals(
            "https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-first-v1.png",
            outputSummary.get("firstFrameRemoteUrl")
        );
        assertEquals(
            "https://assets.example.com/storage/gen/workflows/wf_base64_keyframe/keyframes/clip1-last-v1.png",
            outputSummary.get("lastFrameRemoteUrl")
        );
    }

    @Test
    void generateKeyframeAllowsLocalGeneratedFramesWhenPublicBaseUrlMissing() {
        StageWorkflowEntity workflow = workflow("wf_local_keyframe");
        workflow.setImageModel("gpt-image-2");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/workflows/wf_local_keyframe/keyframes/clip1-first-v1.png"))
            .thenReturn("data:image/png;base64,Zmlyc3Q=");

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun(
                "run_start_local",
                "/storage/gen/workflows/wf_local_keyframe/keyframes/clip1-first-v1.png",
                ""
            ),
            imageRun(
                "run_end_local",
                "/storage/gen/workflows/wf_local_keyframe/keyframes/clip1-last-v1.png",
                ""
            )
        );

        service.generateKeyframe("wf_local_keyframe", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(2)).createRun(requestCaptor.capture());
        Map<String, Object> firstRequest = requestCaptor.getAllValues().get(0);
        Map<String, Object> tailInput = mapValue(requestCaptor.getAllValues().get(1).get("input"));
        assertFalse(Boolean.TRUE.equals(mapValue(firstRequest.get("storage")).get("requireRemoteSourceUrl")));
        assertEquals("data:image/png;base64,Zmlyc3Q=", tailInput.get("referenceImageUrl"));
        assertEquals(List.of("data:image/png;base64,Zmlyc3Q="), listValue(tailInput.get("referenceImageUrls")));

        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getOutputSummaryJson());
        assertEquals("/storage/gen/workflows/wf_local_keyframe/keyframes/clip1-first-v1.png", outputSummary.get("firstFrameRemoteUrl"));
        assertEquals("/storage/gen/workflows/wf_local_keyframe/keyframes/clip1-last-v1.png", outputSummary.get("lastFrameRemoteUrl"));
    }

    @Test
    void generateFirstClipCreatesMissingCharacterSheetsBeforeClipKeyframe() {
        StageWorkflowEntity workflow = workflow("wf_character");
        workflow.setGlobalPrompt("新海诚动漫风，空气透视明显，光影清透。");
        workflow.setImageModel("workflow-image-model");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(modelResolver.resolveMediaProfile("workflow-image-model", GenerationModelKinds.IMAGE, USER_ID)).thenReturn(mediaProfile(
            GenerationModelKinds.IMAGE,
            "workflow-image-model",
            "image-provider",
            "image-provider-upstream-model",
            true,
            true,
            ""
        ));
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
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("禁止半身像"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("双手空置"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("禁止手拿"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("不得出现任何文字"));
        assertTrue(String.valueOf(mapValue(requests.get(0).get("input")).get("prompt")).contains("背景必须是纯白色背景"));
        assertEquals(1824, mapValue(requests.get(0).get("input")).get("width"));
        assertEquals(1024, mapValue(requests.get(0).get("input")).get("height"));
        assertEquals(false, mapValue(requests.get(0).get("storage")).get("requireRemoteSourceUrl"));
        for (int requestIndex : List.of(0, 1)) {
            assertEquals("workflow-image-model", mapValue(requests.get(requestIndex).get("model")).get("providerModel"));
            assertStageStrategy(
                requests.get(requestIndex),
                WorkflowConstants.STAGE_KEYFRAME,
                "character_sheet.image-provider",
                "image-provider",
                "image-provider-upstream-model",
                true,
                true
            );
        }
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertTrue(String.valueOf(mapValue(requests.get(1).get("input")).get("prompt")).contains("三视图设定图"));
        assertNotNull(mapValue(requests.get(0).get("input")).get("seed"));
        assertNotNull(mapValue(requests.get(1).get("input")).get("seed"));
        assertTrue(String.valueOf(mapValue(requests.get(2).get("input")).get("prompt")).contains("全局画风要求：新海诚动漫风"));
        assertEquals("first", mapValue(requests.get(2).get("input")).get("frameRole"));
        for (int requestIndex : List.of(2, 3)) {
            assertEquals("workflow-image-model", mapValue(requests.get(requestIndex).get("model")).get("providerModel"));
            assertStageStrategy(
                requests.get(requestIndex),
                WorkflowConstants.STAGE_KEYFRAME,
                "keyframe.image-provider",
                "image-provider",
                "image-provider-upstream-model",
                true,
                true
            );
        }
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
        List<Map<String, Object>> firstCharacterSheetVersions = listValue(characterSheets.get(0).get("versions"));
        assertFalse(firstCharacterSheetVersions.isEmpty());
        assertEquals(
            mapValue(requests.get(0).get("input")).get("seed"),
            mapValue(firstCharacterSheetVersions.get(0).get("inputSummary")).get("seed")
        );
    }

    @Test
    void generateCharacterSheetSurfacesInvalidImagePayloadWithoutRetry() {
        StageWorkflowEntity workflow = workflow("wf_character_retry");
        workflow.setGlobalPrompt("少女漫画画风");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition(
                "苏浅",
                "黑色高马尾，白色翻领校服衬衫，同色系针织背心，格纹百褶短裙",
                "性别年龄：女性，约17岁；人物定位：被告白的女高中生；脸部五官：鹅蛋脸，眉眼弯弯，瞳仁明亮，鼻尖小巧，耳垂微红；发型：黑色高马尾，鬓角留有两缕碎发修饰脸型；体型身高：身高约160cm，身形娇小匀称，站姿轻盈；服装：白色翻领校服衬衫，外搭同色系针织背心，下身格纹百褶短裙；不可变视觉锚点：黑色高马尾、娇小匀称体型、白蓝配色校服套装"
            )
        ));
        when(generationApplicationService.createRun(any())).thenThrow(invalidImagePayloadException());

        GenerationProviderException exception = assertThrows(
            GenerationProviderException.class,
            () -> service.generateKeyframe("wf_character_retry", 1001)
        );
        assertTrue(exception.getMessage().contains("invalid image payload"));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(1)).createRun(requestCaptor.capture());
        String firstPrompt = String.valueOf(mapValue(requestCaptor.getAllValues().get(0).get("input")).get("prompt"));
        assertTrue(firstPrompt.contains("角色完整定义：性别年龄：女性"));

        ArgumentCaptor<Map<String, Object>> modelCallCaptor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(2)).saveModelCall(anyString(), modelCallCaptor.capture());
        Map<String, Object> modelCall = modelCallCaptor.getAllValues().get(1);
        assertEquals("workflow.character_sheet.generate", modelCall.get("operation"));
        assertEquals(false, modelCall.get("success"));
        assertEquals(502, modelCall.get("httpStatus"));
        assertTrue(listStageVersions(workflow.getWorkflowId()).stream()
            .noneMatch(item -> intValue(item.getClipIndex(), 0) == 1001));
    }

    private GenerationProviderException invalidImagePayloadException() {
        return new GenerationProviderException(
            "provider request failed: http 502 {\"error\":{\"message\":\"Upstream returned an invalid image payload\",\"type\":\"upstream_error\"}}",
            Map.of("body", Map.of("model", "gpt-5.4")),
            "{\"error\":{\"message\":\"Upstream returned an invalid image payload\",\"type\":\"upstream_error\"}}",
            502
        );
    }

    @Test
    void generateKeyframeForLaterClipCarriesCurrentStartFrameIntoContinuityPrompt() {
        StageWorkflowEntity workflow = workflow("wf_later_clip");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        versions.put("sv_key_1", keyframeVersion(workflow.getWorkflowId(), 1, "asset_key_1", "https://cdn.example.com/clip1-last-selected.png"));
        assets.put("asset_key_1", asset(workflow.getWorkflowId(), "asset_key_1", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/clip1-last-selected.png", "image/png"));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_end_clip2", "https://cdn.example.com/clip2-last.png")
        );

        service.generateKeyframe("wf_later_clip", 2);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(1)).createRun(requestCaptor.capture());
        Map<String, Object> request = requestCaptor.getValue();
        Map<String, Object> input = mapValue(request.get("input"));
        assertEquals("last", input.get("frameRole"));
        assertNotNull(input.get("seed"));
        assertEquals("https://cdn.example.com/clip1-last-selected.png", input.get("referenceImageUrl"));
        assertTrue(String.valueOf(input.get("prompt")).contains("参考首帧描述：角色停在门口，回望黑暗书架。"));
        assertTrue(String.valueOf(input.get("prompt")).contains("场景锚点：图书馆内部"));
        assertTrue(String.valueOf(input.get("prompt")).contains("尾帧目标：角色停在破旧书架前，抬头看见掉落尘埃。"));
        assertFalse(String.valueOf(input.get("prompt")).contains("镜头过程："));
    }

    @Test
    void generateKeyframeFallsBackSceneAnchorToStartFrameWhenSceneMissing() {
        StageWorkflowEntity workflow = workflow("wf_scene_fallback");
        workflows.put(workflow.getWorkflowId(), workflow);
        Map<String, Object> clip = new LinkedHashMap<>(storyboardClips().get(0));
        clip.put("scene", "");
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), List.of(clip)));

        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_start_scene", "https://cdn.example.com/scene-fallback-first.png"),
            imageRun("run_end_scene", "https://cdn.example.com/scene-fallback-last.png")
        );

        service.generateKeyframe("wf_scene_fallback", 1);

        StageVersionEntity keyframeVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .findFirst()
            .orElseThrow();
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(keyframeVersion.getOutputSummaryJson());
        Map<String, Object> normalizedClip = mapValue(outputSummary.get("clip"));
        assertEquals("镜头开场，角色推门进入废弃图书馆。", normalizedClip.get("scene"));
    }

    @Test
    void generateKeyframeMatchesCharacterFromClipMotionAndExposesItInClipSlot() {
        StageWorkflowEntity workflow = workflow("wf_character_match");
        workflows.put(workflow.getWorkflowId(), workflow);
        Map<String, Object> clip = new LinkedHashMap<>(Map.of(
            "clipIndex", 1,
            "shotLabel", "01",
            "scene", "咖啡馆靠窗座位",
            "firstFramePrompt", "女人坐在窗边，手里攥着已经凉掉的咖啡杯。",
            "lastFramePrompt", "她低下头，指尖摩挲杯沿，窗外雨痕映在玻璃上。",
            "motion", "周泽沉默地看着她，林舒把杯子推回桌面后移开视线。",
            "cameraMovement", "slow push",
            "durationHint", "5s",
            "imagePrompt", "女人坐在窗边，手里攥着已经凉掉的咖啡杯。",
            "videoPrompt", "周泽沉默地看着她，林舒把杯子推回桌面后移开视线。"
        ));
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), List.of(clip), storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition(
                "林舒",
                "鬓角垂落一缕碎发，身着素色针织开衫与深色长裤",
                "女性，约28岁。外观锚点：鬓角垂落一缕碎发，身着素色针织开衫与深色长裤。行为特征：情绪内敛克制。"
            ),
            new TaskStoryboardPlanner.CharacterDefinition(
                "周泽",
                "穿着深灰休闲西装外套，内搭素色衬衫",
                "男性，约29岁。外观锚点：穿着深灰休闲西装外套，内搭素色衬衫。行为特征：主动开口但声音干涩。"
            )
        ));
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_sheet_match_1", "/storage/workflows/wf_character_match/keyframes/character-sheet-1.png", "https://cdn.example.com/character-sheet-1-remote.png"),
            imageRun("run_sheet_match_2", "/storage/workflows/wf_character_match/keyframes/character-sheet-2.png", "https://cdn.example.com/character-sheet-2-remote.png"),
            imageRun("run_match_start", "/storage/workflows/wf_character_match/keyframes/match-first.png", "https://cdn.example.com/match-first-remote.png"),
            imageRun("run_match_end", "/storage/workflows/wf_character_match/keyframes/match-last.png", "https://cdn.example.com/match-last-remote.png")
        );

        Map<String, Object> detail = service.generateKeyframe("wf_character_match", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(4)).createRun(requestCaptor.capture());
        List<Map<String, Object>> requests = requestCaptor.getAllValues();
        String lastPrompt = String.valueOf(mapValue(requests.get(3).get("input")).get("prompt"));
        assertTrue(lastPrompt.contains("角色一致性绑定"));
        assertTrue(lastPrompt.contains("林舒：鬓角垂落一缕碎发"));
        assertTrue(lastPrompt.contains("周泽：穿着深灰休闲西装外套"));
        assertEquals(
            List.of(
                "https://cdn.example.com/match-first-remote.png",
                "https://cdn.example.com/character-sheet-1-remote.png",
                "https://cdn.example.com/character-sheet-2-remote.png"
            ),
            listValue(mapValue(requests.get(3).get("input")).get("referenceImageUrls"))
        );

        List<Map<String, Object>> clipSlots = listValue(detail.get("clipSlots"));
        Map<String, Object> clipSlot = clipSlots.get(0);
        List<Map<String, Object>> matchedCharacters = listValue(clipSlot.get("matchedCharacters"));
        assertEquals(2, matchedCharacters.size());
        assertEquals("林舒", matchedCharacters.get(0).get("characterName"));
        assertEquals("周泽", matchedCharacters.get(1).get("characterName"));
    }

    @Test
    void generateVideoPrefersPreviousSelectedVideoLastFrameUrl() {
        StageWorkflowEntity workflow = workflow("wf_2");
        workflow.setGlobalPrompt("新海诚动漫风，空气透视明显，光影清透。");
        workflow.setVideoModel("workflow-video-model");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story_2", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        versions.put("sv_video_1", videoVersion(workflow.getWorkflowId(), 1, "asset_video_1", "https://cdn.example.com/clip1.mp4", "https://cdn.example.com/video-last.png"));
        versions.put("sv_key_2", keyframeVersion(workflow.getWorkflowId(), 2, "asset_key_2", "https://cdn.example.com/clip2-last.png"));
        assets.put("asset_video_1", asset(workflow.getWorkflowId(), "asset_video_1", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/clip1.mp4", "video/mp4"));
        assets.put("asset_key_2", asset(workflow.getWorkflowId(), "asset_key_2", WorkflowConstants.STAGE_KEYFRAME, 2, "https://cdn.example.com/clip2-last.png", "image/png"));
        when(modelResolver.resolveMediaProfile("workflow-video-model", GenerationModelKinds.VIDEO, USER_ID)).thenReturn(mediaProfile(
            GenerationModelKinds.VIDEO,
            "workflow-video-model",
            "video-provider",
            "video-provider-upstream-model",
            false,
            false,
            "i2v"
        ));

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
        assertEquals("workflow-video-model", mapValue(requestCaptor.getValue().get("model")).get("providerModel"));
        assertStageStrategy(
            requestCaptor.getValue(),
            WorkflowConstants.STAGE_VIDEO,
            "video.video-provider",
            "video-provider",
            "video-provider-upstream-model",
            false,
            false
        );

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
    void generateVideoConvertsHistoricalLocalKeyframeUrlsToDataUri() {
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        StageWorkflowEntity workflow = workflow("wf_local_frames");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        StageVersionEntity keyframeVersion = keyframeVersion(
            workflow.getWorkflowId(),
            1,
            "asset_key_local",
            "/storage/gen/workflows/wf_local_frames/keyframes/clip1-last.png"
        );
        keyframeVersion.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "firstFrameUrl", "/storage/gen/workflows/wf_local_frames/keyframes/clip1-first.png",
            "startFrameUrl", "/storage/gen/workflows/wf_local_frames/keyframes/clip1-first.png",
            "lastFrameUrl", "/storage/gen/workflows/wf_local_frames/keyframes/clip1-last.png",
            "endFrameUrl", "/storage/gen/workflows/wf_local_frames/keyframes/clip1-last.png",
            "fileUrl", "/storage/gen/workflows/wf_local_frames/keyframes/clip1-last.png"
        )));
        versions.put(keyframeVersion.getStageVersionId(), keyframeVersion);
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/workflows/wf_local_frames/keyframes/clip1-first.png"))
            .thenReturn("data:image/png;base64,bG9jYWwtZmlyc3Q=");
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/workflows/wf_local_frames/keyframes/clip1-last.png"))
            .thenReturn("data:image/png;base64,bG9jYWwtbGFzdA==");

        when(generationApplicationService.createRun(any())).thenReturn(videoRun(
            "run_video_local_frames",
            "https://cdn.example.com/clip1.mp4",
            "data:image/png;base64,bG9jYWwtZmlyc3Q=",
            "data:image/png;base64,bG9jYWwtbGFzdA==",
            "https://cdn.example.com/clip1-generated-last.png"
        ));

        service.generateVideo("wf_local_frames", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("data:image/png;base64,bG9jYWwtZmlyc3Q=", input.get("firstFrameUrl"));
        assertEquals("data:image/png;base64,bG9jYWwtbGFzdA==", input.get("lastFrameUrl"));
    }

    @Test
    void generateVideoConvertsLocalKeyframeUrlsToDataUriWhenPublicBaseUrlIsMissing() {
        StageWorkflowEntity workflow = workflow("wf_local_data_uri_frames");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        StageVersionEntity keyframeVersion = keyframeVersion(
            workflow.getWorkflowId(),
            1,
            "asset_key_data_uri",
            "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-last.png"
        );
        keyframeVersion.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "firstFrameUrl", "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-first.png",
            "startFrameUrl", "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-first.png",
            "lastFrameUrl", "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-last.png",
            "endFrameUrl", "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-last.png",
            "fileUrl", "/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-last.png"
        )));
        versions.put(keyframeVersion.getStageVersionId(), keyframeVersion);
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-first.png"))
            .thenReturn("data:image/png;base64,Zmlyc3Q=");
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/workflows/wf_local_data_uri_frames/keyframes/clip1-last.png"))
            .thenReturn("data:image/png;base64,bGFzdA==");
        when(generationApplicationService.createRun(any())).thenReturn(videoRun(
            "run_video_data_uri_frames",
            "https://cdn.example.com/clip1.mp4",
            "data:image/png;base64,Zmlyc3Q=",
            "data:image/png;base64,bGFzdA==",
            "https://cdn.example.com/clip1-generated-last.png"
        ));

        service.generateVideo("wf_local_data_uri_frames", 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("data:image/png;base64,Zmlyc3Q=", input.get("firstFrameUrl"));
        assertEquals("data:image/png;base64,bGFzdA==", input.get("lastFrameUrl"));
    }

    @Test
    void generateVideoUpdatesSameModelCallWhenPollingEndsInFailure() {
        StageWorkflowEntity workflow = workflow("wf_video_fail");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips()));
        versions.put("sv_key_fail", keyframeVersion(workflow.getWorkflowId(), 1, "asset_key_fail", "https://cdn.example.com/clip1-last.png"));
        assets.put("asset_key_fail", asset(workflow.getWorkflowId(), "asset_key_fail", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/clip1-last.png", "image/png"));

        when(generationApplicationService.createRun(any())).thenReturn(videoSubmittedRun("run_video_fail"));
        when(generationApplicationService.getRun("run_video_fail")).thenReturn(videoFailedRun(
            "run_video_fail",
            "OutputVideoSensitiveContentDetected",
            "The request failed because the output video may contain sensitive information."
        ));

        assertThrows(RuntimeException.class, () -> service.generateVideo("wf_video_fail", 1));

        ArgumentCaptor<Map<String, Object>> modelCallCaptor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(3)).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_video_fail"), modelCallCaptor.capture());
        List<Map<String, Object>> modelCalls = modelCallCaptor.getAllValues();
        Map<String, Object> pendingModelCall = modelCalls.get(0);
        Map<String, Object> submittedModelCall = modelCalls.get(1);
        Map<String, Object> failedModelCall = modelCalls.get(2);

        assertEquals("pending", pendingModelCall.get("status"));
        assertEquals("mdlcall_", String.valueOf(pendingModelCall.get("modelCallId")).substring(0, 8));

        assertEquals(submittedModelCall.get("modelCallId"), failedModelCall.get("modelCallId"));
        assertEquals(true, submittedModelCall.get("success"));
        assertEquals("run_video_fail", submittedModelCall.get("requestId"));

        assertEquals(false, failedModelCall.get("success"));
        assertEquals("workflow.video.generate", failedModelCall.get("operation"));
        assertTrue(String.valueOf(failedModelCall.get("errorMessage")).contains("The request failed because the output video may contain sensitive information."));

        assertTrue(listStageVersions(workflow.getWorkflowId()).stream()
            .noneMatch(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == 1));
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
        when(generationApplicationService.createRun(any())).thenThrow(new GenerationProviderException(
            "text model response is empty",
            Map.of("method", "POST", "endpoint", "https://api.deepseek.com/v1/chat/completions", "body", Map.of("model", "deepseek-v4-flash")),
            Map.of("id", "resp_empty", "choices", List.of()),
            200
        ));

        GenerationProviderException exception = assertThrows(GenerationProviderException.class, () -> service.generateStoryboard("wf_story_fail"));

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
        ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(2)).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_story_fail"), captor.capture());
        Map<String, Object> modelCall = captor.getAllValues().get(1);
        Map<String, Object> responsePayload = mapValue(modelCall.get("responsePayload"));
        Map<String, Object> requestPayload = mapValue(modelCall.get("requestPayload"));
        assertEquals(200, modelCall.get("httpStatus"));
        assertEquals(200, responsePayload.get("httpStatus"));
        assertEquals("POST", requestPayload.get("method"));
        assertEquals("https://api.deepseek.com/v1/chat/completions", requestPayload.get("endpoint"));
        assertEquals("deepseek-v4-flash", mapValue(requestPayload.get("body")).get("model"));
        assertFalse(mapValue(requestPayload.get("businessRequest")).isEmpty());
        assertFalse(mapValue(responsePayload.get("providerRequest")).isEmpty());
        assertFalse(mapValue(responsePayload.get("providerResponse")).isEmpty());
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

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        assertOnlyTextAnalysisModel(requestCaptor.getValue(), "text-model");

        ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(2)).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_story_ok"), captor.capture());
        Map<String, Object> pendingModelCall = captor.getAllValues().get(0);
        Map<String, Object> modelCall = captor.getAllValues().get(1);
        assertEquals("pending", pendingModelCall.get("status"));
        assertEquals(true, mapValue(pendingModelCall.get("responsePayload")).isEmpty());
        assertEquals("script", modelCall.get("callKind"));
        assertEquals(WorkflowConstants.STAGE_STORYBOARD, modelCall.get("stage"));
        assertEquals("workflow.storyboard.generate", modelCall.get("operation"));
        assertEquals(true, modelCall.get("success"));
        assertEquals("deepseek", modelCall.get("provider"));
        assertEquals("deepseek-v4-pro", modelCall.get("requestedModel"));
        assertEquals("deepseek-v4-pro", modelCall.get("providerModel"));
        assertEquals("run_story_1", modelCall.get("requestId"));
        Map<String, Object> requestPayload = mapValue(modelCall.get("requestPayload"));
        assertEquals("https://api.deepseek.com/v1/chat/completions", requestPayload.get("endpoint"));
        assertFalse(mapValue(requestPayload.get("businessRequest")).isEmpty());
        assertFalse(mapValue(modelCall.get("responsePayload")).isEmpty());
        Map<String, Object> run = mapValue(mapValue(modelCall.get("responsePayload")).get("run"));
        Map<String, Object> metadata = mapValue(mapValue(run.get("result")).get("metadata"));
        assertFalse(listValue(metadata.get("providerInteractions")).isEmpty());
    }

    @Test
    void updateWorkflowSettingsPersistsStructuredColumns() {
        StageWorkflowEntity workflow = workflow("wf_settings");
        workflows.put(workflow.getWorkflowId(), workflow);

        Map<String, Object> detail = service.updateWorkflowSettings("wf_settings", new UpdateWorkflowSettingsRequest(
            "16:9",
            "noir",
            "text-model-next",
            "image-model-next",
            "video-model-next",
            "1280*720",
            1234,
            5678,
            "manual",
            6,
            9
        ));

        StageWorkflowEntity updated = workflows.get("wf_settings");
        assertEquals("16:9", updated.getAspectRatio());
        assertEquals("noir", updated.getStylePreset());
        assertEquals("text-model-next", updated.getTextAnalysisModel());
        assertEquals("image-model-next", updated.getImageModel());
        assertEquals("video-model-next", updated.getVideoModel());
        assertEquals("1280*720", updated.getVideoSize());
        assertEquals(1234, updated.getKeyframeSeed());
        assertEquals(5678, updated.getVideoSeed());
        assertEquals("manual", updated.getDurationMode());
        assertEquals(null, updated.getTaskSeed());
        assertEquals(6, updated.getMinDurationSeconds());
        assertEquals(9, updated.getMaxDurationSeconds());
        assertEquals("16:9", detail.get("aspectRatio"));
        assertEquals("manual", detail.get("durationMode"));
        assertEquals("video-model-next", detail.get("videoModel"));
        verify(workflowRepository).saveSystemLog(
            org.mockito.ArgumentMatchers.eq("wf_settings"),
            org.mockito.ArgumentMatchers.eq("workflow"),
            org.mockito.ArgumentMatchers.eq("settings"),
            org.mockito.ArgumentMatchers.eq("workflow.settings.updated"),
            org.mockito.ArgumentMatchers.eq("INFO"),
            org.mockito.ArgumentMatchers.eq("工作流设置已更新"),
            any()
        );
    }

    @Test
    void updateWorkflowSettingsKeepsAutomaticDurationMode() {
        StageWorkflowEntity workflow = workflow("wf_settings_auto");
        workflow.setDurationMode("manual");
        workflow.setMinDurationSeconds(6);
        workflow.setMaxDurationSeconds(9);
        workflows.put(workflow.getWorkflowId(), workflow);

        Map<String, Object> detail = service.updateWorkflowSettings("wf_settings_auto", new UpdateWorkflowSettingsRequest(
            "9:16",
            "cinematic",
            "text-model",
            "image-model",
            "video-model",
            "720*1280",
            null,
            null,
            "auto",
            null,
            null
        ));

        StageWorkflowEntity updated = workflows.get("wf_settings_auto");
        assertEquals("auto", updated.getDurationMode());
        assertEquals(5, updated.getMinDurationSeconds());
        assertEquals(12, updated.getMaxDurationSeconds());
        assertEquals("auto", detail.get("durationMode"));
    }

    @Test
    void adjustStoryboardCreatesNewVersionFromExistingMarkdown() {
        StageWorkflowEntity workflow = workflow("wf_story_adjust");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(generationApplicationService.createRun(any())).thenReturn(scriptRun(
            "run_story_adjust",
            "script_adjust",
            adjustedStoryboardMarkdown(),
            "https://cdn.example.com/storyboard-v2.md"
        ));

        Map<String, Object> detail = service.adjustStoryboard("wf_story_adjust", "sv_story", "加强角色三视图外观信息");

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> request = requestCaptor.getValue();
        assertEquals("script_adjust", request.get("kind"));
        Map<String, Object> input = mapValue(request.get("input"));
        assertEquals(storyboardMarkdownWithCharacters().trim(), String.valueOf(input.get("scriptMarkdown")).trim());
        assertEquals("加强角色三视图外观信息", input.get("adjustmentPrompt"));
        assertEquals("text-model", mapValue(request.get("model")).get("textAnalysisModel"));

        StageVersionEntity adjustedVersion = versions.values().stream()
            .filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType()))
            .filter(item -> intValue(item.getVersionNo(), 0) == 2)
            .findFirst()
            .orElseThrow();
        assertEquals("sv_story", adjustedVersion.getParentVersionId());
        assertEquals(0, intValue(adjustedVersion.getSelected(), 0));
        Map<String, Object> outputSummary = WorkflowJsonSupport.readMap(adjustedVersion.getOutputSummaryJson());
        assertEquals(adjustedStoryboardMarkdown().trim(), String.valueOf(outputSummary.get("scriptMarkdown")).trim());
        assertEquals("sv_story", outputSummary.get("sourceVersionId"));
        assertEquals("加强角色三视图外观信息", outputSummary.get("adjustmentPrompt"));
        assertEquals("sv_story", workflows.get("wf_story_adjust").getSelectedStoryboardVersionId());
        assertEquals(2, listValue(detail.get("storyboardVersions")).size());

        ArgumentCaptor<Map<String, Object>> modelCallCaptor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(2)).saveModelCall(org.mockito.ArgumentMatchers.eq("wf_story_adjust"), modelCallCaptor.capture());
        Map<String, Object> modelCall = modelCallCaptor.getAllValues().get(1);
        assertEquals("script_adjust", modelCall.get("callKind"));
        assertEquals("workflow.storyboard.adjust", modelCall.get("operation"));
        assertEquals("sv_story", mapValue(mapValue(modelCall.get("requestPayload")).get("context")).get("sourceVersionId"));
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
    void generateKeyframeUsesSelectedCharacterSheetAssetDescriptionAsCharacterConstraint() {
        StageWorkflowEntity workflow = workflow("wf_sheet_reference_prompt");
        workflow.setImageModel("image-model");
        workflows.put(workflow.getWorkflowId(), workflow);
        List<Map<String, Object>> clips = new ArrayList<>(storyboardClips());
        Map<String, Object> firstClip = new LinkedHashMap<>(clips.get(0));
        firstClip.put("firstFramePrompt", "林舒推门进入废弃图书馆。");
        firstClip.put("lastFramePrompt", "林舒停在门口，回望黑暗书架。");
        firstClip.put("imagePrompt", "林舒推门进入废弃图书馆。");
        clips.set(0, firstClip);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), clips, storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition("林舒", "旧外观：黑色长发，黑色吊带短裙", "旧外观：黑色长发，黑色吊带短裙")
        ));
        versions.put("sv_sheet_1", characterSheetVersion(workflow.getWorkflowId(), 1001, "sv_story", "asset_sheet_1", "林舒", false));
        versions.put("sv_sheet_2", characterSheetVersion(workflow.getWorkflowId(), 1001, "sv_story", "asset_sheet_2", "林舒", true));
        MaterialAssetEntity v1Asset = asset(workflow.getWorkflowId(), "asset_sheet_1", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/character-sheet-v1.png", "image/png");
        v1Asset.setMetadataJson(WorkflowJsonSupport.write(Map.of("description", "V1黑裙三视图")));
        MaterialAssetEntity v2Asset = asset(workflow.getWorkflowId(), "asset_sheet_2", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/character-sheet-v2.png", "image/png");
        v2Asset.setMetadataJson(WorkflowJsonSupport.write(Map.of("description", "V2银白长发，校园制服，黑色过膝袜")));
        assets.put("asset_sheet_1", v1Asset);
        assets.put("asset_sheet_2", v2Asset);
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_sheet_ref_start", "https://cdn.example.com/clip1-first.png"),
            imageRun("run_sheet_ref_last", "https://cdn.example.com/clip1-last.png")
        );

        service.generateKeyframe(workflow.getWorkflowId(), 1);

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService, times(2)).createRun(requestCaptor.capture());
        Map<String, Object> startInput = mapValue(requestCaptor.getAllValues().get(0).get("input"));
        String prompt = String.valueOf(startInput.get("prompt"));
        assertTrue(prompt.contains("V2银白长发，校园制服，黑色过膝袜"));
        assertFalse(prompt.contains("林舒：旧外观：黑色长发，黑色吊带短裙"));
        assertEquals("https://cdn.example.com/character-sheet-v2.png", startInput.get("referenceImageUrl"));
        assertEquals(List.of("https://cdn.example.com/character-sheet-v2.png"), listValue(startInput.get("referenceImageUrls")));
    }

    @Test
    void createMaterialGenerationStoresStandaloneAssetWithMetadata() {
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_scene", "https://cdn.example.com/material-scene.png", "https://remote.example.com/material-scene.png")
        );

        Map<String, Object> row = service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "scene",
            "雨夜街角",
            "湿润柏油路、霓虹招牌、窄巷纵深",
            List.of("cinematic", "rainy night"),
            List.of("https://cdn.example.com/ref.png"),
            List.of(),
            "16:9",
            "1280x720",
            "text-model",
            "image-model",
            1234
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("image", requestCaptor.getValue().get("kind"));
        assertEquals("scene", input.get("frameRole"));
        assertEquals("https://cdn.example.com/ref.png", input.get("referenceImageUrl"));
        assertTrue(String.valueOf(input.get("prompt")).contains("生成类型：场景概念图"));
        assertEquals("雨夜街角", row.get("title"));
        assertEquals("", row.get("workflowId"));
        assertEquals("material_center", row.get("stageType"));
        assertEquals("scene", row.get("assetType"));
        assertEquals(false, row.get("hasRemotePath"));
        assertEquals("", row.get("remotePath"));
        assertEquals("", row.get("remoteUrl"));
        Map<String, Object> metadata = mapValue(row.get("metadata"));
        assertEquals("湿润柏油路、霓虹招牌、窄巷纵深", metadata.get("description"));
        assertEquals("", metadata.get("remoteSourceUrl"));
        assertEquals(false, mapValue(requestCaptor.getValue().get("storage")).get("requireRemoteSourceUrl"));
    }

    @Test
    void uploadMaterialAssetMapsLocalStoragePathToRemotePath() {
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        MaterialAssetEntity asset = asset(
            "",
            "asset_material_scene",
            "material_center",
            0,
            "/storage/gen/material-center/scene/scene-1.png",
            "image/png"
        );
        asset.setRemoteUrl("");
        asset.setThirdPartyUrl("");
        asset.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "scene")));
        assets.put(asset.getMaterialAssetId(), asset);

        Map<String, Object> row = service.uploadMaterialAssetRemote("asset_material_scene");

        assertEquals("https://assets.example.com/storage/gen/material-center/scene/scene-1.png", row.get("remoteUrl"));
        assertEquals(true, row.get("hasRemotePath"));
        assertEquals("https://assets.example.com/storage/gen/material-center/scene/scene-1.png", row.get("remotePath"));
        assertEquals("https://assets.example.com/storage/gen/material-center/scene/scene-1.png", asset.getThirdPartyUrl());
        Map<String, Object> metadata = WorkflowJsonSupport.readMap(asset.getMetadataJson());
        assertEquals("https://assets.example.com/storage/gen/material-center/scene/scene-1.png", metadata.get("remoteSourceUrl"));
        assertNotNull(metadata.get("remoteUploadedAt"));
    }

    @Test
    void deleteMaterialAssetClearsSelectedFlag() {
        MaterialAssetEntity asset = asset(
            "",
            "asset_delete_scene",
            "material_center",
            0,
            "/storage/gen/material-center/scene/delete-me.png",
            "image/png"
        );
        assets.put(asset.getMaterialAssetId(), asset);

        Map<String, Object> result = service.deleteMaterialAsset("asset_delete_scene");

        assertEquals("asset_delete_scene", result.get("assetId"));
        assertEquals(true, result.get("deleted"));
        assertEquals(1, intValue(asset.getIsDeleted(), 0));
        assertEquals(0, intValue(asset.getSelectedForNext(), 0));
    }

    @Test
    void listMaterialAssetsClassifiesWorkflowGeneratedCharacterSheetsByVariantKind() {
        MaterialAssetEntity generatedSheet = asset(
            "wf_story",
            "asset_generated_suwan_sheet",
            WorkflowConstants.STAGE_KEYFRAME,
            1002,
            "https://cdn.example.com/suwan-sheet.png",
            "image/png"
        );
        generatedSheet.setTitle("操场偶遇 角色三视图 苏晚 V1");
        generatedSheet.setAssetRole(WorkflowConstants.STAGE_KEYFRAME);
        generatedSheet.setMetadataJson(WorkflowJsonSupport.write(Map.of(
            "variantKind", "character_sheet",
            "characterName", "苏晚",
            "sheetUrl", "https://cdn.example.com/suwan-sheet.png"
        )));
        assets.put(generatedSheet.getMaterialAssetId(), generatedSheet);

        List<Map<String, Object>> rows = service.listMaterialAssets("苏晚", null, null, null, null, null, "character_sheet");

        assertEquals(1, rows.size());
        assertEquals(generatedSheet.getMaterialAssetId(), rows.get(0).get("id"));
        assertEquals("character_sheet", rows.get(0).get("assetType"));
    }

    @Test
    void listMaterialAssetPageReturnsRequestedSliceAndNextOffset() {
        MaterialAssetEntity first = asset("", "asset_page_1", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/page-1.png", "image/png");
        MaterialAssetEntity second = asset("", "asset_page_2", WorkflowConstants.STAGE_KEYFRAME, 1002, "https://cdn.example.com/page-2.png", "image/png");
        MaterialAssetEntity third = asset("", "asset_page_3", WorkflowConstants.STAGE_KEYFRAME, 1003, "https://cdn.example.com/page-3.png", "image/png");
        first.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "scene")));
        second.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "scene")));
        third.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "scene")));
        assets.put(first.getMaterialAssetId(), first);
        assets.put(second.getMaterialAssetId(), second);
        assets.put(third.getMaterialAssetId(), third);

        Map<String, Object> page = service.listMaterialAssetPage(null, null, null, null, null, null, "scene", 1, 1);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) page.get("items");

        assertEquals(1, rows.size());
        assertEquals("asset_page_2", rows.get(0).get("id"));
        assertEquals(1, page.get("offset"));
        assertEquals(1, page.get("limit"));
        assertEquals(3L, page.get("total"));
        assertEquals(true, page.get("hasMore"));
        assertEquals(2, page.get("nextOffset"));
    }

    @Test
    void listMaterialAssetPageUsesRepositoryPageForUnfilteredQuery() {
        MaterialAssetEntity first = asset("", "asset_unfiltered_1", WorkflowConstants.STAGE_KEYFRAME, 1001, "https://cdn.example.com/unfiltered-1.png", "image/png");
        MaterialAssetEntity second = asset("", "asset_unfiltered_2", WorkflowConstants.STAGE_KEYFRAME, 1002, "https://cdn.example.com/unfiltered-2.png", "image/png");
        MaterialAssetEntity third = asset("", "asset_unfiltered_3", WorkflowConstants.STAGE_KEYFRAME, 1003, "https://cdn.example.com/unfiltered-3.png", "image/png");
        assets.put(first.getMaterialAssetId(), first);
        assets.put(second.getMaterialAssetId(), second);
        assets.put(third.getMaterialAssetId(), third);

        Map<String, Object> page = service.listMaterialAssetPage(null, null, null, null, null, null, null, 0, 2);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) page.get("items");

        assertEquals(List.of("asset_unfiltered_1", "asset_unfiltered_2"), rows.stream().map(row -> row.get("id")).toList());
        assertEquals(3L, page.get("total"));
        assertEquals(true, page.get("hasMore"));
        assertEquals(2, page.get("nextOffset"));
        verify(workflowRepository).listMaterialAssetsPage(USER_ID, 0, 2);
        verify(workflowRepository).countMaterialAssets(USER_ID);
    }

    @Test
    void listMaterialAssetsReturnsThumbnailUrlForMediaAssets() {
        MaterialAssetEntity image = asset("", "asset_thumb_image", WorkflowConstants.STAGE_KEYFRAME, 1001, "/storage/gen/images/source.png", "image/png");
        MaterialAssetEntity video = asset("", "asset_thumb_video", WorkflowConstants.STAGE_VIDEO, 1, "/storage/gen/video/source.mp4", "video/mp4");
        assets.put(image.getMaterialAssetId(), image);
        assets.put(video.getMaterialAssetId(), video);
        when(localMediaArtifactService.ensureMediaThumbnail("image", "/storage/gen/images/source.png", List.of(""), 480))
            .thenReturn("/storage/thumbs/gen/images/source-w480.jpg");
        when(localMediaArtifactService.ensureMediaThumbnail("video", "/storage/gen/video/source.mp4", List.of(""), 480))
            .thenReturn("/storage/thumbs/gen/video/source-video-w480.jpg");

        List<Map<String, Object>> rows = service.listMaterialAssets(null, null, null, null, null, null, null);
        Map<String, Object> imageRow = rows.stream()
            .filter(row -> "asset_thumb_image".equals(row.get("id")))
            .findFirst()
            .orElseThrow();
        Map<String, Object> videoRow = rows.stream()
            .filter(row -> "asset_thumb_video".equals(row.get("id")))
            .findFirst()
            .orElseThrow();

        assertEquals("/storage/thumbs/gen/images/source-w480.jpg", imageRow.get("thumbnailUrl"));
        assertEquals("/storage/thumbs/gen/video/source-video-w480.jpg", videoRow.get("thumbnailUrl"));
        verify(localMediaArtifactService).ensureMediaThumbnail("image", "/storage/gen/images/source.png", List.of(""), 480);
        verify(localMediaArtifactService).ensureMediaThumbnail("video", "/storage/gen/video/source.mp4", List.of(""), 480);
    }

    @Test
    void createMaterialGenerationMapsLocalStorageReferencesToPublicBaseUrl() {
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_prop", "https://cdn.example.com/material-prop.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "prop",
            "黄铜钥匙",
            "旧黄铜钥匙，边缘有磨损",
            List.of(),
            List.of("/storage/uploads/ref-key.png"),
            List.of(),
            "1:1",
            "1024x1024",
            "text-model",
            "gpt-image-2",
            null
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("https://assets.example.com/storage/uploads/ref-key.png", input.get("referenceImageUrl"));
        assertEquals(List.of("https://assets.example.com/storage/uploads/ref-key.png"), listValue(input.get("referenceImageUrls")));
    }

    @Test
    void createMaterialGenerationPassesDataUriReferencesThrough() {
        String dataUri = "data:image/png;base64,cmVm";
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_data_uri", "https://cdn.example.com/material-data-uri.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "prop",
            "黄铜钥匙",
            "旧黄铜钥匙，边缘有磨损",
            List.of(),
            List.of(dataUri),
            List.of(),
            "1:1",
            "1024x1024",
            "text-model",
            "gpt-image-2",
            null
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals(dataUri, input.get("referenceImageUrl"));
        assertEquals(List.of(dataUri), listValue(input.get("referenceImageUrls")));
    }

    @Test
    void createMaterialGenerationFailsWhenLocalReferenceHasNoPublicBaseUrlForNonDataUriModel() {
        ApiException ex = assertThrows(
            ApiException.class,
            () -> service.createMaterialGeneration(new CreateMaterialGenerationRequest(
                "prop",
                "黄铜钥匙",
                "旧黄铜钥匙，边缘有磨损",
                List.of(),
                List.of("/storage/uploads/ref-key.png"),
                List.of(),
                "1:1",
                "1024x1024",
                "text-model",
                "image-model",
                null
            ))
        );

        assertEquals("storage_public_base_url_missing", ex.code());
        assertTrue(ex.getMessage().contains("JIANDOU_STORAGE_PUBLIC_BASE_URL"));
    }

    @Test
    void createMaterialGenerationConvertsLocalLibraryReferenceToDataUriForGptImageModel() {
        MaterialAssetEntity referenceAsset = asset(
            "",
            "asset_ref_local",
            "material_center",
            0,
            "/storage/gen/material-center/ref.png",
            "image/png"
        );
        assets.put(referenceAsset.getMaterialAssetId(), referenceAsset);
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/material-center/ref.png"))
            .thenReturn("data:image/png;base64,cmVm");
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_gpt_ref", "https://cdn.example.com/material-gpt-ref.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "free",
            "参考图生成",
            "沿用参考图构图生成",
            List.of(),
            List.of(),
            List.of("asset_ref_local"),
            "1:1",
            "1024x1024",
            "gpt-5.4",
            "gpt-image-2",
            null
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("data:image/png;base64,cmVm", input.get("referenceImageUrl"));
        assertEquals(List.of("data:image/png;base64,cmVm"), listValue(input.get("referenceImageUrls")));
    }

    @Test
    void createMaterialGenerationConvertsLocalLibraryReferenceToDataUriForSeedreamModel() {
        when(modelResolver.resolveMediaProfile("Doubao-Seedream-4.5", GenerationModelKinds.IMAGE, USER_ID)).thenReturn(mediaProfile(
            GenerationModelKinds.IMAGE,
            "Doubao-Seedream-4.5",
            "seedream",
            "doubao-seedream-4-5-251128",
            true,
            true,
            ""
        ));
        MaterialAssetEntity referenceAsset = asset(
            "",
            "asset_ref_seedream_local",
            "material_center",
            0,
            "/storage/gen/material-center/seedream-ref.png",
            "image/png"
        );
        assets.put(referenceAsset.getMaterialAssetId(), referenceAsset);
        when(localMediaArtifactService.imageDataUriFromPublicUrl("/storage/gen/material-center/seedream-ref.png"))
            .thenReturn("data:image/png;base64,c2VlZHJlYW0=");
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_seedream_ref", "https://cdn.example.com/material-seedream-ref.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "free",
            "参考图生成",
            "沿用参考图构图生成",
            List.of(),
            List.of(),
            List.of("asset_ref_seedream_local"),
            "1:1",
            "1024x1024",
            "gpt-5.4",
            "Doubao-Seedream-4.5",
            null
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals("data:image/png;base64,c2VlZHJlYW0=", input.get("referenceImageUrl"));
        assertEquals(List.of("data:image/png;base64,c2VlZHJlYW0="), listValue(input.get("referenceImageUrls")));
    }

    @Test
    void createMaterialGenerationOmitsSeedWhenImageModelDoesNotSupportSeed() {
        when(modelResolver.supportsSeed("gpt-image-2")).thenReturn(false);
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_gpt_no_seed", "https://cdn.example.com/material-gpt-no-seed.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "free",
            "无 seed 生成",
            "一张白底产品照",
            List.of(),
            List.of(),
            List.of(),
            "1:1",
            "1024x1024",
            "gpt-5.4",
            "gpt-image-2",
            12345
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertFalse(input.containsKey("seed"));
    }

    @Test
    void createMaterialGenerationKeepsSeedWhenImageModelSupportsSeed() {
        when(modelResolver.supportsSeed("Doubao-Seedream-4.5")).thenReturn(true);
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_seedream_seed", "https://cdn.example.com/material-seedream-seed.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "free",
            "带 seed 生成",
            "一张白底产品照",
            List.of(),
            List.of(),
            List.of(),
            "1:1",
            "1024x1024",
            "gpt-5.4",
            "Doubao-Seedream-4.5",
            12345
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals(12345, input.get("seed"));
    }

    @Test
    void createMaterialGenerationFreeModeUsesPagePromptOnly() {
        when(generationApplicationService.createRun(any())).thenReturn(
            imageRun("run_material_free", "https://cdn.example.com/material-free.png", "")
        );

        service.createMaterialGeneration(new CreateMaterialGenerationRequest(
            "free",
            "自由生成",
            "一张白底产品照，透明玻璃香水瓶放在中央，柔和阴影，高级商业摄影。",
            List.of("cinematic"),
            List.of("https://cdn.example.com/ref.png"),
            List.of(),
            "9:16",
            "1024x1536",
            "text-model",
            "image-model",
            null
        ));

        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        String prompt = String.valueOf(input.get("prompt"));
        assertEquals("一张白底产品照，透明玻璃香水瓶放在中央，柔和阴影，高级商业摄影。", prompt);
        assertFalse(prompt.contains("素材标题"));
        assertFalse(prompt.contains("画风关键词"));
        assertFalse(prompt.contains("参考图要求"));
        assertFalse(prompt.contains("生成类型"));
        assertEquals(1024, input.get("width"));
        assertEquals(1536, input.get("height"));
        assertEquals("free", input.get("frameRole"));
        assertEquals(true, input.get("promptPassthrough"));
        assertEquals("https://cdn.example.com/ref.png", input.get("referenceImageUrl"));
    }

    @Test
    void createMaterialGenerationPersistsFailedModelCall() {
        when(generationApplicationService.createRun(any())).thenThrow(new GenerationProviderException(
            "provider request failed: http 502",
            Map.of("body", Map.of("model", "gpt-image-2", "size", "1024x1536")),
            "{\"error\":{\"message\":\"Upstream returned an invalid image payload\"}}",
            502
        ));

        GenerationProviderException ex = assertThrows(
            GenerationProviderException.class,
            () -> service.createMaterialGeneration(new CreateMaterialGenerationRequest(
                "character_sheet",
                "林舒",
                "17岁女生，短发，校服，身高165cm",
                List.of(),
                List.of(),
                List.of(),
                "9:16",
                "1280x720",
                "gpt-5.4",
                "gpt-image-2",
                null
            ))
        );

        assertTrue(ex.getMessage().contains("http 502"));
        ArgumentCaptor<Map<String, Object>> requestCaptor = ArgumentCaptor.forClass(Map.class);
        verify(generationApplicationService).createRun(requestCaptor.capture());
        Map<String, Object> input = mapValue(requestCaptor.getValue().get("input"));
        assertEquals(1280, input.get("width"));
        assertEquals(720, input.get("height"));
        ArgumentCaptor<Map<String, Object>> modelCallCaptor = ArgumentCaptor.forClass(Map.class);
        verify(workflowRepository, times(2)).saveModelCall(anyString(), modelCallCaptor.capture());
        Map<String, Object> modelCall = modelCallCaptor.getAllValues().get(1);
        assertEquals("material_center", modelCall.get("stage"));
        assertEquals("material_center.generate", modelCall.get("operation"));
        assertEquals(false, modelCall.get("success"));
        assertEquals(502, modelCall.get("httpStatus"));
        assertTrue(String.valueOf(modelCall.get("errorMessage")).contains("http 502"));
        assertEquals("gpt-image-2", modelCall.get("providerModel"));
        Map<String, Object> requestPayload = mapValue(modelCall.get("requestPayload"));
        assertEquals("gpt-image-2", mapValue(requestPayload.get("body")).get("model"));
        assertEquals("1024x1536", mapValue(requestPayload.get("body")).get("size"));
        assertFalse(mapValue(requestPayload.get("businessRequest")).isEmpty());
    }

    @Test
    void uploadMaterialAssetRemoteWritesConfiguredRemotePath() {
        storageProperties.setPublicBaseUrl("https://assets.example.com/storage");
        MaterialAssetEntity asset = asset("", "asset_local_scene", "material_center", 0, "/storage/gen/material-center/scene.png", "image/png");
        asset.setRemoteUrl("");
        asset.setThirdPartyUrl("");
        asset.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "scene")));
        assets.put(asset.getMaterialAssetId(), asset);

        Map<String, Object> row = service.uploadMaterialAssetRemote(asset.getMaterialAssetId());

        assertEquals(true, row.get("hasRemotePath"));
        assertEquals("https://assets.example.com/storage/gen/material-center/scene.png", row.get("remotePath"));
        assertEquals("https://assets.example.com/storage/gen/material-center/scene.png", asset.getRemoteUrl());
        assertEquals("https://assets.example.com/storage/gen/material-center/scene.png", asset.getThirdPartyUrl());
        assertEquals("https://assets.example.com/storage/gen/material-center/scene.png", mapValue(row.get("metadata")).get("remoteSourceUrl"));
    }

    @Test
    void uploadMaterialAssetRemoteRequiresPublicBaseUrl() {
        MaterialAssetEntity asset = asset("", "asset_local_no_base", "material_center", 0, "/storage/gen/material-center/prop.png", "image/png");
        asset.setRemoteUrl("");
        asset.setThirdPartyUrl("");
        assets.put(asset.getMaterialAssetId(), asset);

        ApiException ex = assertThrows(ApiException.class, () -> service.uploadMaterialAssetRemote(asset.getMaterialAssetId()));

        assertEquals("storage_public_base_url_missing", ex.code());
    }

    @Test
    void deleteMaterialAssetSoftDeletesAsset() {
        MaterialAssetEntity asset = asset("", "asset_delete_library", "material_center", 0, "/storage/gen/material-center/delete.png", "image/png");
        assets.put(asset.getMaterialAssetId(), asset);

        Map<String, Object> result = service.deleteMaterialAsset(asset.getMaterialAssetId());

        assertEquals("asset_delete_library", result.get("assetId"));
        assertEquals(true, result.get("deleted"));
        assertEquals(1, asset.getIsDeleted());
        assertEquals(0, asset.getSelectedForNext());
    }

    @Test
    void selectCharacterSheetAssetClonesLibraryAssetIntoWorkflowVersion() {
        StageWorkflowEntity workflow = workflow("wf_pick_sheet_asset");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story", storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters()));
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition("林舒", "鬓角碎发，素色针织开衫", "女性，外观锚点：鬓角碎发，素色针织开衫")
        ));
        MaterialAssetEntity libraryAsset = asset("", "asset_library_sheet", "material_center", 0, "https://cdn.example.com/library-sheet.png", "image/png");
        libraryAsset.setAssetRole("character_sheet");
        libraryAsset.setSelectedForNext(0);
        libraryAsset.setMetadataJson(WorkflowJsonSupport.write(Map.of(
            "assetType", "character_sheet",
            "description", "林舒三视图",
            "styleKeywords", List.of("clean")
        )));
        assets.put(libraryAsset.getMaterialAssetId(), libraryAsset);

        Map<String, Object> detail = service.selectCharacterSheetAsset(
            workflow.getWorkflowId(),
            1001,
            new SelectCharacterSheetAssetRequest(libraryAsset.getMaterialAssetId())
        );

        List<StageVersionEntity> sheetVersions = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> intValue(item.getClipIndex(), 0) == 1001)
            .toList();
        assertEquals(1, sheetVersions.size());
        StageVersionEntity version = sheetVersions.get(0);
        assertEquals(libraryAsset.getMaterialAssetId(), version.getSourceMaterialAssetId());
        assertEquals(libraryAsset.getMaterialAssetId(), version.getMaterialAssetId());
        assertEquals(1, version.getSelected());
        assertEquals("character_sheet", mapValue(WorkflowJsonSupport.readMap(version.getOutputSummaryJson())).get("variantKind"));
        assertEquals(0, libraryAsset.getSelectedForNext());
        List<Map<String, Object>> characterSheets = listValue(detail.get("characterSheets"));
        assertFalse(listValue(characterSheets.get(0).get("versions")).isEmpty());
    }

    @Test
    void deleteSelectedCharacterSheetVersionFromLibraryDoesNotDeleteSourceAsset() {
        StageWorkflowEntity workflow = workflow("wf_delete_library_character_sheet");
        workflows.put(workflow.getWorkflowId(), workflow);
        StageVersionEntity storyboard = storyboardVersion(workflow.getWorkflowId(), storyboardClips(), storyboardMarkdownWithCharacters());
        versions.put(storyboard.getStageVersionId(), storyboard);
        workflow.setSelectedStoryboardVersionId(storyboard.getStageVersionId());
        when(storyboardPlanner.extractCharacterDefinitions(anyString())).thenReturn(List.of(
            new TaskStoryboardPlanner.CharacterDefinition("林舒", "鬓角碎发，素色针织开衫", "女性，外观锚点：鬓角碎发，素色针织开衫")
        ));
        MaterialAssetEntity libraryAsset = asset("", "asset_library_sheet_delete", "material_center", 0, "https://cdn.example.com/library-sheet-delete.png", "image/png");
        libraryAsset.setAssetRole("character_sheet");
        libraryAsset.setMetadataJson(WorkflowJsonSupport.write(Map.of("assetType", "character_sheet")));
        assets.put(libraryAsset.getMaterialAssetId(), libraryAsset);

        service.selectCharacterSheetAsset(
            workflow.getWorkflowId(),
            1001,
            new SelectCharacterSheetAssetRequest(libraryAsset.getMaterialAssetId())
        );
        StageVersionEntity selectedVersion = listStageVersions(workflow.getWorkflowId()).stream()
            .filter(item -> intValue(item.getClipIndex(), 0) == 1001)
            .findFirst()
            .orElseThrow();

        service.deleteStageVersion(workflow.getWorkflowId(), selectedVersion.getStageVersionId());

        MaterialAssetEntity reloadedAsset = assets.get(libraryAsset.getMaterialAssetId());
        assertNotNull(reloadedAsset);
        assertEquals(0, intValue(reloadedAsset.getIsDeleted(), 0));
        assertEquals(0, intValue(reloadedAsset.getSelectedForNext(), 0));
    }

    @Test
    void selectStoryboardHidesKeyframesAndVideosFromPreviousStoryboardVersion() {
        StageWorkflowEntity workflow = workflow("wf_select_storyboard");
        workflow.setSelectedStoryboardVersionId("sv_story_old");
        workflows.put(workflow.getWorkflowId(), workflow);
        versions.put("sv_story_old", customStoryboardVersion(workflow.getWorkflowId(), "sv_story_old", 1, true, storyboardClips()));
        versions.put("sv_story_new", customStoryboardVersion(workflow.getWorkflowId(), "sv_story_new", 2, false, storyboardClips()));
        versions.put("sv_key_old", customKeyframeVersion(workflow.getWorkflowId(), "sv_key_old", 1, 1, "sv_story_old", "asset_key_old", true));
        versions.put("sv_video_old", customVideoVersion(workflow.getWorkflowId(), "sv_video_old", 1, 1, "sv_key_old", "asset_video_old", true));
        assets.put("asset_key_old", asset(workflow.getWorkflowId(), "asset_key_old", WorkflowConstants.STAGE_KEYFRAME, 1, "https://cdn.example.com/key-old.png", "image/png"));
        assets.put("asset_video_old", asset(workflow.getWorkflowId(), "asset_video_old", WorkflowConstants.STAGE_VIDEO, 1, "https://cdn.example.com/video-old.mp4", "video/mp4"));

        Map<String, Object> detail = service.selectStoryboard("wf_select_storyboard", "sv_story_new");

        assertEquals("sv_story_new", detail.get("selectedStoryboardVersionId"));
        List<Map<String, Object>> clipSlots = listValue(detail.get("clipSlots"));
        assertFalse(clipSlots.isEmpty());
        assertTrue(listValue(clipSlots.get(0).get("keyframeVersions")).isEmpty());
        assertTrue(listValue(clipSlots.get(0).get("videoVersions")).isEmpty());
        assertEquals(0, versions.get("sv_key_old").getSelected());
        assertEquals(0, versions.get("sv_video_old").getSelected());
        assertEquals(0, versions.get("sv_key_old").getIsDeleted());
        assertEquals(0, versions.get("sv_video_old").getIsDeleted());
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
        workflow.setImageModel("image-model");
        workflow.setVideoModel("video-model");
        workflow.setVideoSize("720*1280");
        workflow.setDurationMode("auto");
        workflow.setMinDurationSeconds(5);
        workflow.setMaxDurationSeconds(12);
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
                "firstFramePrompt", "角色停在门口，回望黑暗书架。",
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

    private String adjustedStoryboardMarkdown() {
        return """
            【角色定义信息】
            | 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 林舒 | 女性，约28岁 | 被旧案牵引进图书馆的调查者 | 杏眼，鼻梁挺直，唇形偏薄 | 黑色低马尾，鬓角一缕碎发 | 中等身高，肩背偏瘦 | 素色针织开衫，深色长裤 | 细框眼镜 | 鬓角碎发、细框眼镜、素色针织开衫、深色长裤 | 克制谨慎 | 低声短句 |

            【分镜脚本】
            | 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
            | :--- | :--- | :--- | :--- | :--- |
            | 001 | 林舒（鬓角碎发、细框眼镜、素色针织开衫、深色长裤）站在废弃图书馆门口，画面左侧是半开的木门，右侧是落灰书架。 | 林舒（鬓角碎发、细框眼镜、素色针织开衫、深色长裤）仍站在同一扇半开木门旁，转头望向右侧落灰书架。 | 林舒推开木门后停住，先观察门内过道，再转头看向右侧书架。 | 5s |
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
        return scriptRun(runId, "script", scriptMarkdown, markdownUrl);
    }

    private Map<String, Object> scriptRun(String runId, String kind, String scriptMarkdown, String markdownUrl) {
        return Map.of(
            "id", runId,
            "kind", kind,
            "status", "succeeded",
            "result", Map.of(
                "scriptMarkdown", scriptMarkdown,
                "markdownUrl", markdownUrl,
                "mimeType", "text/markdown",
                "latencyMs", 321,
                "metadata", Map.of(
                    "providerRequest", Map.of("endpoint", "https://api.deepseek.com/v1/chat/completions"),
                    "providerResponse", Map.of("id", "resp_story_1"),
                    "providerHttpStatus", 200,
                    "providerInteractions", List.of(
                        Map.of(
                            "step", "draft",
                            "providerRequest", Map.of("endpoint", "https://api.deepseek.com/v1/chat/completions"),
                            "providerResponse", Map.of("id", "resp_story_1"),
                            "httpStatus", 200
                        )
                    )
                ),
                "modelInfo", Map.of(
                    "provider", "deepseek",
                    "providerModel", "deepseek-v4-pro",
                    "requestedModel", "deepseek-v4-pro",
                    "resolvedModel", "deepseek-v4-pro",
                    "modelName", "deepseek-v4-pro",
                    "endpointHost", "api.deepseek.com"
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

    private Map<String, Object> videoSubmittedRun(String runId) {
        return Map.of(
            "id", runId,
            "status", "running",
            "result", Map.of(
                "outputUrl", "",
                "mimeType", "video/mp4",
                "modelInfo", Map.of("providerModel", "video-model"),
                "metadata", Map.of(
                    "taskId", runId + "_task",
                    "taskStatus", "SUBMITTED",
                    "outputUrl", "",
                    "remoteSourceUrl", ""
                )
            )
        );
    }

    private Map<String, Object> videoFailedRun(String runId, String errorCode, String errorMessage) {
        return Map.of(
            "id", runId,
            "status", "failed",
            "result", Map.of(
                "outputUrl", "",
                "error", errorMessage,
                "mimeType", "video/mp4",
                "modelInfo", Map.of("providerModel", "video-model"),
                "metadata", Map.of(
                    "taskId", runId + "_task",
                    "taskStatus", "FAILED",
                    "outputUrl", "",
                    "remoteSourceUrl", "",
                    "providerPayload", Map.of(
                        "error", Map.of(
                            "code", errorCode,
                            "message", errorMessage
                        )
                    )
                )
            )
        );
    }

    private MediaProviderProfile mediaProfile(
        String kind,
        String requestedModel,
        String provider,
        String providerModel,
        boolean supportsSeed,
        boolean supportsImageDataUriReferences,
        String generationMode
    ) {
        return new MediaProviderProfile(
            new MediaProviderConfig(
                kind,
                requestedModel,
                provider,
                providerModel,
                "api-key",
                "https://api.example.com",
                "https://task.example.com",
                30,
                "test"
            ),
            new MediaProviderCapabilities(
                supportsSeed,
                false,
                false,
                false,
                5,
                120,
                generationMode,
                List.of(),
                List.of(),
                supportsImageDataUriReferences
            )
        );
    }

    private void assertOnlyTextAnalysisModel(Map<String, Object> request, String expectedTextAnalysisModel) {
        Map<String, Object> model = mapValue(request.get("model"));
        assertEquals(expectedTextAnalysisModel, model.get("textAnalysisModel"));
        assertEquals(1, model.size());
        assertFalse(model.containsKey("providerModel"));
        assertFalse(model.containsKey("imageModel"));
        assertFalse(model.containsKey("videoModel"));
    }

    private void assertStageStrategy(
        Map<String, Object> request,
        String expectedStage,
        String expectedKey,
        String expectedProvider,
        String expectedProviderModel,
        boolean expectedSupportsSeed,
        boolean expectedSupportsImageDataUriReferences
    ) {
        Map<String, Object> stageStrategy = mapValue(mapValue(request.get("metadata")).get("stageStrategy"));
        assertEquals(expectedStage, stageStrategy.get("stage"));
        assertEquals(expectedKey, stageStrategy.get("key"));
        assertEquals(expectedProvider, stageStrategy.get("provider"));
        assertEquals(expectedProviderModel, stageStrategy.get("providerModel"));
        assertEquals(expectedSupportsSeed, stageStrategy.get("supportsSeed"));
        assertEquals(expectedSupportsImageDataUriReferences, stageStrategy.get("supportsImageDataUriReferences"));
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
