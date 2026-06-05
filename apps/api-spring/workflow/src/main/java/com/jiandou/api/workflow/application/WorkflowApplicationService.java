package com.jiandou.api.workflow.application;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.auth.security.SecurityCurrentUser;
import com.jiandou.api.common.exception.ApiException;
import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.config.JiandouStorageProperties;
import com.jiandou.api.generation.GenerationRunStatuses;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.media.MaterialAssetThumbnailService;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.workflow.WorkflowConstants;
import com.jiandou.api.workflow.infrastructure.WorkflowJsonSupport;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import com.jiandou.api.workflow.web.dto.CreateMaterialGenerationRequest;
import com.jiandou.api.workflow.web.dto.CreateWorkflowRequest;
import com.jiandou.api.workflow.web.dto.RateStageVersionRequest;
import com.jiandou.api.workflow.web.dto.RateWorkflowRequest;
import com.jiandou.api.workflow.web.dto.ReuseMaterialRequest;
import com.jiandou.api.workflow.web.dto.SelectCharacterSheetAssetRequest;
import com.jiandou.api.workflow.web.dto.UpdateMaterialAssetRatingRequest;
import com.jiandou.api.workflow.web.dto.UpdateWorkflowSettingsRequest;
import com.jiandou.api.workflow.web.dto.WorkflowSummaryResponse;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class WorkflowApplicationService {

    private static final long VIDEO_RUN_POLL_INTERVAL_MILLIS = 1000L;
    private static final int VIDEO_RUN_MAX_POLLS = 240;
    private static final int CHARACTER_SHEET_CLIP_INDEX_BASE = 1000;
    private static final int DEFAULT_WORKFLOW_MIN_DURATION_SECONDS = 5;
    private static final int DEFAULT_WORKFLOW_MAX_DURATION_SECONDS = 12;
    private static final int MATERIAL_ASSET_PAGE_DEFAULT_LIMIT = 30;
    private static final int MATERIAL_ASSET_PAGE_MAX_LIMIT = 80;
    private static final String VARIANT_KIND_CHARACTER_SHEET = "character_sheet";

    private final WorkflowRepository workflowRepository;
    private final GenerationApplicationService generationApplicationService;
    private final TaskStoryboardPlanner storyboardPlanner;
    private final LocalMediaArtifactService localMediaArtifactService;
    private final MaterialAssetThumbnailService materialAssetThumbnailService;
    private final JiandouStorageProperties storageProperties;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final WorkflowStageGenerationStrategyResolver stageStrategyResolver;

    public WorkflowApplicationService(
        WorkflowRepository workflowRepository,
        GenerationApplicationService generationApplicationService,
        TaskStoryboardPlanner storyboardPlanner,
        LocalMediaArtifactService localMediaArtifactService,
        JiandouStorageProperties storageProperties,
        ModelRuntimePropertiesResolver modelResolver
    ) {
        this.workflowRepository = workflowRepository;
        this.generationApplicationService = generationApplicationService;
        this.storyboardPlanner = storyboardPlanner;
        this.localMediaArtifactService = localMediaArtifactService;
        this.materialAssetThumbnailService = new MaterialAssetThumbnailService(localMediaArtifactService);
        this.storageProperties = storageProperties;
        this.modelResolver = modelResolver;
        this.stageStrategyResolver = new WorkflowStageGenerationStrategyResolver(modelResolver);
    }

    public Map<String, Object> createWorkflow(CreateWorkflowRequest request) {
        Long ownerUserId = requiredUserId();
        validateCreateWorkflowRequest(request);
        StageWorkflowEntity workflow = new StageWorkflowEntity();
        workflow.setWorkflowId("wf_" + randomId());
        workflow.setOwnerUserId(ownerUserId);
        workflow.setTitle(trimmed(request.title(), "未命名工作流"));
        workflow.setTranscriptText(trimmed(request.transcriptText(), ""));
        workflow.setAspectRatio(trimmed(request.aspectRatio(), "9:16"));
        workflow.setStylePreset(trimmed(request.stylePreset(), "cinematic"));
        workflow.setTextAnalysisModel(trimmed(request.textAnalysisModel(), ""));
        workflow.setImageModel(trimmed(request.imageModel(), ""));
        workflow.setVideoModel(trimmed(request.videoModel(), ""));
        workflow.setVideoSize(trimmed(request.videoSize(), defaultVideoSize(workflow.getAspectRatio())));
        Integer keyframeSeed = request.keyframeSeed() != null ? request.keyframeSeed() : request.seed();
        Integer videoSeed = request.videoSeed() != null ? request.videoSeed() : request.seed();
        workflow.setTaskSeed(resolvedSharedSeed(keyframeSeed, videoSeed, request.seed()));
        workflow.setKeyframeSeed(keyframeSeed);
        workflow.setVideoSeed(videoSeed);
        String durationMode = normalizeDurationMode(request.durationMode(), request.minDurationSeconds(), request.maxDurationSeconds());
        workflow.setDurationMode(durationMode);
        int minDurationSeconds = "auto".equals(durationMode) ? DEFAULT_WORKFLOW_MIN_DURATION_SECONDS : Math.max(1, request.minDurationSeconds());
        int maxDurationSeconds = "auto".equals(durationMode) ? DEFAULT_WORKFLOW_MAX_DURATION_SECONDS : Math.max(request.maxDurationSeconds(), minDurationSeconds);
        workflow.setMinDurationSeconds(minDurationSeconds);
        workflow.setMaxDurationSeconds(maxDurationSeconds);
        workflow.setStatus(WorkflowConstants.STATUS_DRAFT);
        workflow.setCurrentStage(WorkflowConstants.STAGE_STORYBOARD);
        workflow.setSelectedStoryboardVersionId("");
        workflow.setFinalJoinAssetId("");
        workflow.setEffectRating(null);
        workflow.setEffectRatingNote("");
        workflow.setRatedAt(null);
        workflow.setMetadataJson(WorkflowJsonSupport.write(Map.of()));
        workflow.setIsDeleted(0);
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflow.getWorkflowId());
    }

    public List<WorkflowSummaryResponse> listWorkflows() {
        Long ownerUserId = requiredUserId();
        List<StageWorkflowEntity> workflows = workflowRepository.listWorkflows(ownerUserId);
        Map<String, List<StageVersionEntity>> versionMap = new LinkedHashMap<>();
        for (StageWorkflowEntity workflow : workflows) {
            versionMap.put(workflow.getWorkflowId(), workflowRepository.listStageVersions(workflow.getWorkflowId()));
        }
        return workflows.stream().map(workflow -> toWorkflowSummaryResponse(workflow, versionMap.getOrDefault(workflow.getWorkflowId(), List.of()))).toList();
    }

    public Map<String, Object> getWorkflow(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId);
        Map<String, MaterialAssetEntity> assetMap = loadAssetMap(versions, workflow.getFinalJoinAssetId(), workflow.getOwnerUserId());
        return toWorkflowDetail(workflow, versions, assetMap);
    }

    public Map<String, Object> deleteWorkflow(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId);
        Set<String> assetIds = new LinkedHashSet<>();
        for (StageVersionEntity version : versions) {
            if (!isBlank(version.getMaterialAssetId())) {
                assetIds.add(version.getMaterialAssetId());
            }
            markStageVersionDeleted(version);
        }
        if (!isBlank(workflow.getFinalJoinAssetId())) {
            assetIds.add(workflow.getFinalJoinAssetId());
        }
        for (String assetId : assetIds) {
            markMaterialAssetDeleted(assetId);
        }
        workflow.setIsDeleted(1);
        workflow.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveWorkflow(workflow);
        return Map.of(
            "workflowId", workflowId,
            "deleted", true
        );
    }

    public Map<String, Object> updateWorkflowSettings(String workflowId, UpdateWorkflowSettingsRequest request) {
        if (request == null) {
            throw badRequest("workflow_settings_request_invalid", "工作流设置请求不能为空");
        }
        validateWorkflowSettingsRequest(request);
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        workflow.setAspectRatio(trimmed(request.aspectRatio(), "9:16"));
        workflow.setStylePreset(trimmed(request.stylePreset(), "cinematic"));
        workflow.setTextAnalysisModel(trimmed(request.textAnalysisModel(), ""));
        workflow.setImageModel(trimmed(request.imageModel(), ""));
        workflow.setVideoModel(trimmed(request.videoModel(), ""));
        workflow.setVideoSize(trimmed(request.videoSize(), defaultVideoSize(workflow.getAspectRatio())));
        workflow.setKeyframeSeed(request.keyframeSeed());
        workflow.setVideoSeed(request.videoSeed());
        workflow.setTaskSeed(resolvedSharedSeed(request.keyframeSeed(), request.videoSeed(), null));
        String durationMode = normalizeDurationMode(request.durationMode(), request.minDurationSeconds(), request.maxDurationSeconds());
        workflow.setDurationMode(durationMode);
        int minDurationSeconds = "auto".equals(durationMode) ? DEFAULT_WORKFLOW_MIN_DURATION_SECONDS : Math.max(1, request.minDurationSeconds());
        int maxDurationSeconds = "auto".equals(durationMode) ? DEFAULT_WORKFLOW_MAX_DURATION_SECONDS : Math.max(request.maxDurationSeconds(), minDurationSeconds);
        workflow.setMinDurationSeconds(minDurationSeconds);
        workflow.setMaxDurationSeconds(maxDurationSeconds);
        workflow.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveWorkflow(workflow);
        Map<String, Object> settingsLogPayload = new LinkedHashMap<>();
        settingsLogPayload.put("workflowId", workflowId);
        settingsLogPayload.put("aspectRatio", workflow.getAspectRatio());
        settingsLogPayload.put("stylePreset", workflow.getStylePreset());
        settingsLogPayload.put("textAnalysisModel", workflow.getTextAnalysisModel());
        settingsLogPayload.put("imageModel", workflow.getImageModel());
        settingsLogPayload.put("videoModel", workflow.getVideoModel());
        settingsLogPayload.put("videoSize", workflow.getVideoSize());
        settingsLogPayload.put("keyframeSeed", workflow.getKeyframeSeed() == null ? "" : workflow.getKeyframeSeed());
        settingsLogPayload.put("videoSeed", workflow.getVideoSeed() == null ? "" : workflow.getVideoSeed());
        settingsLogPayload.put("durationMode", workflow.getDurationMode());
        settingsLogPayload.put("minDurationSeconds", workflow.getMinDurationSeconds());
        settingsLogPayload.put("maxDurationSeconds", workflow.getMaxDurationSeconds());
        workflowRepository.saveSystemLog(
            workflowId,
            "workflow",
            "settings",
            "workflow.settings.updated",
            "INFO",
            "工作流设置已更新",
            settingsLogPayload
        );
        return getWorkflow(workflowId);
    }

    public Map<String, Object> deleteStageVersion(String workflowId, String versionId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity targetVersion = requireStageVersion(workflowId, versionId, "");
        List<StageVersionEntity> existingVersions = workflowRepository.listStageVersions(workflowId);
        List<StageVersionEntity> versionsToDelete = resolveDeleteVersionChain(targetVersion, existingVersions);
        boolean selectedStoryboardDeleted = WorkflowConstants.STAGE_STORYBOARD.equals(targetVersion.getStageType())
            && targetVersion.getStageVersionId().equals(trimmed(workflow.getSelectedStoryboardVersionId(), ""));
        boolean selectedVersionDeleted = versionsToDelete.stream().anyMatch(item -> intValue(item.getSelected(), 0) == 1) || selectedStoryboardDeleted;
        Set<Integer> impactedKeyframeClips = versionsToDelete.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .map(item -> intValue(item.getClipIndex(), 0))
            .collect(Collectors.toCollection(LinkedHashSet::new));
        Set<Integer> impactedVideoClips = versionsToDelete.stream()
            .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()))
            .map(item -> intValue(item.getClipIndex(), 0))
            .collect(Collectors.toCollection(LinkedHashSet::new));
        for (StageVersionEntity version : versionsToDelete) {
            markStageVersionDeleted(version);
            markStageVersionMaterialAssetDeleted(version);
        }
        if (selectedStoryboardDeleted) {
            StageVersionEntity replacementStoryboard = latestStageVersion(workflowRepository.listStageVersions(workflowId), WorkflowConstants.STAGE_STORYBOARD, 0, null);
            applyStoryboardSelection(workflow, replacementStoryboard);
            workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_KEYFRAME, null);
            workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, null);
        } else {
            normalizeImpactedKeyframeSelections(workflowId, impactedKeyframeClips);
            if (WorkflowConstants.STAGE_KEYFRAME.equals(targetVersion.getStageType())) {
                for (Integer clipIndex : impactedKeyframeClips) {
                    int normalizedClipIndex = intValue(clipIndex, 0);
                    if (normalizedClipIndex > 0 && normalizedClipIndex < CHARACTER_SHEET_CLIP_INDEX_BASE) {
                        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, normalizedClipIndex);
                    }
                }
            } else {
                impactedVideoClips.addAll(impactedKeyframeClips.stream().filter(clipIndex -> clipIndex > 0 && clipIndex < CHARACTER_SHEET_CLIP_INDEX_BASE).toList());
                normalizeImpactedVideoSelections(workflowId, impactedVideoClips);
            }
        }
        if (selectedVersionDeleted) {
            detachFinalJoinAsset(workflow);
        }
        syncAllWorkflowAssetSelection(workflowId);
        refreshWorkflowProgressState(workflow);
        workflow.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> generateStoryboard(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0);
        Map<String, Object> storyboardRequest = buildStoryboardRunRequest(workflow, versionNo);
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            "workflow.storyboard.generate",
            storyboardRequest,
            Map.of("versionNo", versionNo)
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String scriptMarkdown = stringValue(result.get("scriptMarkdown"));
        if (scriptMarkdown.isBlank()) {
            throw badRequest("workflow_storyboard_empty", "分镜脚本为空，未生成有效输出");
        }
        List<Map<String, Object>> clips = buildStoryboardClipPayload(workflow, scriptMarkdown);
        String fileUrl = stringValue(result.get("markdownUrl"));
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            0,
            versionNo,
            "text",
            workflow.getTitle() + " 分镜脚本 V" + versionNo,
            fileUrl,
            fileUrl,
            "text/markdown",
            0.0,
            0,
            0,
            false,
            "",
            "",
            Map.of(
                "scriptMarkdown", scriptMarkdown,
                "clipCount", clips.size()
            )
        );
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_STORYBOARD);
        version.setClipIndex(0);
        version.setVersionNo(versionNo);
        version.setTitle("分镜脚本 V" + versionNo);
        version.setStatus("SUCCEEDED");
        version.setSelected(isBlank(workflow.getSelectedStoryboardVersionId()) ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId("");
        version.setSourceMaterialAssetId("");
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(fileUrl);
        version.setDownloadUrl(fileUrl);
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "title", workflow.getTitle(),
            "transcriptLength", safeLength(workflow.getTranscriptText())
        )));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "scriptMarkdown", scriptMarkdown,
            "clips", clips,
            "clipCount", clips.size(),
            "previewText", truncate(scriptMarkdown, 220)
        )));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "runId", stringValue(run.get("id")),
            "modelInfo", mapValue(result.get("modelInfo"))
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (version.getSelected() == 1) {
            workflow.setSelectedStoryboardVersionId(version.getStageVersionId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> adjustStoryboard(String workflowId, String versionId, String prompt) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity sourceVersion = requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_STORYBOARD);
        Map<String, Object> sourceOutputSummary = stageOutputSummary(sourceVersion);
        String sourceScriptMarkdown = stringValue(sourceOutputSummary.get("scriptMarkdown"));
        if (sourceScriptMarkdown.isBlank()) {
            throw badRequest("workflow_storyboard_source_empty", "原分镜脚本为空，无法调整");
        }
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0);
        String adjustmentPrompt = trimmed(prompt, "");
        Map<String, Object> storyboardRequest = buildStoryboardAdjustRunRequest(workflow, sourceScriptMarkdown, adjustmentPrompt, versionNo);
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("versionNo", versionNo);
        context.put("sourceVersionId", sourceVersion.getStageVersionId());
        context.put("adjustmentMode", adjustmentPrompt.isBlank() ? "self_review" : "user_prompt");
        if (!adjustmentPrompt.isBlank()) {
            context.put("adjustmentPrompt", adjustmentPrompt);
        }
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            "workflow.storyboard.adjust",
            storyboardRequest,
            context
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String scriptMarkdown = stringValue(result.get("scriptMarkdown"));
        if (scriptMarkdown.isBlank()) {
            throw badRequest("workflow_storyboard_adjust_empty", "分镜脚本调整结果为空");
        }
        List<Map<String, Object>> clips = buildStoryboardClipPayload(workflow, scriptMarkdown);
        String fileUrl = stringValue(result.get("markdownUrl"));
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_STORYBOARD,
            0,
            versionNo,
            "text",
            workflow.getTitle() + " 分镜脚本 V" + versionNo + " 调整",
            fileUrl,
            fileUrl,
            "text/markdown",
            0.0,
            0,
            0,
            false,
            "",
            "",
            Map.of(
                "scriptMarkdown", scriptMarkdown,
                "clipCount", clips.size(),
                "sourceVersionId", sourceVersion.getStageVersionId(),
                "adjustmentMode", adjustmentPrompt.isBlank() ? "self_review" : "user_prompt"
            )
        );
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_STORYBOARD);
        version.setClipIndex(0);
        version.setVersionNo(versionNo);
        version.setTitle("分镜脚本 V" + versionNo + " 调整");
        version.setStatus("SUCCEEDED");
        version.setSelected(hasNoSelectedVersion(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0) ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId(sourceVersion.getStageVersionId());
        version.setSourceMaterialAssetId(sourceVersion.getMaterialAssetId());
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(fileUrl);
        version.setDownloadUrl(fileUrl);
        Map<String, Object> inputSummary = new LinkedHashMap<>();
        inputSummary.put("title", workflow.getTitle());
        inputSummary.put("sourceVersionId", sourceVersion.getStageVersionId());
        inputSummary.put("adjustmentPrompt", adjustmentPrompt);
        inputSummary.put("adjustmentMode", adjustmentPrompt.isBlank() ? "self_review" : "user_prompt");
        inputSummary.put("transcriptLength", safeLength(workflow.getTranscriptText()));
        version.setInputSummaryJson(WorkflowJsonSupport.write(inputSummary));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("scriptMarkdown", scriptMarkdown);
        outputSummary.put("clips", clips);
        outputSummary.put("clipCount", clips.size());
        outputSummary.put("previewText", truncate(scriptMarkdown, 220));
        outputSummary.put("sourceVersionId", sourceVersion.getStageVersionId());
        outputSummary.put("adjustmentPrompt", adjustmentPrompt);
        outputSummary.put("adjustmentMode", adjustmentPrompt.isBlank() ? "self_review" : "user_prompt");
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "runId", stringValue(run.get("id")),
            "modelInfo", mapValue(result.get("modelInfo")),
            "sourceVersionId", sourceVersion.getStageVersionId()
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (version.getSelected() == 1) {
            workflow.setSelectedStoryboardVersionId(version.getStageVersionId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> selectStoryboard(String workflowId, String versionId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity version = requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_STORYBOARD);
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0, versionId);
        syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0, versionId);
        workflow.setSelectedStoryboardVersionId(versionId);
        workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_KEYFRAME, null);
        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, null);
        syncAllWorkflowAssetSelection(workflowId);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> generateKeyframe(String workflowId, int clipIndex) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        CharacterSheetSlot characterSheetSlot = resolveCharacterSheetSlot(storyboardVersion, clipIndex);
        if (characterSheetSlot != null) {
            generateCharacterSheetVersion(workflow, storyboardVersion, characterSheetSlot);
            return getWorkflow(workflowId);
        }
        if (clipIndex == 1) {
            ensureCharacterSheetVersions(workflow, storyboardVersion);
        }
        Map<String, Object> clip = requireStoryboardClip(storyboardVersion, clipIndex);
        List<CharacterSheetSlot> matchedCharacterSlots = matchedCharacterSheetSlots(storyboardVersion, clip);
        List<CharacterReference> characterReferences = resolveCharacterReferences(workflowId, storyboardVersion, matchedCharacterSlots);
        List<String> characterReferenceImageUrls = characterReferences.stream()
            .map(CharacterReference::imageUrl)
            .filter(url -> !url.isBlank())
            .toList();
        String characterConstraintPrompt = buildCharacterConsistencyPrompt(characterReferences);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        String continuitySource = clipIndex == 1 ? "generated_start_frame" : "previous_clip_end_frame";
        FrameGenerationResult startFrame;
        if (clipIndex == 1) {
            Map<String, Object> startFrameRequest = buildKeyframeRunRequest(
                workflow,
                clip,
                clipIndex,
                versionNo,
                firstNonBlank(stringValue(clip.get("startFrame")), stringValue(clip.get("firstFramePrompt"))),
                characterConstraintPrompt,
                List.of(),
                characterReferenceImageUrls,
                "first",
                "clip" + clipIndex + "-first-v" + versionNo
            );
            startFrame = generateKeyframeFrameSafely(
                workflow,
                clipIndex,
                versionNo,
                "first",
                startFrameRequest,
                Map.of("clipIndex", clipIndex, "versionNo", versionNo, "frameRole", "first")
            );
        } else {
            String inheritedStartFrameUrl = resolveWorkflowClipStartFrameUrl(workflowId, clipIndex);
            String inheritedStartFrameRemoteUrl = resolveWorkflowClipStartFrameRemoteUrl(workflowId, clipIndex);
            if (inheritedStartFrameUrl.isBlank()) {
                continuitySource = "previous_clip_end_frame_missing";
            }
            startFrame = inheritedStartFrameUrl.isBlank()
                ? FrameGenerationResult.failure("first", "上一镜头尾帧缺失")
                : FrameGenerationResult.reused("first", inheritedStartFrameUrl, inheritedStartFrameRemoteUrl);
        }
        Map<String, Object> keyframeRequest = buildKeyframeRunRequest(
            workflow,
            clip,
            clipIndex,
            versionNo,
            firstNonBlank(stringValue(clip.get("endFrame")), stringValue(clip.get("lastFramePrompt"))),
            characterConstraintPrompt,
            firstNonBlank(startFrame.remoteUrl(), startFrame.fileUrl()).isBlank() ? List.of() : List.of(firstNonBlank(startFrame.remoteUrl(), startFrame.fileUrl())),
            characterReferenceImageUrls,
            "last",
            "clip" + clipIndex + "-last-v" + versionNo
        );
        FrameGenerationResult endFrame = generateKeyframeFrameSafely(
            workflow,
            clipIndex,
            versionNo,
            "last",
            keyframeRequest,
            Map.of("clipIndex", clipIndex, "versionNo", versionNo, "frameRole", "last", "continuitySource", continuitySource)
        );
        if (!startFrame.available() && !endFrame.available()) {
            throw badRequest("workflow_keyframe_empty", String.join("；", frameFailureMessages(startFrame, endFrame)));
        }
        String fileUrl = firstNonBlank(endFrame.fileUrl(), startFrame.fileUrl());
        String remoteUrl = firstNonBlank(endFrame.remoteUrl(), startFrame.remoteUrl());
        Map<String, Object> assetResult = !endFrame.result().isEmpty() ? endFrame.result() : startFrame.result();
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            "image",
            workflow.getTitle() + " 关键帧 #" + clipIndex + " V" + versionNo,
            fileUrl,
            fileUrl,
            stringValue(assetResult.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(assetResult.get("width"), 0),
            intValue(assetResult.get("height"), 0),
            false,
            stringValue(mapValue(assetResult.get("metadata")).get("taskId")),
            remoteUrl,
            keyframeAssetMetadata(clip, endFrame.run(), startFrame.run(), startFrame.fileUrl(), startFrame.remoteUrl(), endFrame.fileUrl(), endFrame.remoteUrl(), continuitySource)
        );
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle("关键帧 #" + clipIndex + " V" + versionNo);
        boolean completePair = startFrame.available() && endFrame.available();
        boolean shouldSelectWholeVersion = completePair && hasNoSelectedVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        version.setStatus(completePair ? "SUCCEEDED" : "PARTIAL");
        version.setSelected(shouldSelectWholeVersion ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId(storyboardVersion.getStageVersionId());
        version.setSourceMaterialAssetId("");
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(fileUrl);
        version.setDownloadUrl(fileUrl);
        Map<String, Object> keyframeInputSummary = new LinkedHashMap<>();
        keyframeInputSummary.put("clipIndex", clipIndex);
        keyframeInputSummary.put("generationMode", clipIndex == 1 ? "start_and_end" : "end_only");
        keyframeInputSummary.put("imagePrompt", stringValue(clip.get("imagePrompt")));
        keyframeInputSummary.put("firstFramePrompt", stringValue(clip.get("firstFramePrompt")));
        keyframeInputSummary.put("lastFramePrompt", stringValue(clip.get("lastFramePrompt")));
        keyframeInputSummary.put("startFrame", stringValue(clip.get("startFrame")));
        keyframeInputSummary.put("endFrame", stringValue(clip.get("endFrame")));
        keyframeInputSummary.put("actionPath", stringValue(clip.get("actionPath")));
        keyframeInputSummary.put("continuity", stringValue(clip.get("continuity")));
        keyframeInputSummary.put("motion", stringValue(clip.get("motion")));
        keyframeInputSummary.put("cameraMovement", stringValue(clip.get("cameraMovement")));
        keyframeInputSummary.put("continuityHint", stringValue(clip.get("continuityHint")));
        keyframeInputSummary.put("matchedCharacters", matchedCharacterSlots.stream().map(this::toCharacterMatchRow).toList());
        keyframeInputSummary.put("characterReferenceImageUrls", characterReferenceImageUrls);
        keyframeInputSummary.put("startFrameUrl", startFrame.fileUrl());
        keyframeInputSummary.put("firstFrameUrl", startFrame.fileUrl());
        keyframeInputSummary.put("startFrameRemoteUrl", startFrame.remoteUrl());
        keyframeInputSummary.put("firstFrameRemoteUrl", startFrame.remoteUrl());
        keyframeInputSummary.put("endFrameUrl", endFrame.fileUrl());
        keyframeInputSummary.put("lastFrameUrl", endFrame.fileUrl());
        keyframeInputSummary.put("endFrameRemoteUrl", endFrame.remoteUrl());
        keyframeInputSummary.put("lastFrameRemoteUrl", endFrame.remoteUrl());
        keyframeInputSummary.put("continuitySource", continuitySource);
        Integer keyframeSeed = resolvedKeyframeSeedForImageModel(workflow, clipIndex);
        if (keyframeSeed != null) {
            keyframeInputSummary.put("seed", keyframeSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(keyframeInputSummary));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("clip", clip);
        outputSummary.put("fileUrl", fileUrl);
        outputSummary.put("startFrameUrl", startFrame.fileUrl());
        outputSummary.put("firstFrameUrl", startFrame.fileUrl());
        outputSummary.put("startFrameRemoteUrl", startFrame.remoteUrl());
        outputSummary.put("firstFrameRemoteUrl", startFrame.remoteUrl());
        outputSummary.put("endFrameUrl", endFrame.fileUrl());
        outputSummary.put("lastFrameUrl", endFrame.fileUrl());
        outputSummary.put("endFrameRemoteUrl", endFrame.remoteUrl());
        outputSummary.put("lastFrameRemoteUrl", endFrame.remoteUrl());
        outputSummary.put("continuitySource", continuitySource);
        outputSummary.put("width", intValue(assetResult.get("width"), 0));
        outputSummary.put("height", intValue(assetResult.get("height"), 0));
        outputSummary.put("generatedFrames", generatedKeyframeFrames(startFrame.run(), startFrame.result(), endFrame.run(), endFrame.result(), startFrame.fileUrl(), startFrame.remoteUrl(), endFrame.fileUrl(), endFrame.remoteUrl()));
        outputSummary.put("frameFailures", frameFailures(startFrame, endFrame));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        Map<String, Object> modelCallSummary = new LinkedHashMap<>();
        modelCallSummary.put("runId", firstNonBlank(stringValue(endFrame.run().get("id")), stringValue(startFrame.run().get("id"))));
        modelCallSummary.put("endFrameRunId", stringValue(endFrame.run().get("id")));
        modelCallSummary.put("modelInfo", !endFrame.result().isEmpty() ? mapValue(endFrame.result().get("modelInfo")) : mapValue(startFrame.result().get("modelInfo")));
        if (!stringValue(startFrame.run().get("id")).isBlank()) {
            modelCallSummary.put("startFrameRunId", stringValue(startFrame.run().get("id")));
            modelCallSummary.put("startFrameModelInfo", mapValue(startFrame.result().get("modelInfo")));
        }
        modelCallSummary.put("endFrameModelInfo", mapValue(endFrame.result().get("modelInfo")));
        modelCallSummary.put("frameFailures", frameFailures(startFrame, endFrame));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(modelCallSummary));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (startFrame.available() && selectedKeyframeFrameVersion(workflowId, clipIndex, "first") == null) {
            markSelectedKeyframeFrame(workflowId, clipIndex, version.getStageVersionId(), "first");
        }
        if (endFrame.available() && selectedKeyframeFrameVersion(workflowId, clipIndex, "last") == null) {
            markSelectedKeyframeFrame(workflowId, clipIndex, version.getStageVersionId(), "last");
        }
        if (version.getSelected() == 1) {
            syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        } else {
            workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> generateKeyframeFrame(String workflowId, int clipIndex, String requestedFrameRole) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        if (resolveCharacterSheetSlot(storyboardVersion, clipIndex) != null) {
            throw badRequest("keyframe_frame_role_invalid", "角色三视图不支持单独重生首尾帧");
        }
        String frameRole = normalizeFrameRole(requestedFrameRole);
        if (!Set.of("first", "last").contains(frameRole)) {
            throw badRequest("keyframe_frame_role_invalid", "请选择首帧或尾帧");
        }
        if ("first".equals(frameRole) && clipIndex > 1) {
            throw badRequest("keyframe_first_frame_inherited", "第二个镜头开始的首帧由上一镜头尾帧承接，请重生上一镜头尾帧");
        }
        Map<String, Object> clip = requireStoryboardClip(storyboardVersion, clipIndex);
        List<CharacterSheetSlot> matchedCharacterSlots = matchedCharacterSheetSlots(storyboardVersion, clip);
        List<CharacterReference> characterReferences = resolveCharacterReferences(workflowId, storyboardVersion, matchedCharacterSlots);
        List<String> characterReferenceImageUrls = characterReferences.stream()
            .map(CharacterReference::imageUrl)
            .filter(url -> !url.isBlank())
            .toList();
        String characterConstraintPrompt = buildCharacterConsistencyPrompt(characterReferences);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        StageVersionEntity selectedVersion = selectedKeyframeFrameVersion(workflowId, clipIndex, frameRole);
        String inheritedStartFrameUrl = firstNonBlank(
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "first", false),
            selectedVersion == null ? "" : resolveKeyframeFrameUrl(selectedVersion, "first", false)
        );
        String inheritedStartFrameRemoteUrl = firstNonBlank(
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "first", true),
            selectedVersion == null ? "" : resolveKeyframeFrameUrl(selectedVersion, "first", true)
        );
        String inheritedEndFrameUrl = firstNonBlank(
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "last", false),
            selectedVersion == null ? "" : resolveKeyframeFrameUrl(selectedVersion, "last", false)
        );
        String inheritedEndFrameRemoteUrl = firstNonBlank(
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "last", true),
            selectedVersion == null ? "" : resolveKeyframeFrameUrl(selectedVersion, "last", true)
        );
        List<String> continuityReferences = "last".equals(frameRole) && !firstNonBlank(inheritedStartFrameRemoteUrl, inheritedStartFrameUrl).isBlank()
            ? List.of(firstNonBlank(inheritedStartFrameRemoteUrl, inheritedStartFrameUrl))
            : List.of();
        String prompt = "first".equals(frameRole)
            ? firstNonBlank(stringValue(clip.get("startFrame")), stringValue(clip.get("firstFramePrompt")))
            : firstNonBlank(stringValue(clip.get("endFrame")), stringValue(clip.get("lastFramePrompt")));
        Map<String, Object> keyframeRequest = buildKeyframeRunRequest(
            workflow,
            clip,
            clipIndex,
            versionNo,
            prompt,
            characterConstraintPrompt,
            continuityReferences,
            characterReferenceImageUrls,
            frameRole,
            "clip" + clipIndex + "-" + frameRole + "-v" + versionNo
        );
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            "workflow.keyframe.generate",
            keyframeRequest,
            Map.of("clipIndex", clipIndex, "versionNo", versionNo, "frameRole", frameRole, "generationMode", "single_frame")
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String generatedUrl = extractGenerationFileUrl(result);
        if (generatedUrl.isBlank()) {
            throw badRequest("workflow_keyframe_empty", ("first".equals(frameRole) ? "首帧" : "尾帧") + "关键帧生成结果为空");
        }
        String generatedRemoteUrl = resolveGeneratedMediaRemoteUrl(result);
        String startFrameUrl = "first".equals(frameRole) ? generatedUrl : inheritedStartFrameUrl;
        String startFrameRemoteUrl = "first".equals(frameRole) ? generatedRemoteUrl : inheritedStartFrameRemoteUrl;
        String endFrameUrl = "last".equals(frameRole) ? generatedUrl : inheritedEndFrameUrl;
        String endFrameRemoteUrl = "last".equals(frameRole) ? generatedRemoteUrl : inheritedEndFrameRemoteUrl;
        if (startFrameUrl.isBlank() || endFrameUrl.isBlank()) {
            throw badRequest("keyframe_pair_incomplete", "单帧重生需要已有另一张首尾帧作为继承来源");
        }
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            "image",
            workflow.getTitle() + " 关键帧 #" + clipIndex + " V" + versionNo,
            endFrameUrl,
            endFrameUrl,
            stringValue(result.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            false,
            stringValue(mapValue(result.get("metadata")).get("taskId")),
            endFrameRemoteUrl,
            keyframeAssetMetadata(clip, "last".equals(frameRole) ? run : Map.of(), "first".equals(frameRole) ? run : Map.of(), startFrameUrl, startFrameRemoteUrl, endFrameUrl, endFrameRemoteUrl, "single_frame")
        );
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle("关键帧 #" + clipIndex + " V" + versionNo);
        version.setStatus("SUCCEEDED");
        version.setSelected(selectedVersion == null ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId(storyboardVersion.getStageVersionId());
        version.setSourceMaterialAssetId("");
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(endFrameUrl);
        version.setDownloadUrl(endFrameUrl);
        Map<String, Object> inputSummary = new LinkedHashMap<>();
        inputSummary.put("clipIndex", clipIndex);
        inputSummary.put("generationMode", "single_" + frameRole);
        inputSummary.put("frameRole", frameRole);
        inputSummary.put("startFrameUrl", startFrameUrl);
        inputSummary.put("firstFrameUrl", startFrameUrl);
        inputSummary.put("endFrameUrl", endFrameUrl);
        inputSummary.put("lastFrameUrl", endFrameUrl);
        inputSummary.put("inheritedVersionId", selectedVersion == null ? "" : selectedVersion.getStageVersionId());
        Integer keyframeSeed = resolvedKeyframeSeedForImageModel(workflow, clipIndex);
        if (keyframeSeed != null) {
            inputSummary.put("seed", keyframeSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(inputSummary));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("clip", clip);
        outputSummary.put("fileUrl", endFrameUrl);
        outputSummary.put("startFrameUrl", startFrameUrl);
        outputSummary.put("firstFrameUrl", startFrameUrl);
        outputSummary.put("startFrameRemoteUrl", startFrameRemoteUrl);
        outputSummary.put("firstFrameRemoteUrl", startFrameRemoteUrl);
        outputSummary.put("endFrameUrl", endFrameUrl);
        outputSummary.put("lastFrameUrl", endFrameUrl);
        outputSummary.put("endFrameRemoteUrl", endFrameRemoteUrl);
        outputSummary.put("lastFrameRemoteUrl", endFrameRemoteUrl);
        outputSummary.put("generatedFrames", generatedKeyframeFrames(
            "first".equals(frameRole) ? run : Map.of(),
            "first".equals(frameRole) ? result : Map.of(),
            "last".equals(frameRole) ? run : Map.of(),
            "last".equals(frameRole) ? result : Map.of(),
            startFrameUrl,
            startFrameRemoteUrl,
            endFrameUrl,
            endFrameRemoteUrl
        ));
        outputSummary.put(selectionKey(frameRole), true);
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "runId", stringValue(run.get("id")),
            "frameRole", frameRole,
            "modelInfo", mapValue(result.get("modelInfo"))
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        markSelectedKeyframeFrame(workflowId, clipIndex, version.getStageVersionId(), frameRole);
        if (version.getSelected() == 1) {
            syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
        }
        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex);
        if ("last".equals(frameRole)) {
            workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex + 1);
        }
        workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        syncAllWorkflowAssetSelection(workflowId);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> selectKeyframe(String workflowId, int clipIndex, String versionId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        requireSelectedStoryboard(workflow);
        StageVersionEntity version = requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_KEYFRAME);
        if (intValue(version.getClipIndex(), 0) != clipIndex) {
            throw badRequest("stage_version_clip_mismatch", "阶段版本与镜头不匹配");
        }
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, versionId);
        markSelectedKeyframeFrame(workflowId, clipIndex, versionId, "first");
        markSelectedKeyframeFrame(workflowId, clipIndex, versionId, "last");
        syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, versionId);
        if (isCharacterSheetClipIndex(clipIndex)) {
            workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
            return getWorkflow(workflowId);
        }
        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex);
        syncAllWorkflowAssetSelection(workflowId);
        workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> selectKeyframeFrame(String workflowId, int clipIndex, String versionId, String requestedFrameRole) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        requireSelectedStoryboard(workflow);
        String frameRole = normalizeFrameRole(requestedFrameRole);
        if (!Set.of("first", "last").contains(frameRole)) {
            throw badRequest("keyframe_frame_role_invalid", "请选择首帧或尾帧");
        }
        StageVersionEntity version = requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_KEYFRAME);
        if (intValue(version.getClipIndex(), 0) != clipIndex) {
            throw badRequest("stage_version_clip_mismatch", "阶段版本与镜头不匹配");
        }
        if (resolveKeyframeFrameUrlForView(version, frameRole, false).isBlank()) {
            throw badRequest("keyframe_frame_missing", "当前版本没有可选的" + ("first".equals(frameRole) ? "首帧" : "尾帧"));
        }
        markSelectedKeyframeFrame(workflowId, clipIndex, versionId, frameRole);
        workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex);
        if ("last".equals(frameRole)) {
            workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex + 1);
        }
        workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        syncAllWorkflowAssetSelection(workflowId);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> selectCharacterSheetAsset(String workflowId, int clipIndex, SelectCharacterSheetAssetRequest request) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        CharacterSheetSlot slot = resolveCharacterSheetSlot(storyboardVersion, clipIndex);
        String assetId = trimmed(request == null ? "" : request.assetId(), "");
        if (assetId.isBlank()) {
            throw badRequest("material_asset_required", "请选择素材");
        }
        MaterialAssetEntity sourceAsset = requireMaterialAsset(assetId);
        if (!"image".equalsIgnoreCase(trimmed(sourceAsset.getMediaType(), ""))) {
            throw badRequest("material_asset_type_mismatch", "角色三视图只能选择图片素材");
        }
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle(slot.characterName() + " 三视图 V" + versionNo);
        version.setStatus("SUCCEEDED");
        version.setSelected(1);
        version.setRating(sourceAsset.getUserRating());
        version.setRatingNote(trimmed(sourceAsset.getRatingNote(), ""));
        version.setParentVersionId(storyboardVersion.getStageVersionId());
        version.setSourceMaterialAssetId(sourceAsset.getMaterialAssetId());
        version.setMaterialAssetId(sourceAsset.getMaterialAssetId());
        String assetUrl = firstNonBlank(trimmed(sourceAsset.getPublicUrl(), ""), trimmed(sourceAsset.getRemoteUrl(), ""));
        version.setPreviewUrl(assetUrl);
        version.setDownloadUrl(assetUrl);
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "variantKind", VARIANT_KIND_CHARACTER_SHEET,
            "clipIndex", clipIndex,
            "characterName", slot.characterName(),
            "characterDefinition", slot.characterDefinition(),
            "characterAppearance", slot.characterAppearance(),
            "sourceMaterialAssetId", sourceAsset.getMaterialAssetId(),
            "selectionMode", "material_center"
        )));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("variantKind", VARIANT_KIND_CHARACTER_SHEET);
        outputSummary.put("clipIndex", clipIndex);
        outputSummary.put("characterName", slot.characterName());
        outputSummary.put("characterDefinition", slot.characterDefinition());
        outputSummary.put("characterAppearance", slot.characterAppearance());
        outputSummary.put("fileUrl", assetUrl);
        outputSummary.put("sheetUrl", assetUrl);
        outputSummary.put("previewUrl", assetUrl);
        outputSummary.put("sourceMaterialAssetId", sourceAsset.getMaterialAssetId());
        outputSummary.put("width", intValue(sourceAsset.getWidth(), 0));
        outputSummary.put("height", intValue(sourceAsset.getHeight(), 0));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "source", "material_center",
            "sourceMaterialAssetId", sourceAsset.getMaterialAssetId()
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
        syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
        workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        syncAllWorkflowAssetSelection(workflowId);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> generateVideo(String workflowId, int clipIndex) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        StageVersionEntity keyframeVersion = requireSelectedStageVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        Map<String, Object> clip = requireStoryboardClip(storyboardVersion, clipIndex);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex);
        String firstFrameUrl = resolveWorkflowVideoFirstFrameUrl(workflowId, clipIndex, keyframeVersion);
        String lastFrameUrl = resolveWorkflowVideoLastFrameUrl(keyframeVersion);
        Map<String, Object> videoRequest = buildVideoRunRequest(workflow, clip, clipIndex, versionNo, firstFrameUrl, lastFrameUrl);
        LoggedGenerationRun loggedRun = createLoggedGenerationRunWithTracking(
            workflow,
            WorkflowConstants.STAGE_VIDEO,
            "workflow.video.generate",
            videoRequest,
            Map.of("clipIndex", clipIndex, "versionNo", versionNo)
        );
        Map<String, Object> run = loggedRun.run();
        try {
            run = awaitCompletedVideoRun(run);
            persistWorkflowModelCallCompletion(
                loggedRun,
                workflow,
                WorkflowConstants.STAGE_VIDEO,
                "workflow.video.generate",
                videoRequest,
                Map.of("clipIndex", clipIndex, "versionNo", versionNo),
                run,
                null
            );
        } catch (Exception ex) {
            persistWorkflowModelCallCompletion(
                loggedRun,
                workflow,
                WorkflowConstants.STAGE_VIDEO,
                "workflow.video.generate",
                videoRequest,
                Map.of("clipIndex", clipIndex, "versionNo", versionNo),
                ex instanceof GenerationProviderException providerException ? mapValue(providerException.providerResponse()) : Map.of(),
                ex
            );
            throw ex;
        }
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String fileUrl = extractGenerationFileUrl(result);
        if (fileUrl.isBlank()) {
            throw badRequest("workflow_video_empty", "视频生成结果为空");
        }
        String resolvedLastFrameUrl = firstNonBlank(stringValue(metadata.get("lastFrameUrl")), stringValue(metadata.get("requestedLastFrameUrl")), lastFrameUrl);
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_VIDEO,
            clipIndex,
            versionNo,
            "video",
            workflow.getTitle() + " 视频 #" + clipIndex + " V" + versionNo,
            fileUrl,
            fileUrl,
            stringValue(result.getOrDefault("mimeType", "video/mp4")),
            doubleValue(result.get("durationSeconds"), intValue(clip.get("targetDurationSeconds"), workflow.getMaxDurationSeconds())),
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            boolValue(result.get("hasAudio")),
            stringValue(metadata.get("taskId")),
            stringValue(metadata.get("remoteSourceUrl")),
            videoAssetMetadata(clip, run, metadata, firstFrameUrl, lastFrameUrl, resolvedLastFrameUrl)
        );
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflowId);
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_VIDEO);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle("视频 #" + clipIndex + " V" + versionNo);
        version.setStatus("SUCCEEDED");
        version.setSelected(hasNoSelectedVersion(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex) ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId(keyframeVersion.getStageVersionId());
        version.setSourceMaterialAssetId(keyframeVersion.getMaterialAssetId());
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(fileUrl);
        version.setDownloadUrl(fileUrl);
        Map<String, Object> videoInputSummary = new LinkedHashMap<>();
        videoInputSummary.put("clipIndex", clipIndex);
        videoInputSummary.put("videoPrompt", stringValue(clip.get("videoPrompt")));
        videoInputSummary.put("keyframeAssetId", keyframeVersion.getMaterialAssetId());
        videoInputSummary.put("firstFrameUrl", firstFrameUrl);
        videoInputSummary.put("requestedLastFrameUrl", lastFrameUrl);
        Integer videoSeed = resolvedVideoSeed(workflow);
        if (videoSeed != null) {
            videoInputSummary.put("seed", videoSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(videoInputSummary));
        Map<String, Object> videoOutputSummary = new LinkedHashMap<>();
        videoOutputSummary.put("clip", clip);
        videoOutputSummary.put("fileUrl", fileUrl);
        videoOutputSummary.put("durationSeconds", doubleValue(result.get("durationSeconds"), 0.0));
        videoOutputSummary.put("firstFrameUrl", firstNonBlank(stringValue(metadata.get("firstFrameUrl")), firstFrameUrl));
        videoOutputSummary.put("requestedLastFrameUrl", lastFrameUrl);
        videoOutputSummary.put("lastFrameUrl", resolvedLastFrameUrl);
        version.setOutputSummaryJson(WorkflowJsonSupport.write(videoOutputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "runId", stringValue(run.get("id")),
            "modelInfo", mapValue(result.get("modelInfo")),
            "remoteTaskId", stringValue(metadata.get("taskId"))
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (version.getSelected() == 1) {
            syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex, version.getStageVersionId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> selectVideo(String workflowId, int clipIndex, String versionId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_VIDEO);
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex, versionId);
        syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex, versionId);
        workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
        workflow.setStatus(WorkflowConstants.STATUS_READY);
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> finalizeWorkflow(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        List<Map<String, Object>> clips = readClips(storyboardVersion);
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId);
        Map<Integer, StageVersionEntity> selectedVideos = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()) && intValue(item.getSelected(), 0) == 1)
            .collect(Collectors.toMap(item -> intValue(item.getClipIndex(), 0), item -> item, (left, right) -> left, LinkedHashMap::new));
        List<String> sourceUrls = new ArrayList<>();
        List<Integer> clipIndices = new ArrayList<>();
        for (Map<String, Object> clip : clips) {
            int clipIndex = intValue(clip.get("clipIndex"), 0);
            StageVersionEntity videoVersion = selectedVideos.get(clipIndex);
            if (videoVersion == null) {
                throw badRequest("workflow_finalize_missing_video", "镜头 #" + clipIndex + " 还没有选中的视频版本");
            }
            sourceUrls.add(firstNonBlank(videoVersion.getDownloadUrl(), videoVersion.getPreviewUrl()));
            clipIndices.add(clipIndex);
        }
        if (sourceUrls.isEmpty()) {
            throw badRequest("workflow_finalize_empty", "当前没有可拼接的视频版本");
        }
        String relativeDir = workflowRelativeDir(workflow.getWorkflowId()) + "/joined";
        String fileName = "join-" + clipIndices.get(clipIndices.size() - 1) + ".mp4";
        LocalMediaArtifactService.StoredArtifact artifact = sourceUrls.size() == 1
            ? localMediaArtifactService.copyArtifact(sourceUrls.get(0), relativeDir, fileName)
            : localMediaArtifactService.concatVideos(relativeDir, fileName, sourceUrls);
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_JOINED,
            clipIndices.get(clipIndices.size() - 1),
            nextJoinedVersionNo(workflow),
            "video",
            workflow.getTitle() + " 拼接结果",
            artifact.publicUrl(),
            artifact.publicUrl(),
            "video/mp4",
            sumSelectedVideoDuration(selectedVideos.values()),
            0,
            0,
            true,
            "",
            "",
            Map.of(
                "clipIndices", clipIndices,
                "sourceUrls", sourceUrls
            )
        );
        asset.setSelectedForNext(1);
        workflowRepository.saveMaterialAsset(asset);
        workflow.setFinalJoinAssetId(asset.getMaterialAssetId());
        workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
        workflow.setStatus(WorkflowConstants.STATUS_COMPLETED);
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> rateWorkflow(String workflowId, RateWorkflowRequest request) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        workflow.setEffectRating(normalizeRating(request.effectRating()));
        workflow.setEffectRatingNote(normalizeRatingNote(request.effectRatingNote()));
        workflow.setRatedAt(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveWorkflow(workflow);
        return getWorkflow(workflowId);
    }

    public Map<String, Object> rateStageVersion(String workflowId, String versionId, RateStageVersionRequest request) {
        StageVersionEntity version = requireStageVersion(workflowId, versionId, "");
        version.setRating(normalizeRating(request.effectRating()));
        version.setRatingNote(normalizeRatingNote(request.effectRatingNote()));
        version.setRatedAt(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveStageVersion(version);
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(version.getMaterialAssetId(), requiredUserId());
        if (asset != null) {
            asset.setUserRating(version.getRating());
            asset.setRatingNote(version.getRatingNote());
            workflowRepository.saveMaterialAsset(asset);
        }
        return getWorkflow(workflowId);
    }

    public List<Map<String, Object>> listMaterialAssets(
        String q,
        String type,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex,
        String assetType
    ) {
        Long ownerUserId = requiredUserId();
        List<MaterialAssetEntity> assets = workflowRepository.listMaterialAssets(ownerUserId);
        return assets.stream()
            .filter(item -> matchesMaterialFilters(item, q, type, minRating, model, aspectRatio, clipIndex, assetType))
            .map(item -> toMaterialAssetRow(item, false))
            .toList();
    }

    public Map<String, Object> listMaterialAssetPage(
        String q,
        String type,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex,
        String assetType,
        Integer offset,
        Integer limit
    ) {
        Long ownerUserId = requiredUserId();
        int normalizedOffset = Math.max(0, intValue(offset, 0));
        int normalizedLimit = normalizeMaterialAssetPageLimit(limit);
        if (isSimpleMaterialAssetPageQuery(q, type, minRating, model, aspectRatio, clipIndex, assetType)) {
            long total = workflowRepository.countMaterialAssets(ownerUserId);
            List<Map<String, Object>> rows = workflowRepository.listMaterialAssetsPage(ownerUserId, normalizedOffset, normalizedLimit).stream()
                .map(item -> toMaterialAssetRow(item, false))
                .toList();
            return materialAssetPage(rows, normalizedOffset, normalizedLimit, total);
        }
        List<Map<String, Object>> filtered = workflowRepository.listMaterialAssets(ownerUserId).stream()
            .filter(item -> matchesMaterialFilters(item, q, type, minRating, model, aspectRatio, clipIndex, assetType))
            .map(item -> toMaterialAssetRow(item, false))
            .toList();
        int total = filtered.size();
        int fromIndex = Math.min(normalizedOffset, total);
        int toIndex = Math.min(fromIndex + normalizedLimit, total);
        return materialAssetPage(filtered.subList(fromIndex, toIndex), normalizedOffset, normalizedLimit, total);
    }

    public Map<String, Object> createMaterialGeneration(CreateMaterialGenerationRequest request) {
        Long ownerUserId = requiredUserId();
        String assetType = normalizeMaterialAssetType(request == null ? "" : request.assetType());
        String title = trimmed(request == null ? "" : request.title(), defaultMaterialTitle(assetType));
        String description = trimmed(request == null ? "" : request.description(), "");
        List<String> styleKeywords = normalizeStringList(request == null ? null : request.styleKeywords());
        List<String> referenceAssetIds = normalizeStringList(request == null ? null : request.referenceAssetIds());
        List<String> referenceImageUrls = new ArrayList<>(normalizeStringList(request == null ? null : request.referenceImageUrls()));
        for (MaterialAssetEntity referenceAsset : workflowRepository.findMaterialAssetsByIds(new LinkedHashSet<>(referenceAssetIds), ownerUserId).values()) {
            String referenceUrl = firstNonBlank(trimmed(referenceAsset.getRemoteUrl(), ""), trimmed(referenceAsset.getPublicUrl(), ""));
            if (!referenceUrl.isBlank() && !referenceImageUrls.contains(referenceUrl)) {
                referenceImageUrls.add(referenceUrl);
            }
        }
        String aspectRatio = trimmed(request == null ? "" : request.aspectRatio(), "9:16");
        String imageSize = trimmed(request == null ? "" : request.imageSize(), "");
        String textAnalysisModel = trimmed(request == null ? "" : request.textAnalysisModel(), "");
        String imageModel = trimmed(request == null ? "" : request.imageModel(), "");
        requireNonBlank(textAnalysisModel, "textAnalysisModel", "文本模型");
        requireNonBlank(imageModel, "imageModel", "图片模型");
        WorkflowStageGenerationStrategy imageStrategy = stageStrategyResolver.materialImage(ownerUserId, imageModel, assetType);
        referenceImageUrls = externallyAccessibleReferenceImageUrls(referenceImageUrls, imageStrategy.supportsImageDataUriReferences());
        requireNonBlank(description, "description", "素材描述");
        int[] dimensions = materialGenerationDimensions(assetType, aspectRatio, imageSize);
        StageWorkflowEntity materialContext = materialCenterContext(ownerUserId, aspectRatio, styleKeywords, textAnalysisModel, imageModel);
        Map<String, Object> runRequest = buildMaterialGenerationRunRequest(
            ownerUserId,
            assetType,
            title,
            description,
            styleKeywords,
            referenceImageUrls,
            aspectRatio,
            textAnalysisModel,
            imageModel,
            request == null ? null : request.seed(),
            imageStrategy,
            dimensions
        );
        Map<String, Object> run = createLoggedGenerationRun(
            materialContext,
            "material_center",
            "material_center.generate",
            runRequest,
            Map.of(
                "assetType", assetType,
                "title", title,
                "aspectRatio", aspectRatio,
                "imageSize", imageSize
            )
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String fileUrl = extractGenerationFileUrl(result);
        if (fileUrl.isBlank()) {
            throw badRequest("material_generation_empty", "素材生成结果为空");
        }
        String remoteUrl = "";
        MaterialAssetEntity asset = createMaterialAsset(
            materialContext,
            "material_center",
            0,
            1,
            "image",
            title,
            fileUrl,
            fileUrl,
            stringValue(result.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(result.get("width"), dimensions[0]),
            intValue(result.get("height"), dimensions[1]),
            false,
            stringValue(mapValue(result.get("metadata")).get("taskId")),
            remoteUrl,
            materialGenerationMetadata(assetType, title, description, styleKeywords, referenceAssetIds, referenceImageUrls, aspectRatio, imageSize, run, remoteUrl)
        );
        asset.setWorkflowId("");
        asset.setAssetRole(materialAssetRole(assetType));
        asset.setOriginProvider("image-model");
        asset.setOriginModel(imageModel);
        workflowRepository.saveMaterialAsset(asset);
        return getMaterialAsset(asset.getMaterialAssetId());
    }

    public Map<String, Object> getMaterialAsset(String assetId) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        return toMaterialAssetRow(asset);
    }

    public Map<String, Object> rateMaterialAsset(String assetId, UpdateMaterialAssetRatingRequest request) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        asset.setUserRating(normalizeRating(request.effectRating()));
        asset.setRatingNote(normalizeRatingNote(request.effectRatingNote()));
        workflowRepository.saveMaterialAsset(asset);
        StageVersionEntity version = workflowRepository.findStageVersionByMaterialAssetId(assetId);
        if (version != null) {
            version.setRating(asset.getUserRating());
            version.setRatingNote(asset.getRatingNote());
            version.setRatedAt(OffsetDateTime.now(ZoneOffset.UTC));
            workflowRepository.saveStageVersion(version);
        }
        return getMaterialAsset(assetId);
    }

    public Map<String, Object> uploadMaterialAssetRemote(String assetId) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        String remotePath = trimmed(asset.getRemoteUrl(), "");
        if (remotePath.isBlank()) {
            String localUrl = trimmed(asset.getPublicUrl(), "");
            if (localUrl.isBlank()) {
                throw badRequest("material_asset_local_path_missing", "素材缺少本地文件路径，无法上传远端");
            }
            if (!localUrl.startsWith(ApiPathConstants.STORAGE)) {
                throw badRequest("material_asset_local_path_invalid", "只有本地 /storage 素材支持按需上传远端");
            }
            remotePath = storageProperties.buildExternallyAccessibleUrl(localUrl);
            if (remotePath.isBlank()) {
                throw badRequest(
                    "storage_public_base_url_missing",
                    "请先配置 JIANDOU_STORAGE_PUBLIC_BASE_URL 后再上传远端素材"
                );
            }
            if (!isAbsoluteHttpUrl(remotePath)) {
                throw badRequest(
                    "storage_public_base_url_invalid",
                    "JIANDOU_STORAGE_PUBLIC_BASE_URL 必须生成公网可访问的 http(s) URL"
                );
            }
            asset.setRemoteUrl(remotePath);
            asset.setThirdPartyUrl(remotePath);
            asset.setMetadataJson(WorkflowJsonSupport.write(withRemoteUploadMetadata(asset.getMetadataJson(), remotePath)));
            asset.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
            workflowRepository.saveMaterialAsset(asset);
        }
        return toMaterialAssetRow(asset);
    }

    public Map<String, Object> deleteMaterialAsset(String assetId) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        asset.setSelectedForNext(0);
        asset.setIsDeleted(1);
        asset.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveMaterialAsset(asset);
        return Map.of(
            "assetId", assetId,
            "deleted", true
        );
    }

    public Map<String, Object> reuseMaterialAsset(String assetId, ReuseMaterialRequest request) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        if (WorkflowConstants.STAGE_JOINED.equals(asset.getStageType())) {
            throw badRequest("material_reuse_not_supported", "拼接结果暂不支持直接复用");
        }
        StageWorkflowEntity sourceWorkflow = requireWorkflow(asset.getWorkflowId());
        CreateWorkflowRequest createRequest = new CreateWorkflowRequest(
            sourceWorkflow.getTitle() + " 复用",
            sourceWorkflow.getTranscriptText(),
            sourceWorkflow.getAspectRatio(),
            sourceWorkflow.getStylePreset(),
            sourceWorkflow.getTextAnalysisModel(),
            sourceWorkflow.getImageModel(),
            sourceWorkflow.getVideoModel(),
            sourceWorkflow.getVideoSize(),
            sourceWorkflow.getKeyframeSeed(),
            sourceWorkflow.getVideoSeed(),
            sourceWorkflow.getTaskSeed(),
            workflowDurationMode(sourceWorkflow),
            sourceWorkflow.getMinDurationSeconds(),
            sourceWorkflow.getMaxDurationSeconds()
        );
        Map<String, Object> created = createWorkflow(createRequest);
        String targetWorkflowId = stringValue(created.get("id"));
        StageWorkflowEntity targetWorkflow = requireWorkflow(targetWorkflowId);
        StageVersionEntity sourceVersion = workflowRepository.findStageVersionByMaterialAssetId(assetId);
        if (sourceVersion == null) {
            throw notFound("source_stage_version_not_found", "未找到素材对应的阶段版本");
        }
        copyReusableChain(sourceWorkflow, targetWorkflow, sourceVersion);
        return getWorkflow(targetWorkflowId);
    }

    private void copyReusableChain(StageWorkflowEntity sourceWorkflow, StageWorkflowEntity targetWorkflow, StageVersionEntity sourceVersion) {
        if (WorkflowConstants.STAGE_STORYBOARD.equals(sourceVersion.getStageType())) {
            cloneStageVersionAssetAndSelect(targetWorkflow, sourceVersion);
            return;
        }
        if (WorkflowConstants.STAGE_KEYFRAME.equals(sourceVersion.getStageType())) {
            StageVersionEntity storyboardVersion = requireStageVersion(sourceWorkflow.getWorkflowId(), sourceVersion.getParentVersionId(), WorkflowConstants.STAGE_STORYBOARD);
            StageVersionEntity clonedStoryboard = cloneStageVersionAssetAndSelect(targetWorkflow, storyboardVersion);
            StageVersionEntity clonedKeyframe = cloneStageVersionAsset(sourceVersion, targetWorkflow, clonedStoryboard.getStageVersionId(), true);
            targetWorkflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
            targetWorkflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(targetWorkflow);
            syncWorkflowStageAssetSelection(targetWorkflow.getWorkflowId(), WorkflowConstants.STAGE_KEYFRAME, intValue(clonedKeyframe.getClipIndex(), 0), clonedKeyframe.getStageVersionId());
            return;
        }
        if (WorkflowConstants.STAGE_VIDEO.equals(sourceVersion.getStageType())) {
            StageVersionEntity keyframeVersion = requireStageVersion(sourceWorkflow.getWorkflowId(), sourceVersion.getParentVersionId(), WorkflowConstants.STAGE_KEYFRAME);
            copyReusableChain(sourceWorkflow, targetWorkflow, keyframeVersion);
        }
    }

    private StageVersionEntity cloneStageVersionAssetAndSelect(StageWorkflowEntity targetWorkflow, StageVersionEntity sourceVersion) {
        StageVersionEntity cloned = cloneStageVersionAsset(sourceVersion, targetWorkflow, "", true);
        if (WorkflowConstants.STAGE_STORYBOARD.equals(sourceVersion.getStageType())) {
            targetWorkflow.setSelectedStoryboardVersionId(cloned.getStageVersionId());
            targetWorkflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            targetWorkflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(targetWorkflow);
            syncWorkflowStageAssetSelection(targetWorkflow.getWorkflowId(), WorkflowConstants.STAGE_STORYBOARD, 0, cloned.getStageVersionId());
        }
        return cloned;
    }

    private StageVersionEntity cloneStageVersionAsset(StageVersionEntity sourceVersion, StageWorkflowEntity targetWorkflow, String parentVersionId, boolean selected) {
        MaterialAssetEntity sourceAsset = requireMaterialAsset(sourceVersion.getMaterialAssetId());
        MaterialAssetEntity clonedAsset = cloneMaterialAsset(sourceAsset, targetWorkflow, sourceVersion.getStageType(), intValue(sourceVersion.getClipIndex(), 0), 1);
        StageVersionEntity cloned = new StageVersionEntity();
        cloned.setStageVersionId("sv_" + randomId());
        cloned.setWorkflowId(targetWorkflow.getWorkflowId());
        cloned.setOwnerUserId(targetWorkflow.getOwnerUserId());
        cloned.setStageType(sourceVersion.getStageType());
        cloned.setClipIndex(sourceVersion.getClipIndex());
        cloned.setVersionNo(1);
        cloned.setTitle(sourceVersion.getTitle());
        cloned.setStatus("SUCCEEDED");
        cloned.setSelected(selected ? 1 : 0);
        cloned.setRating(sourceVersion.getRating());
        cloned.setRatingNote(sourceVersion.getRatingNote());
        cloned.setRatedAt(sourceVersion.getRatedAt());
        cloned.setParentVersionId(parentVersionId);
        cloned.setSourceMaterialAssetId(sourceVersion.getMaterialAssetId());
        cloned.setMaterialAssetId(clonedAsset.getMaterialAssetId());
        cloned.setPreviewUrl(clonedAsset.getPublicUrl());
        cloned.setDownloadUrl(clonedAsset.getPublicUrl());
        cloned.setInputSummaryJson(sourceVersion.getInputSummaryJson());
        cloned.setOutputSummaryJson(sourceVersion.getOutputSummaryJson());
        cloned.setModelCallSummaryJson(sourceVersion.getModelCallSummaryJson());
        cloned.setIsDeleted(0);
        workflowRepository.saveStageVersion(cloned);
        return cloned;
    }

    private MaterialAssetEntity cloneMaterialAsset(MaterialAssetEntity sourceAsset, StageWorkflowEntity targetWorkflow, String stageType, int clipIndex, int versionNo) {
        String fileUrl = stringValue(sourceAsset.getPublicUrl());
        String targetFileName = fileNameFromUrl(fileUrl);
        String targetRelativeDir = workflowRelativeDir(targetWorkflow.getWorkflowId()) + "/" + stageTypeFolder(stageType);
        LocalMediaArtifactService.StoredArtifact copied = localMediaArtifactService.copyArtifact(fileUrl, targetRelativeDir, targetFileName.isBlank() ? ("reused-" + randomId()) : targetFileName);
        MaterialAssetEntity cloned = createMaterialAsset(
            targetWorkflow,
            stageType,
            clipIndex,
            versionNo,
            trimmed(sourceAsset.getMediaType(), "image"),
            trimmed(sourceAsset.getTitle(), targetWorkflow.getTitle()),
            copied.publicUrl(),
            copied.publicUrl(),
            trimmed(sourceAsset.getMimeType(), ""),
            sourceAsset.getDurationSeconds() == null ? 0.0 : sourceAsset.getDurationSeconds(),
            sourceAsset.getWidth() == null ? 0 : sourceAsset.getWidth(),
            sourceAsset.getHeight() == null ? 0 : sourceAsset.getHeight(),
            sourceAsset.getHasAudio() != null && sourceAsset.getHasAudio() == 1,
            trimmed(sourceAsset.getRemoteTaskId(), ""),
            trimmed(sourceAsset.getRemoteUrl(), ""),
            Map.of(
                "sourceMaterialAssetId", sourceAsset.getMaterialAssetId()
            )
        );
        cloned.setSourceMaterialId(sourceAsset.getMaterialAssetId());
        workflowRepository.saveMaterialAsset(cloned);
        return cloned;
    }

    private boolean matchesMaterialFilters(
        MaterialAssetEntity asset,
        String q,
        String type,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex,
        String assetType
    ) {
        if (!typeValue(type).isBlank() && !typeValue(type).equalsIgnoreCase(trimmed(asset.getStageType(), ""))) {
            return false;
        }
        if (!typeValue(assetType).isBlank() && !materialAssetType(asset).equalsIgnoreCase(typeValue(assetType))) {
            return false;
        }
        if (minRating != null && (asset.getUserRating() == null || asset.getUserRating() < minRating)) {
            return false;
        }
        if (!typeValue(model).isBlank() && !trimmed(asset.getOriginModel(), "").toLowerCase(Locale.ROOT).contains(typeValue(model).toLowerCase(Locale.ROOT))) {
            return false;
        }
        Map<String, Object> metadata = WorkflowJsonSupport.readMap(asset.getMetadataJson());
        if (!typeValue(aspectRatio).isBlank() && !typeValue(aspectRatio).equalsIgnoreCase(stringValue(metadata.get("aspectRatio")))) {
            return false;
        }
        if (clipIndex != null && intValue(asset.getClipIndex(), 0) != clipIndex) {
            return false;
        }
        String keyword = typeValue(q).toLowerCase(Locale.ROOT);
        if (!keyword.isBlank()) {
            String haystack = String.join(" ",
                trimmed(asset.getTitle(), ""),
                trimmed(asset.getStageType(), ""),
                trimmed(asset.getAssetRole(), ""),
                trimmed(asset.getOriginModel(), ""),
                trimmed(asset.getWorkflowId(), ""),
                metadata.values().stream().map(this::stringValue).collect(Collectors.joining(" "))
            ).toLowerCase(Locale.ROOT);
            if (!haystack.contains(keyword)) {
                return false;
            }
        }
        return true;
    }

    private int normalizeMaterialAssetPageLimit(Integer limit) {
        int value = intValue(limit, MATERIAL_ASSET_PAGE_DEFAULT_LIMIT);
        if (value <= 0) {
            return MATERIAL_ASSET_PAGE_DEFAULT_LIMIT;
        }
        return Math.min(value, MATERIAL_ASSET_PAGE_MAX_LIMIT);
    }

    private boolean isSimpleMaterialAssetPageQuery(
        String q,
        String type,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex,
        String assetType
    ) {
        return typeValue(q).isBlank()
            && typeValue(type).isBlank()
            && minRating == null
            && typeValue(model).isBlank()
            && typeValue(aspectRatio).isBlank()
            && clipIndex == null
            && typeValue(assetType).isBlank();
    }

    private Map<String, Object> materialAssetPage(List<Map<String, Object>> items, int offset, int limit, long total) {
        int nextOffset = offset + items.size();
        Map<String, Object> page = new LinkedHashMap<>();
        page.put("items", items);
        page.put("offset", offset);
        page.put("limit", limit);
        page.put("total", total);
        page.put("hasMore", nextOffset < total);
        page.put("nextOffset", nextOffset < total ? nextOffset : null);
        return page;
    }

    private Map<String, Object> toWorkflowSummary(StageWorkflowEntity workflow, List<StageVersionEntity> versions) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", workflow.getWorkflowId());
        row.put("title", workflow.getTitle());
        row.put("status", workflow.getStatus());
        row.put("currentStage", workflow.getCurrentStage());
        row.put("aspectRatio", workflow.getAspectRatio());
        row.put("effectRating", workflow.getEffectRating());
        row.put("createdAt", format(workflow.getCreateTime()));
        row.put("updatedAt", format(workflow.getUpdateTime()));
        long characterSheetVersionCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .count();
        long keyframeVersionCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> !VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .count();
        long characterSheetCount = selectedWorkflowStoryboard(versions, workflow)
            .map(storyboard -> (long) characterSheetSlots(storyboard).size())
            .orElse(0L);
        long selectedCharacterSheetCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .filter(item -> intValue(item.getSelected(), 0) == 1)
            .count();
        row.put("storyboardVersionCount", versions.stream().filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType())).count());
        row.put("characterSheetCount", characterSheetCount);
        row.put("selectedCharacterSheetCount", selectedCharacterSheetCount);
        row.put("characterSheetVersionCount", characterSheetVersionCount);
        row.put("keyframeVersionCount", keyframeVersionCount);
        row.put("videoVersionCount", versions.stream().filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType())).count());
        return row;
    }

    private WorkflowSummaryResponse toWorkflowSummaryResponse(StageWorkflowEntity workflow, List<StageVersionEntity> versions) {
        long characterSheetVersionCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .count();
        long keyframeVersionCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> !VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .count();
        long characterSheetCount = selectedWorkflowStoryboard(versions, workflow)
            .map(storyboard -> (long) characterSheetSlots(storyboard).size())
            .orElse(0L);
        long selectedCharacterSheetCount = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
            .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .filter(item -> intValue(item.getSelected(), 0) == 1)
            .count();
        return new WorkflowSummaryResponse(
            workflow.getWorkflowId(),
            workflow.getTitle(),
            workflow.getStatus(),
            workflow.getCurrentStage(),
            workflow.getAspectRatio(),
            workflow.getEffectRating(),
            format(workflow.getCreateTime()),
            format(workflow.getUpdateTime()),
            versions.stream().filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType())).count(),
            characterSheetCount,
            selectedCharacterSheetCount,
            characterSheetVersionCount,
            keyframeVersionCount,
            versions.stream().filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType())).count()
        );
    }

    private Optional<StageVersionEntity> selectedWorkflowStoryboard(List<StageVersionEntity> versions, StageWorkflowEntity workflow) {
        String selectedStoryboardVersionId = trimmed(workflow.getSelectedStoryboardVersionId(), "");
        return versions.stream()
            .filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType()))
            .filter(item -> selectedStoryboardVersionId.equals(trimmed(item.getStageVersionId(), "")) || intValue(item.getSelected(), 0) == 1)
            .max(Comparator.comparing(item -> intValue(item.getVersionNo(), 0)));
    }

    private Map<String, Object> toWorkflowDetail(
        StageWorkflowEntity workflow,
        List<StageVersionEntity> versions,
        Map<String, MaterialAssetEntity> assetMap
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", workflow.getWorkflowId());
        row.put("title", workflow.getTitle());
        row.put("transcriptText", workflow.getTranscriptText());
        row.put("aspectRatio", workflow.getAspectRatio());
        row.put("stylePreset", workflow.getStylePreset());
        row.put("textAnalysisModel", workflow.getTextAnalysisModel());
        row.put("imageModel", workflow.getImageModel());
        row.put("videoModel", workflow.getVideoModel());
        row.put("videoSize", workflow.getVideoSize());
        row.put("keyframeSeed", resolvedKeyframeSeed(workflow));
        row.put("videoSeed", resolvedVideoSeed(workflow));
        row.put("seed", resolvedSharedSeed(workflow));
        row.put("durationMode", workflowDurationMode(workflow));
        row.put("minDurationSeconds", workflow.getMinDurationSeconds());
        row.put("maxDurationSeconds", workflow.getMaxDurationSeconds());
        row.put("status", workflow.getStatus());
        row.put("currentStage", workflow.getCurrentStage());
        row.put("selectedStoryboardVersionId", workflow.getSelectedStoryboardVersionId());
        row.put("effectRating", workflow.getEffectRating());
        row.put("effectRatingNote", workflow.getEffectRatingNote());
        row.put("ratedAt", format(workflow.getRatedAt()));
        row.put("createdAt", format(workflow.getCreateTime()));
        row.put("updatedAt", format(workflow.getUpdateTime()));
        List<StageVersionEntity> storyboardVersions = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType()))
            .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
            .toList();
        List<Map<String, Object>> storyboardRows = storyboardVersions.stream()
            .map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId())))
            .toList();
        row.put("storyboardVersions", storyboardRows);
        StageVersionEntity selectedStoryboard = storyboardVersions.stream().filter(item -> intValue(item.getSelected(), 0) == 1).findFirst().orElse(null);
        row.put(
            "characterSheets",
            selectedStoryboard == null ? List.of() : buildCharacterSheetRows(selectedStoryboard, versions, assetMap)
        );
        List<Map<String, Object>> clips = selectedStoryboard == null ? List.of() : readClips(selectedStoryboard);
        List<Map<String, Object>> clipSlots = new ArrayList<>();
        String selectedStoryboardVersionId = selectedStoryboard == null ? "" : trimmed(selectedStoryboard.getStageVersionId(), "");
        for (Map<String, Object> clip : clips) {
            int clipIndex = intValue(clip.get("clipIndex"), 0);
            List<CharacterSheetSlot> matchedCharacterSlots = selectedStoryboard == null ? List.of() : matchedCharacterSheetSlots(selectedStoryboard, clip);
            List<StageVersionEntity> keyframeVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
                .filter(item -> selectedStoryboardVersionId.equals(trimmed(item.getParentVersionId(), "")))
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            Set<String> keyframeVersionIds = keyframeVersions.stream()
                .map(StageVersionEntity::getStageVersionId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
            List<StageVersionEntity> videoVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
                .filter(item -> keyframeVersionIds.contains(trimmed(item.getParentVersionId(), "")))
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            Map<String, Object> slot = new LinkedHashMap<>();
            slot.put("clipIndex", clipIndex);
            slot.put("shotLabel", stringValue(clip.get("shotLabel")));
            slot.put("scene", stringValue(clip.get("scene")));
            slot.put("startFrame", stringValue(clip.get("startFrame")));
            slot.put("endFrame", stringValue(clip.get("endFrame")));
            slot.put("actionPath", stringValue(clip.get("actionPath")));
            slot.put("continuity", stringValue(clip.get("continuity")));
            slot.put("visualConsistency", stringValue(clip.get("visualConsistency")));
            slot.put("firstFramePrompt", stringValue(clip.get("firstFramePrompt")));
            slot.put("lastFramePrompt", stringValue(clip.get("lastFramePrompt")));
            slot.put("motion", stringValue(clip.get("motion")));
            slot.put("cameraMovement", stringValue(clip.get("cameraMovement")));
            slot.put("continuityHint", stringValue(clip.get("continuityHint")));
            slot.put("durationHint", stringValue(clip.get("durationHint")));
            slot.put("targetDurationSeconds", intValue(clip.get("targetDurationSeconds"), 0));
            slot.put("matchedCharacters", matchedCharacterSlots.stream().map(this::toCharacterMatchRow).toList());
            slot.put("keyframeVersions", keyframeVersions.stream().map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()))).toList());
            slot.put("videoVersions", videoVersions.stream().map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()))).toList());
            clipSlots.add(slot);
        }
        row.put("clipSlots", clipSlots);
        row.put("finalResult", isBlank(workflow.getFinalJoinAssetId()) ? null : toMaterialAssetRow(assetMap.get(workflow.getFinalJoinAssetId())));
        return row;
    }

    private List<Map<String, Object>> buildCharacterSheetRows(
        StageVersionEntity storyboardVersion,
        List<StageVersionEntity> versions,
        Map<String, MaterialAssetEntity> assetMap
    ) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (CharacterSheetSlot slot : characterSheetSlots(storyboardVersion)) {
            List<StageVersionEntity> characterSheetVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
                .filter(item -> intValue(item.getClipIndex(), 0) == slot.syntheticClipIndex())
                .filter(item -> storyboardVersion.getStageVersionId().equals(trimmed(item.getParentVersionId(), "")))
                .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", "character-sheet-" + slot.syntheticClipIndex());
            row.put("characterName", slot.characterName());
            row.put("displayName", slot.characterName());
            row.put("appearanceSummary", slot.characterAppearance());
            row.put("appearance", slot.characterAppearance());
            row.put("syntheticClipIndex", slot.syntheticClipIndex());
            row.put("clipIndex", slot.syntheticClipIndex());
            row.put(
                "versions",
                characterSheetVersions.stream()
                    .map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId())))
                    .toList()
            );
            rows.add(row);
        }
        return rows;
    }

    private Map<String, Object> toStageVersionRow(StageVersionEntity version, MaterialAssetEntity asset) {
        Map<String, Object> inputSummary = stageInputSummary(version);
        Map<String, Object> outputSummary = stageOutputSummaryForView(version);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", version.getStageVersionId());
        row.put("stageType", version.getStageType());
        row.put("clipIndex", intValue(version.getClipIndex(), 0));
        row.put("versionNo", intValue(version.getVersionNo(), 0));
        row.put("title", version.getTitle());
        row.put("status", version.getStatus());
        row.put("selected", intValue(version.getSelected(), 0) == 1);
        row.put("rating", version.getRating());
        row.put("ratingNote", version.getRatingNote());
        row.put("ratedAt", format(version.getRatedAt()));
        row.put("parentVersionId", version.getParentVersionId());
        row.put("sourceMaterialAssetId", version.getSourceMaterialAssetId());
        row.put("materialAssetId", version.getMaterialAssetId());
        row.put("previewUrl", version.getPreviewUrl());
        row.put("downloadUrl", version.getDownloadUrl());
        row.put("inputSummary", inputSummary);
        row.put("outputSummary", outputSummary);
        row.put("modelCallSummary", WorkflowJsonSupport.readMap(version.getModelCallSummaryJson()));
        row.put("createdAt", format(version.getCreateTime()));
        row.put("updatedAt", format(version.getUpdateTime()));
        row.put("asset", asset == null ? null : toMaterialAssetRow(asset));
        return row;
    }

    private Map<String, Object> toMaterialAssetRow(MaterialAssetEntity asset) {
        return toMaterialAssetRow(asset, true);
    }

    private Map<String, Object> toMaterialAssetRow(MaterialAssetEntity asset, boolean includeFullMetadata) {
        if (asset == null) {
            return null;
        }
        Map<String, Object> metadata = WorkflowJsonSupport.readMap(asset.getMetadataJson());
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", asset.getMaterialAssetId());
        row.put("workflowId", asset.getWorkflowId());
        row.put("stageType", asset.getStageType());
        row.put("assetType", materialAssetType(asset));
        row.put("assetRole", asset.getAssetRole());
        row.put("clipIndex", intValue(asset.getClipIndex(), 0));
        row.put("versionNo", intValue(asset.getVersionNo(), 0));
        row.put("selectedForNext", intValue(asset.getSelectedForNext(), 0) == 1);
        row.put("userRating", asset.getUserRating());
        row.put("ratingNote", asset.getRatingNote());
        row.put("mediaType", asset.getMediaType());
        row.put("title", asset.getTitle());
        row.put("originModel", asset.getOriginModel());
        row.put("originProvider", asset.getOriginProvider());
        row.put("mimeType", asset.getMimeType());
        row.put("durationSeconds", asset.getDurationSeconds());
        row.put("width", asset.getWidth());
        row.put("height", asset.getHeight());
        row.put("hasAudio", asset.getHasAudio() != null && asset.getHasAudio() == 1);
        row.put("fileUrl", asset.getPublicUrl());
        row.put("previewUrl", asset.getPublicUrl());
        row.put("thumbnailUrl", persistedMaterialAssetThumbnailUrl(asset));
        row.put("remoteUrl", asset.getRemoteUrl());
        row.put("hasRemotePath", !trimmed(asset.getRemoteUrl(), "").isBlank());
        row.put("remotePath", trimmed(asset.getRemoteUrl(), ""));
        row.put("metadata", includeFullMetadata ? metadata : materialAssetListMetadata(asset, metadata));
        row.put("createdAt", format(asset.getCreateTime()));
        row.put("updatedAt", format(asset.getUpdateTime()));
        return row;
    }

    private Map<String, Object> materialAssetListMetadata(MaterialAssetEntity asset, Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> compact = new LinkedHashMap<>();
        copyCompactMetadata(compact, metadata, "assetType");
        copyCompactMetadata(compact, metadata, "description");
        copyCompactMetadata(compact, metadata, "aspectRatio");
        copyCompactMetadata(compact, metadata, "imageSize");
        copyCompactMetadata(compact, metadata, "kind");
        copyCompactMetadata(compact, metadata, "clipIndex");
        copyCompactMetadata(compact, metadata, "runId");
        copyCompactMetadata(compact, metadata, "remoteSourceUrl");
        copyCompactMetadata(compact, metadata, "sourceMaterialAssetId");
        copyCompactMetadata(compact, metadata, "styleKeywords");
        if ("text".equalsIgnoreCase(trimmed(asset.getMediaType(), ""))) {
            copyCompactMetadata(compact, metadata, "scriptMarkdown");
            copyCompactMetadata(compact, metadata, "clipCount");
        }
        return compact;
    }

    private void copyCompactMetadata(Map<String, Object> target, Map<String, Object> source, String key) {
        if (target == null || source == null || key == null || !source.containsKey(key)) {
            return;
        }
        Object value = source.get(key);
        if (value == null) {
            return;
        }
        if (value instanceof String text) {
            String trimmedValue = text.trim();
            if (trimmedValue.isBlank() || trimmedValue.startsWith("data:")) {
                return;
            }
            target.put(key, trimmedValue.length() > 2000 ? trimmedValue.substring(0, 2000) : trimmedValue);
            return;
        }
        if (value instanceof Number || value instanceof Boolean || value instanceof List<?>) {
            target.put(key, value);
        }
    }

    private String persistedMaterialAssetThumbnailUrl(MaterialAssetEntity asset) {
        if (asset == null) {
            return "";
        }
        String previousThumbnailUrl = trimmed(asset.getThumbnailUrl(), "");
        String thumbnailUrl = materialAssetThumbnailService.ensureThumbnail(asset);
        if (!thumbnailUrl.isBlank() && previousThumbnailUrl.isBlank()) {
            asset.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
            workflowRepository.saveMaterialAsset(asset);
        }
        return thumbnailUrl;
    }

    private void syncWorkflowStageAssetSelection(String workflowId, String stageType, int clipIndex, String selectedVersionId) {
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> stageType.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
            .toList();
        for (StageVersionEntity item : versions) {
            MaterialAssetEntity asset = workflowRepository.findMaterialAsset(item.getMaterialAssetId(), requiredUserId());
            if (asset == null || !shouldManageStageVersionAssetSelection(item, asset)) {
                continue;
            }
            boolean selected = item.getStageVersionId().equals(selectedVersionId);
            syncMaterialAssetSelection(asset.getMaterialAssetId(), selected);
        }
    }

    private void syncAllWorkflowAssetSelection(String workflowId) {
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId);
        for (StageVersionEntity item : versions) {
            MaterialAssetEntity asset = workflowRepository.findMaterialAsset(item.getMaterialAssetId(), requiredUserId());
            if (asset == null || !shouldManageStageVersionAssetSelection(item, asset)) {
                continue;
            }
            syncMaterialAssetSelection(asset.getMaterialAssetId(), intValue(item.getSelected(), 0) == 1);
        }
    }

    private void syncMaterialAssetSelection(String assetId, boolean selected) {
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(assetId, requiredUserId());
        if (asset == null) {
            return;
        }
        asset.setSelectedForNext(selected ? 1 : 0);
        workflowRepository.saveMaterialAsset(asset);
    }

    private List<StageVersionEntity> resolveDeleteVersionChain(StageVersionEntity targetVersion, List<StageVersionEntity> versions) {
        List<StageVersionEntity> deleted = new ArrayList<>();
        deleted.add(targetVersion);
        if (WorkflowConstants.STAGE_STORYBOARD.equals(targetVersion.getStageType())) {
            List<StageVersionEntity> keyframeVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
                .filter(item -> targetVersion.getStageVersionId().equals(trimmed(item.getParentVersionId(), "")))
                .toList();
            deleted.addAll(keyframeVersions);
            Set<String> keyframeIds = keyframeVersions.stream().map(StageVersionEntity::getStageVersionId).collect(Collectors.toSet());
            deleted.addAll(versions.stream()
                .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()))
                .filter(item -> keyframeIds.contains(trimmed(item.getParentVersionId(), "")))
                .toList());
        } else if (WorkflowConstants.STAGE_KEYFRAME.equals(targetVersion.getStageType())) {
            deleted.addAll(versions.stream()
                .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()))
                .filter(item -> targetVersion.getStageVersionId().equals(trimmed(item.getParentVersionId(), "")))
                .toList());
        }
        return deleted.stream()
            .collect(Collectors.toMap(StageVersionEntity::getStageVersionId, item -> item, (left, right) -> left, LinkedHashMap::new))
            .values()
            .stream()
            .toList();
    }

    private void markStageVersionDeleted(StageVersionEntity version) {
        if (version == null || intValue(version.getIsDeleted(), 0) == 1) {
            return;
        }
        version.setSelected(0);
        version.setIsDeleted(1);
        version.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveStageVersion(version);
    }

    private void markMaterialAssetDeleted(String assetId) {
        if (isBlank(assetId)) {
            return;
        }
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(assetId, requiredUserId());
        if (asset == null || intValue(asset.getIsDeleted(), 0) == 1) {
            return;
        }
        asset.setSelectedForNext(0);
        asset.setIsDeleted(1);
        asset.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
        workflowRepository.saveMaterialAsset(asset);
    }

    private void markStageVersionMaterialAssetDeleted(StageVersionEntity version) {
        if (version == null || isBlank(version.getMaterialAssetId())) {
            return;
        }
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(version.getMaterialAssetId(), requiredUserId());
        if (asset == null) {
            return;
        }
        if (!shouldManageStageVersionAssetSelection(version, asset)) {
            asset.setSelectedForNext(0);
            workflowRepository.saveMaterialAsset(asset);
            return;
        }
        markMaterialAssetDeleted(asset.getMaterialAssetId());
    }

    private boolean shouldManageStageVersionAssetSelection(StageVersionEntity version, MaterialAssetEntity asset) {
        if (version == null || asset == null) {
            return false;
        }
        boolean isReferencedLibraryAsset = !trimmed(version.getSourceMaterialAssetId(), "").isBlank()
            && trimmed(version.getMaterialAssetId(), "").equals(trimmed(version.getSourceMaterialAssetId(), ""));
        boolean belongsToAnotherWorkflow = !trimmed(asset.getWorkflowId(), "").isBlank()
            && !trimmed(asset.getWorkflowId(), "").equals(trimmed(version.getWorkflowId(), ""));
        boolean isMaterialCenterAsset = "material_center".equals(trimmed(asset.getStageType(), ""));
        return !isReferencedLibraryAsset && !belongsToAnotherWorkflow && !isMaterialCenterAsset;
    }

    private void applyStoryboardSelection(StageWorkflowEntity workflow, StageVersionEntity selectedStoryboard) {
        String workflowId = workflow.getWorkflowId();
        if (selectedStoryboard == null) {
            workflow.setSelectedStoryboardVersionId("");
            workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0);
            return;
        }
        workflow.setSelectedStoryboardVersionId(selectedStoryboard.getStageVersionId());
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0, selectedStoryboard.getStageVersionId());
    }

    private void normalizeImpactedKeyframeSelections(String workflowId, Set<Integer> clipIndices) {
        for (Integer clipIndex : clipIndices) {
            int normalizedClipIndex = intValue(clipIndex, 0);
            List<StageVersionEntity> candidates = workflowRepository.listStageVersions(workflowId).stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
                .filter(item -> intValue(item.getClipIndex(), 0) == normalizedClipIndex)
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            if (candidates.isEmpty()) {
                workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_KEYFRAME, normalizedClipIndex);
                continue;
            }
            boolean hasSelected = candidates.stream().anyMatch(item -> intValue(item.getSelected(), 0) == 1);
            if (!hasSelected) {
                workflowRepository.markSelectedStageVersion(
                    workflowId,
                    WorkflowConstants.STAGE_KEYFRAME,
                    normalizedClipIndex,
                    candidates.get(0).getStageVersionId()
                );
            }
        }
    }

    private void normalizeImpactedVideoSelections(String workflowId, Set<Integer> clipIndices) {
        for (Integer clipIndex : clipIndices) {
            int normalizedClipIndex = intValue(clipIndex, 0);
            if (normalizedClipIndex <= 0 || normalizedClipIndex >= CHARACTER_SHEET_CLIP_INDEX_BASE) {
                continue;
            }
            String selectedKeyframeId = selectedStageVersionId(workflowId, WorkflowConstants.STAGE_KEYFRAME, normalizedClipIndex);
            if (selectedKeyframeId.isBlank()) {
                workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, normalizedClipIndex);
                continue;
            }
            List<StageVersionEntity> candidates = workflowRepository.listStageVersions(workflowId).stream()
                .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()))
                .filter(item -> intValue(item.getClipIndex(), 0) == normalizedClipIndex)
                .filter(item -> selectedKeyframeId.equals(trimmed(item.getParentVersionId(), "")))
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            if (candidates.isEmpty()) {
                workflowRepository.clearSelectedStageVersions(workflowId, WorkflowConstants.STAGE_VIDEO, normalizedClipIndex);
                continue;
            }
            boolean hasSelected = candidates.stream().anyMatch(item -> intValue(item.getSelected(), 0) == 1);
            if (!hasSelected) {
                workflowRepository.markSelectedStageVersion(
                    workflowId,
                    WorkflowConstants.STAGE_VIDEO,
                    normalizedClipIndex,
                    candidates.get(0).getStageVersionId()
                );
            }
        }
    }

    private String selectedStageVersionId(String workflowId, String stageType, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> stageType.equals(item.getStageType()))
            .filter(item -> intValue(item.getClipIndex(), 0) == clipIndex)
            .filter(item -> intValue(item.getSelected(), 0) == 1)
            .map(StageVersionEntity::getStageVersionId)
            .findFirst()
            .orElse("");
    }

    private StageVersionEntity latestStageVersion(
        List<StageVersionEntity> versions,
        String stageType,
        int clipIndex,
        String parentVersionId
    ) {
        return versions.stream()
            .filter(item -> stageType.equals(item.getStageType()))
            .filter(item -> intValue(item.getClipIndex(), 0) == clipIndex)
            .filter(item -> parentVersionId == null || parentVersionId.equals(trimmed(item.getParentVersionId(), "")))
            .max(Comparator.comparing(item -> intValue(item.getVersionNo(), 0)))
            .orElse(null);
    }

    private void detachFinalJoinAsset(StageWorkflowEntity workflow) {
        if (workflow == null || isBlank(workflow.getFinalJoinAssetId())) {
            return;
        }
        MaterialAssetEntity finalAsset = workflowRepository.findMaterialAsset(workflow.getFinalJoinAssetId(), requiredUserId());
        if (finalAsset != null) {
            finalAsset.setSelectedForNext(0);
            finalAsset.setUpdateTime(OffsetDateTime.now(ZoneOffset.UTC));
            workflowRepository.saveMaterialAsset(finalAsset);
        }
        workflow.setFinalJoinAssetId("");
    }

    private void refreshWorkflowProgressState(StageWorkflowEntity workflow) {
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflow.getWorkflowId());
        StageVersionEntity selectedStoryboard = versions.stream()
            .filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType()))
            .filter(item -> item.getStageVersionId().equals(trimmed(workflow.getSelectedStoryboardVersionId(), "")) || intValue(item.getSelected(), 0) == 1)
            .max(Comparator.comparing(item -> intValue(item.getVersionNo(), 0)))
            .orElse(null);
        if (selectedStoryboard == null) {
            workflow.setSelectedStoryboardVersionId("");
            workflow.setCurrentStage(WorkflowConstants.STAGE_STORYBOARD);
            workflow.setStatus(WorkflowConstants.STATUS_DRAFT);
            return;
        }
        workflow.setSelectedStoryboardVersionId(selectedStoryboard.getStageVersionId());
        List<Integer> regularClipIndices = readClips(selectedStoryboard).stream()
            .map(clip -> intValue(clip.get("clipIndex"), 0))
            .filter(clipIndex -> clipIndex > 0 && clipIndex < CHARACTER_SHEET_CLIP_INDEX_BASE)
            .toList();
        boolean allKeyframesSelected = regularClipIndices.stream()
            .allMatch(clipIndex -> !selectedStageVersionId(workflow.getWorkflowId(), WorkflowConstants.STAGE_KEYFRAME, clipIndex).isBlank());
        if (!allKeyframesSelected) {
            workflow.setCurrentStage(WorkflowConstants.STAGE_KEYFRAME);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            return;
        }
        boolean allVideosSelected = regularClipIndices.stream()
            .allMatch(clipIndex -> !selectedStageVersionId(workflow.getWorkflowId(), WorkflowConstants.STAGE_VIDEO, clipIndex).isBlank());
        if (!allVideosSelected) {
            workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            return;
        }
        workflow.setCurrentStage(WorkflowConstants.STAGE_JOINED);
        workflow.setStatus(isBlank(workflow.getFinalJoinAssetId()) ? WorkflowConstants.STATUS_READY : WorkflowConstants.STATUS_COMPLETED);
    }

    private Map<String, Object> buildStoryboardRunRequest(StageWorkflowEntity workflow, int versionNo) {
        WorkflowStageGenerationStrategy strategy = stageStrategyResolver.storyboard(workflow);
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("text", !trimmed(workflow.getTranscriptText(), "").isBlank() ? workflow.getTranscriptText() : firstNonBlank(workflow.getGlobalPrompt(), workflow.getTitle()));
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", strategy.modelSection(workflow.getTextAnalysisModel()));
        request.put("options", Map.of(
            "visualStyle", firstNonBlank(workflow.getStylePreset(), "cinematic")
        ));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/storyboards",
            "fileName", "storyboard-v" + versionNo + ".md"
        ));
        request.put("metadata", Map.of(
            "relatedWorkflowId", workflow.getWorkflowId(),
            "stage", WorkflowConstants.STAGE_STORYBOARD,
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private Map<String, Object> buildStoryboardAdjustRunRequest(StageWorkflowEntity workflow, String sourceScriptMarkdown, String adjustmentPrompt, int versionNo) {
        WorkflowStageGenerationStrategy strategy = stageStrategyResolver.storyboardAdjust(workflow);
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("text", !trimmed(workflow.getTranscriptText(), "").isBlank() ? workflow.getTranscriptText() : firstNonBlank(workflow.getGlobalPrompt(), workflow.getTitle()));
        input.put("scriptMarkdown", sourceScriptMarkdown);
        input.put("adjustmentPrompt", adjustmentPrompt);
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", strategy.modelSection(workflow.getTextAnalysisModel()));
        request.put("options", Map.of(
            "visualStyle", firstNonBlank(workflow.getStylePreset(), "cinematic")
        ));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/storyboards",
            "fileName", "storyboard-v" + versionNo + ".md"
        ));
        request.put("metadata", Map.of(
            "relatedWorkflowId", workflow.getWorkflowId(),
            "stage", WorkflowConstants.STAGE_STORYBOARD,
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private Map<String, Object> createLoggedGenerationRun(
        StageWorkflowEntity workflow,
        String stage,
        String eventPrefix,
        Map<String, Object> request,
        Map<String, Object> context
    ) {
        return createLoggedGenerationRunWithTracking(workflow, stage, eventPrefix, request, context).run();
    }

    private LoggedGenerationRun createLoggedGenerationRunWithTracking(
        StageWorkflowEntity workflow,
        String stage,
        String eventPrefix,
        Map<String, Object> request,
        Map<String, Object> context
    ) {
        String modelCallId = "mdlcall_" + randomId();
        OffsetDateTime startedAt = OffsetDateTime.now();
        Map<String, Object> requestPayload = new LinkedHashMap<>();
        requestPayload.put("modelCallId", modelCallId);
        requestPayload.put("workflowId", workflow.getWorkflowId());
        requestPayload.put("workflowTitle", workflow.getTitle());
        requestPayload.put("request", request);
        requestPayload.putAll(context == null ? Map.of() : context);
        workflowRepository.saveModelCall(
            workflow.getWorkflowId(),
            buildWorkflowPendingModelCall(modelCallId, workflow, stage, eventPrefix, request, context, startedAt)
        );
        workflowRepository.saveSystemLog(
            workflow.getWorkflowId(),
            "workflow",
            stage,
            eventPrefix + ".request",
            "INFO",
            "阶段工作流发起模型调用",
            requestPayload
        );
        try {
            Map<String, Object> run = generationApplicationService.createRun(request);
            OffsetDateTime finishedAt = OffsetDateTime.now();
            workflowRepository.saveModelCall(
                workflow.getWorkflowId(),
                buildWorkflowModelCall(modelCallId, workflow, stage, eventPrefix, request, context, run, null, startedAt, finishedAt)
            );
            Map<String, Object> successPayload = new LinkedHashMap<>();
            successPayload.put("modelCallId", modelCallId);
            successPayload.put("workflowId", workflow.getWorkflowId());
            successPayload.put("runId", stringValue(run.get("id")));
            successPayload.put("status", stringValue(run.get("status")));
            successPayload.put("kind", stringValue(run.get("kind")));
            successPayload.put("result", summarizeRunResult(run));
            successPayload.putAll(context == null ? Map.of() : context);
            workflowRepository.saveSystemLog(
                workflow.getWorkflowId(),
                "workflow",
                stage,
                eventPrefix + ".response",
                "INFO",
                "阶段工作流模型调用完成",
                successPayload
            );
            return new LoggedGenerationRun(modelCallId, startedAt, run);
        } catch (Exception ex) {
            OffsetDateTime finishedAt = OffsetDateTime.now();
            workflowRepository.saveModelCall(
                workflow.getWorkflowId(),
                buildWorkflowModelCall(modelCallId, workflow, stage, eventPrefix, request, context, Map.of(), ex, startedAt, finishedAt)
            );
            Map<String, Object> errorPayload = new LinkedHashMap<>();
            errorPayload.put("modelCallId", modelCallId);
            errorPayload.put("workflowId", workflow.getWorkflowId());
            errorPayload.put("request", request);
            errorPayload.put("errorType", ex.getClass().getName());
            errorPayload.put("errorMessage", firstNonBlank(ex.getMessage(), "unknown"));
            errorPayload.putAll(context == null ? Map.of() : context);
            workflowRepository.saveSystemLog(
                workflow.getWorkflowId(),
                "workflow",
                stage,
                eventPrefix + ".failed",
                "ERROR",
                firstNonBlank(ex.getMessage(), "阶段工作流模型调用失败"),
                errorPayload
            );
            throw ex;
        }
    }

    private void persistWorkflowModelCallCompletion(
        LoggedGenerationRun loggedRun,
        StageWorkflowEntity workflow,
        String stage,
        String operation,
        Map<String, Object> request,
        Map<String, Object> context,
        Map<String, Object> run,
        Exception error
    ) {
        if (loggedRun == null || loggedRun.modelCallId().isBlank()) {
            return;
        }
        OffsetDateTime finishedAt = OffsetDateTime.now();
        workflowRepository.saveModelCall(
            workflow.getWorkflowId(),
            buildWorkflowModelCall(
                loggedRun.modelCallId(),
                workflow,
                stage,
                operation,
                request,
                context,
                run == null ? Map.of() : run,
                error,
                loggedRun.startedAt(),
                finishedAt
            )
        );
    }

    private Map<String, Object> buildWorkflowPendingModelCall(
        String modelCallId,
        StageWorkflowEntity workflow,
        String stage,
        String operation,
        Map<String, Object> request,
        Map<String, Object> context,
        OffsetDateTime startedAt
    ) {
        Map<String, Object> modelSection = nestedMapValue(request, "model");
        Map<String, Object> businessRequestPayload = buildBusinessModelCallRequestPayload(workflow, stage, operation, request, context);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", modelCallId);
        row.put("requestLogId", "reqlog_" + modelCallId);
        row.put("ownerUserId", workflow.getOwnerUserId());
        row.put("ownerRefId", workflow.getWorkflowId());
        row.put("workflowId", workflow.getWorkflowId());
        row.put("requestType", firstNonBlank(stringValue(request.get("kind")), stage));
        row.put("callKind", firstNonBlank(stringValue(request.get("kind")), stage));
        row.put("stage", stage);
        row.put("operation", operation);
        row.put("provider", "generation");
        row.put("providerModel", firstNonBlank(
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("requestedModel", firstNonBlank(
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("resolvedModel", "");
        row.put("modelName", "");
        row.put("modelAlias", firstNonBlank(
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("endpointHost", "");
        row.put("requestId", "");
        row.put("requestPayload", businessRequestPayload);
        row.put("responsePayload", Map.of());
        row.put("httpStatus", 0);
        row.put("responseCode", 0);
        row.put("success", false);
        row.put("status", "pending");
        row.put("errorCode", "");
        row.put("errorMessage", "");
        row.put("latencyMs", 0);
        row.put("durationMs", 0);
        row.put("inputTokens", 0);
        row.put("outputTokens", 0);
        row.put("startedAt", startedAt);
        row.put("finishedAt", startedAt);
        return row;
    }

    private Map<String, Object> buildWorkflowModelCall(
        String modelCallId,
        StageWorkflowEntity workflow,
        String stage,
        String operation,
        Map<String, Object> request,
        Map<String, Object> context,
        Map<String, Object> run,
        Exception error,
        OffsetDateTime startedAt,
        OffsetDateTime finishedAt
    ) {
        Map<String, Object> modelSection = nestedMapValue(request, "model");
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> modelInfo = mapValue(result.get("modelInfo"));
        Map<String, Object> businessRequestPayload = buildBusinessModelCallRequestPayload(workflow, stage, operation, request, context);
        Map<String, Object> actualProviderRequest = error instanceof GenerationProviderException providerException
            ? providerException.providerRequest()
            : providerRequestFromRun(run);
        Map<String, Object> requestPayload = actualProviderRequest.isEmpty()
            ? businessRequestPayload
            : buildActualProviderRequestPayload(workflow, stage, operation, context, actualProviderRequest, businessRequestPayload);
        Map<String, Object> responsePayload = new LinkedHashMap<>();
        responsePayload.put("workflowId", workflow.getWorkflowId());
        responsePayload.put("stage", stage);
        responsePayload.put("context", context == null ? Map.of() : context);
        if (error == null) {
            responsePayload.put("run", run == null ? Map.of() : run);
        } else {
            responsePayload.put("errorType", error.getClass().getName());
            responsePayload.put("errorMessage", firstNonBlank(error.getMessage(), "unknown"));
            if (error instanceof GenerationProviderException providerException) {
                responsePayload.put("providerRequest", providerException.providerRequest());
                responsePayload.put("providerResponse", providerException.providerResponse());
                responsePayload.put("httpStatus", providerException.httpStatus());
            }
        }
        int responseStatus = error instanceof GenerationProviderException providerException
            ? Math.max(0, providerException.httpStatus())
            : (error == null ? 200 : 0);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", modelCallId);
        row.put("ownerUserId", workflow.getOwnerUserId());
        row.put("ownerRefId", workflow.getWorkflowId());
        row.put("workflowId", workflow.getWorkflowId());
        row.put("requestType", firstNonBlank(stringValue(request.get("kind")), stage));
        row.put("callKind", firstNonBlank(stringValue(request.get("kind")), stage));
        row.put("stage", stage);
        row.put("operation", operation);
        row.put("provider", firstNonBlank(stringValue(modelInfo.get("provider")), "generation"));
        row.put("providerModel", firstNonBlank(
            stringValue(modelInfo.get("providerModel")),
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("requestedModel", firstNonBlank(
            stringValue(modelInfo.get("requestedModel")),
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("resolvedModel", firstNonBlank(
            stringValue(modelInfo.get("resolvedModel")),
            stringValue(modelInfo.get("providerModel")),
            stringValue(modelInfo.get("modelName"))
        ));
        row.put("modelName", firstNonBlank(
            stringValue(modelInfo.get("modelName")),
            stringValue(modelInfo.get("resolvedModel")),
            stringValue(modelInfo.get("providerModel"))
        ));
        row.put("modelAlias", firstNonBlank(
            stringValue(modelInfo.get("modelName")),
            stringValue(modelInfo.get("requestedModel")),
            stringValue(modelSection.get("providerModel")),
            stringValue(modelSection.get("textAnalysisModel"))
        ));
        row.put("endpointHost", stringValue(modelInfo.get("endpointHost")));
        row.put("requestId", stringValue(run.get("id")));
        row.put("requestPayload", requestPayload);
        row.put("responsePayload", responsePayload);
        row.put("httpStatus", responseStatus);
        row.put("responseCode", responseStatus);
        row.put("success", error == null);
        row.put("errorCode", error == null ? "" : error.getClass().getSimpleName());
        row.put("errorMessage", error == null ? "" : firstNonBlank(error.getMessage(), "unknown"));
        row.put("latencyMs", resolveModelCallLatencyMs(result));
        row.put("durationMs", Math.max(0, (int) java.time.Duration.between(startedAt, finishedAt).toMillis()));
        row.put("inputTokens", intValue(firstNonBlankObject(
            mapValue(result.get("usage")).get("inputTokens"),
            mapValue(mapValue(result.get("metadata")).get("usage")).get("inputTokens")
        ), 0));
        row.put("outputTokens", intValue(firstNonBlankObject(
            mapValue(result.get("usage")).get("outputTokens"),
            mapValue(mapValue(result.get("metadata")).get("usage")).get("outputTokens")
        ), 0));
        row.put("startedAt", startedAt);
        row.put("finishedAt", finishedAt);
        return row;
    }

    private Map<String, Object> buildBusinessModelCallRequestPayload(
        StageWorkflowEntity workflow,
        String stage,
        String operation,
        Map<String, Object> request,
        Map<String, Object> context
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("workflowId", workflow.getWorkflowId());
        payload.put("workflowTitle", workflow.getTitle());
        payload.put("stage", stage);
        payload.put("operation", operation);
        payload.put("context", context == null ? Map.of() : context);
        payload.put("request", request == null ? Map.of() : request);
        return payload;
    }

    private Map<String, Object> buildActualProviderRequestPayload(
        StageWorkflowEntity workflow,
        String stage,
        String operation,
        Map<String, Object> context,
        Map<String, Object> providerRequest,
        Map<String, Object> businessRequestPayload
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.putAll(providerRequest);
        payload.put("workflowId", workflow.getWorkflowId());
        payload.put("workflowTitle", workflow.getTitle());
        payload.put("stage", stage);
        payload.put("operation", operation);
        payload.put("context", context == null ? Map.of() : context);
        payload.put("businessRequest", businessRequestPayload);
        return payload;
    }

    private Map<String, Object> providerRequestFromRun(Map<String, Object> run) {
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        Map<String, Object> providerRequest = mapValue(metadata.get("providerRequest"));
        if (!providerRequest.isEmpty()) {
            return providerRequest;
        }
        Map<String, Object> providerInteraction = mapValue(metadata.get("providerInteraction"));
        return mapValue(providerInteraction.get("providerRequest"));
    }

    private Map<String, Object> nestedMapValue(Map<String, Object> source, String key) {
        if (source == null) {
            return Map.of();
        }
        return mapValue(source.get(key));
    }

    private int resolveModelCallLatencyMs(Map<String, Object> result) {
        return intValue(
            firstNonBlankObject(
                result.get("latencyMs"),
                mapValue(result.get("metadata")).get("latencyMs")
            ),
            0
        );
    }

    private Map<String, Object> summarizeRunResult(Map<String, Object> run) {
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("outputUrl", stringValue(result.get("outputUrl")));
        summary.put("mimeType", stringValue(result.get("mimeType")));
        summary.put("scriptMarkdownLength", safeLength(stringValue(result.get("scriptMarkdown"))));
        summary.put("width", intValue(result.get("width"), 0));
        summary.put("height", intValue(result.get("height"), 0));
        summary.put("durationSeconds", doubleValue(result.get("durationSeconds"), 0.0));
        summary.put("metadata", mapValue(result.get("metadata")));
        return summary;
    }

    private void ensureCharacterSheetVersions(StageWorkflowEntity workflow, StageVersionEntity storyboardVersion) {
        for (CharacterSheetSlot slot : characterSheetSlots(storyboardVersion)) {
            if (hasCharacterSheetVersionForStoryboard(workflow.getWorkflowId(), storyboardVersion.getStageVersionId(), slot.syntheticClipIndex())) {
                continue;
            }
            generateCharacterSheetVersion(workflow, storyboardVersion, slot);
        }
    }

    private void generateCharacterSheetVersion(
        StageWorkflowEntity workflow,
        StageVersionEntity storyboardVersion,
        CharacterSheetSlot slot
    ) {
        int clipIndex = slot.syntheticClipIndex();
        int versionNo = workflowRepository.nextStageVersionNo(workflow.getWorkflowId(), WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        String prompt = buildCharacterSheetPrompt(workflow, slot);
        Map<String, Object> characterSheetRequest = buildCharacterSheetRunRequest(workflow, slot, versionNo, prompt);
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            "workflow.character_sheet.generate",
            characterSheetRequest,
            Map.of(
                "clipIndex", clipIndex,
                "versionNo", versionNo,
                "characterName", slot.characterName(),
                "variantKind", VARIANT_KIND_CHARACTER_SHEET
            )
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String fileUrl = extractGenerationFileUrl(result);
        if (fileUrl.isBlank()) {
            throw badRequest("workflow_character_sheet_empty", "角色三视图生成结果为空");
        }
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            "image",
            workflow.getTitle() + " 角色三视图 " + slot.characterName() + " V" + versionNo,
            fileUrl,
            fileUrl,
            stringValue(result.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            false,
            stringValue(mapValue(result.get("metadata")).get("taskId")),
            resolveGeneratedMediaRemoteUrl(result),
            characterSheetAssetMetadata(slot, run, fileUrl)
        );
        asset.setAssetRole(VARIANT_KIND_CHARACTER_SHEET);
        workflowRepository.saveMaterialAsset(asset);

        StageVersionEntity version = new StageVersionEntity();
        version.setStageVersionId("sv_" + randomId());
        version.setWorkflowId(workflow.getWorkflowId());
        version.setOwnerUserId(workflow.getOwnerUserId());
        version.setStageType(WorkflowConstants.STAGE_KEYFRAME);
        version.setClipIndex(clipIndex);
        version.setVersionNo(versionNo);
        version.setTitle(slot.characterName() + " 三视图 V" + versionNo);
        version.setStatus("SUCCEEDED");
        version.setSelected(hasNoSelectedVersion(workflow.getWorkflowId(), WorkflowConstants.STAGE_KEYFRAME, clipIndex) ? 1 : 0);
        version.setRating(null);
        version.setRatingNote("");
        version.setParentVersionId(storyboardVersion.getStageVersionId());
        version.setSourceMaterialAssetId("");
        version.setMaterialAssetId(asset.getMaterialAssetId());
        version.setPreviewUrl(fileUrl);
        version.setDownloadUrl(fileUrl);
        Map<String, Object> inputSummary = new LinkedHashMap<>();
        inputSummary.put("variantKind", VARIANT_KIND_CHARACTER_SHEET);
        inputSummary.put("clipIndex", clipIndex);
        inputSummary.put("characterName", slot.characterName());
        inputSummary.put("characterDefinition", slot.characterDefinition());
        inputSummary.put("characterAppearance", slot.characterAppearance());
        inputSummary.put("storyboardVersionId", storyboardVersion.getStageVersionId());
        inputSummary.put("imagePrompt", prompt);
        Integer keyframeSeed = resolvedKeyframeSeedForImageModel(workflow, clipIndex);
        if (keyframeSeed != null) {
            inputSummary.put("seed", keyframeSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(inputSummary));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("variantKind", VARIANT_KIND_CHARACTER_SHEET);
        outputSummary.put("clipIndex", clipIndex);
        outputSummary.put("characterName", slot.characterName());
        outputSummary.put("characterDefinition", slot.characterDefinition());
        outputSummary.put("characterAppearance", slot.characterAppearance());
        outputSummary.put("fileUrl", fileUrl);
        outputSummary.put("remoteSourceUrl", resolveGeneratedMediaRemoteUrl(result));
        outputSummary.put("sheetUrl", fileUrl);
        outputSummary.put("previewUrl", fileUrl);
        outputSummary.put("width", intValue(result.get("width"), 0));
        outputSummary.put("height", intValue(result.get("height"), 0));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(Map.of(
            "runId", stringValue(run.get("id")),
            "modelInfo", mapValue(result.get("modelInfo"))
        )));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (version.getSelected() == 1) {
            syncWorkflowStageAssetSelection(workflow.getWorkflowId(), WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
    }

    private String buildCharacterSheetPrompt(StageWorkflowEntity workflow, CharacterSheetSlot slot) {
        return String.join(
            "\n",
            "人物绑定：",
            "- 角色：" + slot.characterName(),
            "- 角色完整定义：" + slot.characterDefinition(),
            "- 外观唯一依据：" + slot.characterAppearance(),
            "生成要求：",
            "- 只出现这一个角色，不要出现其他人物、宠物或路人。",
            "- 输出同一角色的三视图设定图：正面、侧面、背面，放在同一张图中。",
            "- 三个视图都必须是完整的从头到脚全身像，头顶与脚底完整入镜；人物整体缩小并居中放置，头顶、双手、脚底四周保留清晰留白。",
            "- 禁止半身像、胸像、近景特写、肖像照或过度放大构图，不能裁切脸部、头发、手臂、腿部、鞋子或脚部。",
            "- 三个视图横向等距排列在同一张画布内，每个视图都必须完整落在画面边界内，不得超出图片外。",
            "- 三个视图必须保持同一张脸、同一发型、同一服装、同一年龄、同一体型、同一配饰。",
            "- 使用标准中性站姿：身体直立、双脚自然站稳、双臂自然下垂或微微离身、双手空置，不做跑、跳、挥手、持物、战斗、表演或剧情动作。",
            "- 只保留角色身上的稳定穿戴配饰；禁止手拿、背负、牵引、互动或携带任何剧情道具、武器、包袋、手机、文件、杯子、伞、花束等物体。",
            "- 画面内不得出现任何文字、标题、标签、箭头、说明、字幕、水印、logo 或排版标注。",
            "- 背景必须是纯白色背景，画面中不得出现灰底、渐变、阴影布景、场景元素或任何其他背景装饰。",
            "- 使用中性站姿、角色设定图、turnaround sheet、model sheet 风格。",
            "- 背景保持纯净简洁，不做剧情场景，不做动作戏，不做复杂道具互动。",
            "- 禁止表情漂移、服装漂移、换脸、换发型、换体型、换镜头叙事。"
        );
    }

    private Map<String, Object> buildCharacterSheetRunRequest(
        StageWorkflowEntity workflow,
        CharacterSheetSlot slot,
        int versionNo,
        String prompt
    ) {
        WorkflowStageGenerationStrategy strategy = stageStrategyResolver.characterSheet(workflow);
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        int[] dimensions = materialGenerationDimensions(VARIANT_KIND_CHARACTER_SHEET, "16:9", "");
        input.put("prompt", composeVisualPrompt(workflow, prompt));
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", VARIANT_KIND_CHARACTER_SHEET);
        Integer keyframeSeed = resolvedKeyframeSeedForImageModel(workflow, slot.syntheticClipIndex(), strategy);
        if (keyframeSeed != null) {
            input.put("seed", keyframeSeed);
        }
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", strategy.modelSection(workflow.getTextAnalysisModel()));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/keyframes",
            "fileStem", "character-" + slot.syntheticClipIndex() + "-sheet-v" + versionNo,
            "requireRemoteSourceUrl", false
        ));
        request.put("metadata", Map.of(
            "relatedWorkflowId", workflow.getWorkflowId(),
            "stage", WorkflowConstants.STAGE_KEYFRAME,
            "clipIndex", slot.syntheticClipIndex(),
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private Map<String, Object> buildKeyframeRunRequest(
        StageWorkflowEntity workflow,
        Map<String, Object> clip,
        int clipIndex,
        int versionNo,
        String prompt,
        String characterConstraintPrompt,
        List<String> continuityReferenceImageUrls,
        List<String> characterReferenceImageUrls,
        String frameRole,
        String fileStem
    ) {
        WorkflowStageGenerationStrategy strategy = stageStrategyResolver.keyframe(workflow);
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        List<String> referenceImageUrls = externallyAccessibleReferenceImageUrls(
            mergeReferenceImageUrls(continuityReferenceImageUrls, characterReferenceImageUrls),
            strategy.supportsImageDataUriReferences()
        );
        String continuityReferenceImageUrl = referenceImageUrls.isEmpty() ? "" : referenceImageUrls.get(0);
        input.put("prompt", composeVisualPrompt(workflow, joinPromptSections(
            characterConstraintPrompt,
            buildKeyframeContinuityPrompt(clip, prompt, continuityReferenceImageUrl, frameRole)
        )));
        int[] dimensions = dimensionsFromAspectRatio(workflow.getAspectRatio());
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", trimmed(frameRole, "first"));
        if (!referenceImageUrls.isEmpty()) {
            input.put("referenceImageUrl", referenceImageUrls.get(0));
            input.put("referenceImageUrls", referenceImageUrls);
        }
        Integer keyframeSeed = resolvedKeyframeSeedForImageModel(workflow, clipIndex, strategy);
        if (keyframeSeed != null) {
            input.put("seed", keyframeSeed);
        }
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", strategy.modelSection(workflow.getTextAnalysisModel()));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/keyframes",
            "fileStem", trimmed(fileStem, "clip" + clipIndex + "-" + trimmed(frameRole, "first") + "-v" + versionNo),
            "requireRemoteSourceUrl", false
        ));
        request.put("metadata", Map.of(
            "relatedWorkflowId", workflow.getWorkflowId(),
            "stage", WorkflowConstants.STAGE_KEYFRAME,
            "clipIndex", clipIndex,
            "frameRole", trimmed(frameRole, "first"),
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private String buildKeyframeContinuityPrompt(
        Map<String, Object> clip,
        String prompt,
        String referenceImageUrl,
        String frameRole
    ) {
        String basePrompt = firstNonBlank(
            prompt,
            stringValue(clip.get("imagePrompt")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("lastFramePrompt")),
            stringValue(clip.get("videoPrompt")),
            stringValue(clip.get("scene"))
        );
        if (!"last".equalsIgnoreCase(trimmed(frameRole, "first")) || isBlank(referenceImageUrl)) {
            return basePrompt;
        }
        List<String> parts = new ArrayList<>();
        parts.add("你现在要生成同一镜头连续动作后的尾帧，必须严格沿用参考图已经确定的同一场景、同一机位体系、同一空间锚点、同一人物外观与服装、同一道具位置关系，禁止跳到另一个房间、另一侧街道或完全不同的构图。");
        parts.add("尾帧只允许在参考首帧基础上推进人物动作状态、视线方向、手部位置或道具使用结果，禁止新增、删除或替换背景布局、门窗桌椅书架等场景元素。");
        String startFramePrompt = firstNonBlank(
            stringValue(clip.get("startFrame")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("imagePrompt"))
        );
        if (!startFramePrompt.isBlank()) {
            parts.add("参考首帧描述：" + startFramePrompt);
            parts.add("场景锁定基准：" + startFramePrompt);
        }
        String sceneAnchor = firstNonBlank(
            stringValue(clip.get("scene")),
            stringValue(clip.get("startFrame")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("endFrame")),
            stringValue(clip.get("lastFramePrompt"))
        );
        if (!sceneAnchor.isBlank()) {
            parts.add("场景锚点：" + sceneAnchor);
        }
        String continuityHint = firstNonBlank(
            stringValue(clip.get("continuityHint")),
            stringValue(clip.get("continuity"))
        );
        if (!continuityHint.isBlank()) {
            parts.add("连续性要求：" + continuityHint);
        }
        if (!basePrompt.isBlank()) {
            parts.add("尾帧目标：" + basePrompt);
        }
        return String.join("\n", parts);
    }

    private Map<String, Object> buildVideoRunRequest(
        StageWorkflowEntity workflow,
        Map<String, Object> clip,
        int clipIndex,
        int versionNo,
        String firstFrameUrl,
        String lastFrameUrl
    ) {
        WorkflowStageGenerationStrategy strategy = stageStrategyResolver.video(workflow);
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        String externallyAccessibleFirstFrameUrl = compatibleVideoFrameUrl(firstFrameUrl, "video firstFrameUrl");
        String externallyAccessibleLastFrameUrl = compatibleVideoFrameUrl(lastFrameUrl, "video lastFrameUrl");
        input.put("prompt", composeVisualPrompt(workflow, joinPromptSections(
            stringValue(clip.get("videoPrompt"))
        )));
        input.put("videoSize", workflow.getVideoSize());
        input.put("durationSeconds", intValue(clip.get("targetDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("minDurationSeconds", intValue(clip.get("minDurationSeconds"), workflow.getMinDurationSeconds()));
        input.put("maxDurationSeconds", intValue(clip.get("maxDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("firstFrameUrl", externallyAccessibleFirstFrameUrl);
        if (!isBlank(externallyAccessibleLastFrameUrl)) {
            input.put("lastFrameUrl", externallyAccessibleLastFrameUrl);
        }
        input.put("generateAudio", true);
        input.put("returnLastFrame", true);
        Integer videoSeed = resolvedVideoSeed(workflow);
        if (videoSeed != null) {
            input.put("seed", videoSeed);
        }
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", strategy.modelSection(workflow.getTextAnalysisModel()));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/videos",
            "fileStem", "clip" + clipIndex + "-v" + versionNo
        ));
        request.put("metadata", Map.of(
            "relatedWorkflowId", workflow.getWorkflowId(),
            "stage", WorkflowConstants.STAGE_VIDEO,
            "clipIndex", clipIndex,
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private MaterialAssetEntity createMaterialAsset(
        StageWorkflowEntity workflow,
        String stageType,
        int clipIndex,
        int versionNo,
        String mediaType,
        String title,
        String fileUrl,
        String previewUrl,
        String mimeType,
        double durationSeconds,
        int width,
        int height,
        boolean hasAudio,
        String remoteTaskId,
        String remoteUrl,
        Map<String, Object> extraMetadata
    ) {
        MaterialAssetEntity asset = new MaterialAssetEntity();
        asset.setMaterialAssetId("asset_" + randomId());
        asset.setOwnerUserId(workflow.getOwnerUserId());
        asset.setTaskId("");
        asset.setWorkflowId(workflow.getWorkflowId());
        asset.setSourceTaskId("");
        asset.setSourceMaterialId("");
        asset.setAssetRole(stageType);
        asset.setStageType(stageType);
        asset.setClipIndex(clipIndex);
        asset.setVersionNo(versionNo);
        asset.setSelectedForNext(0);
        asset.setUserRating(null);
        asset.setRatingNote("");
        asset.setMediaType(mediaType);
        asset.setTitle(title);
        asset.setOriginProvider(resolveOriginProvider(stageType, workflow));
        asset.setOriginModel(resolveOriginModel(stageType, workflow));
        asset.setRemoteTaskId(remoteTaskId);
        asset.setRemoteAssetId("");
        asset.setOriginalFileName(fileNameFromUrl(fileUrl));
        asset.setStoredFileName(fileNameFromUrl(fileUrl));
        asset.setFileExt(fileExt(fileUrl));
        asset.setStorageProvider("local");
        asset.setMimeType(mimeType);
        asset.setSizeBytes(fileSize(fileUrl));
        asset.setSha256("");
        asset.setDurationSeconds(durationSeconds);
        asset.setWidth(width);
        asset.setHeight(height);
        asset.setHasAudio(hasAudio ? 1 : 0);
        asset.setLocalStoragePath(localMediaArtifactService.resolveAbsolutePath(fileUrl));
        asset.setLocalFilePath(localMediaArtifactService.resolveAbsolutePath(fileUrl));
        asset.setPublicUrl(previewUrl);
        asset.setThumbnailUrl("");
        asset.setThirdPartyUrl(remoteUrl);
        asset.setRemoteUrl(remoteUrl);
        asset.setMetadataJson(WorkflowJsonSupport.write(extraMetadata));
        materialAssetThumbnailService.ensureThumbnail(asset);
        asset.setCapturedAt(OffsetDateTime.now(ZoneOffset.UTC));
        asset.setIsDeleted(0);
        return asset;
    }

    private List<Map<String, Object>> buildStoryboardClipPayload(StageWorkflowEntity workflow, String scriptMarkdown) {
        List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = storyboardPlanner.buildStoryboardShotPlans(null, scriptMarkdown);
        List<int[]> durationPlan = storyboardPlanner.buildClipDurationPlan(
            mockWorkflowTask(workflow),
            workflow.getMaxDurationSeconds() == null ? 5 : workflow.getMaxDurationSeconds(),
            shotPlans.size(),
            scriptMarkdown
        );
        List<Map<String, Object>> clips = new ArrayList<>();
        for (int index = 0; index < shotPlans.size(); index++) {
            TaskStoryboardPlanner.StoryboardShotPlan shot = shotPlans.get(index);
            int[] duration = index < durationPlan.size() ? durationPlan.get(index) : new int[] {workflow.getMaxDurationSeconds(), workflow.getMinDurationSeconds(), workflow.getMaxDurationSeconds()};
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("clipIndex", shot.sequentialIndex());
            row.put("shotLabel", shot.shotLabel());
            row.put("scene", shot.scene());
            row.put("startFrame", shot.firstFramePrompt());
            row.put("endFrame", shot.lastFramePrompt());
            row.put("firstFramePrompt", shot.firstFramePrompt());
            row.put("lastFramePrompt", shot.lastFramePrompt());
            row.put("actionPath", buildActionPath(shot.motion(), shot.cameraMovement()));
            row.put("motion", shot.motion());
            row.put("cameraMovement", shot.cameraMovement());
            row.put("durationHint", shot.durationHint());
            row.put("imagePrompt", shot.imagePrompt());
            row.put("videoPrompt", shot.videoPrompt());
            row.put("targetDurationSeconds", duration[0]);
            row.put("minDurationSeconds", duration[1]);
            row.put("maxDurationSeconds", duration[2]);
            clips.add(row);
        }
        return normalizeStoryboardClips(clips);
    }

    private List<Map<String, Object>> normalizeStoryboardClips(List<Map<String, Object>> rawClips) {
        if (rawClips == null || rawClips.isEmpty()) {
            return List.of();
        }
        List<Map<String, Object>> normalized = new ArrayList<>();
        for (int index = 0; index < rawClips.size(); index++) {
            Map<String, Object> raw = rawClips.get(index) == null ? Map.of() : rawClips.get(index);
            Map<String, Object> row = new LinkedHashMap<>(raw);
            Map<String, Object> previous = normalized.isEmpty() ? null : normalized.get(normalized.size() - 1);
            int clipIndex = intValue(raw.get("clipIndex"), index + 1);
            String inheritedStartFrame = previous == null ? "" : firstNonBlank(
                stringValue(previous.get("endFrame")),
                stringValue(previous.get("lastFramePrompt"))
            );
            String startFrame = firstNonBlank(
                inheritedStartFrame,
                stringValue(raw.get("startFrame")),
                stringValue(raw.get("firstFramePrompt")),
                stringValue(raw.get("imagePrompt")),
                stringValue(raw.get("scene"))
            );
            String endFrame = firstNonBlank(
                stringValue(raw.get("endFrame")),
                stringValue(raw.get("lastFramePrompt")),
                stringValue(raw.get("scene"))
            );
            String actionPath = firstNonBlank(
                stringValue(raw.get("actionPath")),
                buildActionPath(stringValue(raw.get("motion")), stringValue(raw.get("cameraMovement"))),
                stringValue(raw.get("motion")),
                stringValue(raw.get("cameraMovement"))
            );
            row.put("clipIndex", clipIndex);
            row.put("shotLabel", firstNonBlank(stringValue(raw.get("shotLabel")), String.valueOf(clipIndex)));
            row.put("startFrame", startFrame);
            row.put("endFrame", endFrame);
            row.put("scene", firstNonBlank(stringValue(raw.get("scene")), startFrame, stringValue(raw.get("firstFramePrompt")), endFrame));
            row.put("firstFramePrompt", firstNonBlank(inheritedStartFrame, stringValue(raw.get("firstFramePrompt")), startFrame));
            row.put("lastFramePrompt", firstNonBlank(stringValue(raw.get("lastFramePrompt")), endFrame));
            row.put("actionPath", actionPath);
            row.put("motion", firstNonBlank(stringValue(raw.get("motion")), actionPath));
            row.put("cameraMovement", stringValue(raw.get("cameraMovement")));
            normalized.add(row);
        }
        for (int index = 0; index < normalized.size(); index++) {
            Map<String, Object> current = normalized.get(index);
            Map<String, Object> next = index + 1 < normalized.size() ? normalized.get(index + 1) : null;
            String continuity = firstNonBlank(
                stringValue(current.get("continuity")),
                stringValue(current.get("continuityHint")),
                stringValue(current.get("visualConsistency")),
                buildContinuityNote(current, next)
            );
            current.put("continuity", continuity);
            current.put("continuityHint", continuity);
            current.put("visualConsistency", firstNonBlank(stringValue(current.get("visualConsistency")), continuity));
            if (next != null) {
                current.put("nextClipIndex", intValue(next.get("clipIndex"), index + 2));
                current.put("nextClipStartFrame", stringValue(next.get("startFrame")));
            }
            Map<String, Object> structured = new LinkedHashMap<>();
            structured.put("startFrame", stringValue(current.get("startFrame")));
            structured.put("endFrame", stringValue(current.get("endFrame")));
            structured.put("actionPath", stringValue(current.get("actionPath")));
            structured.put("continuity", stringValue(current.get("continuity")));
            structured.put("visualConsistency", stringValue(current.get("visualConsistency")));
            current.put("structured", structured);
        }
        return normalized;
    }

    private String buildActionPath(String motion, String cameraMovement) {
        List<String> parts = new ArrayList<>();
        if (!stringValue(cameraMovement).isBlank()) {
            parts.add("运镜：" + stringValue(cameraMovement));
        }
        if (!stringValue(motion).isBlank()) {
            parts.add("动作：" + stringValue(motion));
        }
        return String.join("；", parts);
    }

    private String buildContinuityNote(Map<String, Object> current, Map<String, Object> next) {
        if (next == null) {
            return "当前尾帧作为本段收束画面完成闭环，无下一镜头衔接。";
        }
        return "当前尾帧需与下一镜头首帧衔接，保持主体位置、光影与镜头逻辑连续。";
    }

    private com.jiandou.api.task.TaskRecord mockWorkflowTask(StageWorkflowEntity workflow) {
        com.jiandou.api.task.TaskRecord task = new com.jiandou.api.task.TaskRecord();
        task.setId(workflow.getWorkflowId());
        task.setTitle(workflow.getTitle());
        task.setMinDurationSeconds(workflow.getMinDurationSeconds() == null ? 5 : workflow.getMinDurationSeconds());
        task.setMaxDurationSeconds(workflow.getMaxDurationSeconds() == null ? 5 : workflow.getMaxDurationSeconds());
        task.setTaskSeed(resolvedSharedSeed(workflow));
        return task;
    }

    private Integer resolvedKeyframeSeed(StageWorkflowEntity workflow) {
        return workflow.getKeyframeSeed() != null ? workflow.getKeyframeSeed() : workflow.getTaskSeed();
    }

    private Integer resolvedKeyframeSeed(StageWorkflowEntity workflow, int clipIndex) {
        Integer configured = resolvedKeyframeSeed(workflow);
        if (configured != null) {
            return configured;
        }
        String workflowIdentity = firstNonBlank(
            workflow == null ? "" : workflow.getWorkflowId(),
            workflow == null ? "" : workflow.getTitle(),
            "workflow"
        );
        String seedSource = workflowIdentity + ":clip:" + Math.max(1, clipIndex) + ":keyframe";
        int raw = UUID.nameUUIDFromBytes(seedSource.getBytes(StandardCharsets.UTF_8)).hashCode();
        return Math.floorMod(raw, Integer.MAX_VALUE - 1) + 1;
    }

    private Integer resolvedKeyframeSeedForImageModel(StageWorkflowEntity workflow, int clipIndex) {
        return resolvedKeyframeSeedForImageModel(workflow, clipIndex, stageStrategyResolver.keyframe(workflow));
    }

    private Integer resolvedKeyframeSeedForImageModel(
        StageWorkflowEntity workflow,
        int clipIndex,
        WorkflowStageGenerationStrategy strategy
    ) {
        if (strategy == null || !strategy.supportsSeed()) {
            return null;
        }
        return resolvedKeyframeSeed(workflow, clipIndex);
    }

    private boolean imageModelSupportsSeed(String imageModel) {
        return imageModelSupportsSeed(imageModel, stageStrategyResolver.materialImage(null, imageModel, "image"));
    }

    private boolean imageModelSupportsSeed(String imageModel, WorkflowStageGenerationStrategy strategy) {
        String normalized = trimmed(imageModel, "");
        return !normalized.isBlank() && strategy != null && strategy.supportsSeed();
    }

    private Integer resolvedVideoSeed(StageWorkflowEntity workflow) {
        return workflow.getVideoSeed() != null ? workflow.getVideoSeed() : workflow.getTaskSeed();
    }

    private Integer resolvedSharedSeed(StageWorkflowEntity workflow) {
        return resolvedSharedSeed(resolvedKeyframeSeed(workflow), resolvedVideoSeed(workflow), workflow.getTaskSeed());
    }

    private Integer resolvedSharedSeed(Integer keyframeSeed, Integer videoSeed, Integer legacySeed) {
        if (legacySeed != null) {
            return legacySeed;
        }
        if (keyframeSeed != null && keyframeSeed.equals(videoSeed)) {
            return keyframeSeed;
        }
        return null;
    }

    private String resolveWorkflowClipStartFrameUrl(String workflowId, int clipIndex) {
        if (clipIndex <= 1) {
            return "";
        }
        String previousVideoLastFrameUrl = resolveSelectedVideoLastFrameUrl(workflowId, clipIndex - 1);
        if (!previousVideoLastFrameUrl.isBlank()) {
            return previousVideoLastFrameUrl;
        }
        return resolveSelectedKeyframeEndFrameUrl(workflowId, clipIndex - 1);
    }

    private String resolveWorkflowVideoFirstFrameUrl(String workflowId, int clipIndex, StageVersionEntity keyframeVersion) {
        String continuityFrameUrl = resolveWorkflowClipStartFrameUrl(workflowId, clipIndex);
        if (!continuityFrameUrl.isBlank()) {
            return continuityFrameUrl;
        }
        return firstNonBlank(
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "first", true),
            resolveKeyframeFrameUrl(keyframeVersion, "first", true),
            resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "first", false),
            resolveKeyframeFrameUrl(keyframeVersion, "first", false)
        );
    }

    private String resolveWorkflowVideoLastFrameUrl(StageVersionEntity keyframeVersion) {
        return firstNonBlank(
            resolveSelectedKeyframeFrameUrl(keyframeVersion.getWorkflowId(), intValue(keyframeVersion.getClipIndex(), 0), "last", true),
            resolveKeyframeFrameUrl(keyframeVersion, "last", true),
            resolveSelectedKeyframeFrameUrl(keyframeVersion.getWorkflowId(), intValue(keyframeVersion.getClipIndex(), 0), "last", false),
            resolveKeyframeFrameUrl(keyframeVersion, "last", false)
        );
    }

    private String resolveSelectedVideoLastFrameUrl(String workflowId, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType())
                && intValue(item.getClipIndex(), 0) == clipIndex
                && intValue(item.getSelected(), 0) == 1)
            .findFirst()
            .map(version -> firstNonBlank(
                stringValue(stageOutputSummary(version).get("lastFrameUrl")),
                stringValue(stageOutputSummary(version).get("requestedLastFrameUrl")),
                stringValue(stageOutputSummary(version).get("firstFrameUrl"))
            ))
            .orElse("");
    }

    private String resolveWorkflowClipStartFrameRemoteUrl(String workflowId, int clipIndex) {
        String previousVideoLastFrameUrl = resolveSelectedVideoLastFrameUrl(workflowId, clipIndex - 1);
        if (!previousVideoLastFrameUrl.isBlank()) {
            return previousVideoLastFrameUrl;
        }
        return resolveSelectedKeyframeEndFrameRemoteUrl(workflowId, clipIndex - 1);
    }

    private String resolveSelectedKeyframeEndFrameUrl(String workflowId, int clipIndex) {
        return resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "last", false);
    }

    private String resolveSelectedKeyframeEndFrameRemoteUrl(String workflowId, int clipIndex) {
        return resolveSelectedKeyframeFrameUrl(workflowId, clipIndex, "last", true);
    }

    private String resolveSelectedKeyframeFrameUrl(String workflowId, int clipIndex, String frameRole, boolean preferRemote) {
        StageVersionEntity version = selectedKeyframeFrameVersion(workflowId, clipIndex, frameRole);
        return version == null ? "" : resolveKeyframeFrameUrl(version, frameRole, preferRemote);
    }

    private StageVersionEntity selectedKeyframeFrameVersion(String workflowId, int clipIndex, String frameRole) {
        String key = selectionKey(frameRole);
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())
                && intValue(item.getClipIndex(), 0) == clipIndex
                && !VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
            .toList();
        return versions.stream()
            .filter(item -> boolValue(stageOutputSummary(item).get(key)))
            .findFirst()
            .or(() -> versions.stream().filter(item -> intValue(item.getSelected(), 0) == 1).findFirst())
            .orElse(null);
    }

    private String resolveKeyframeFrameUrl(StageVersionEntity version, String frameRole, boolean preferRemote) {
        if (version == null) {
            return "";
        }
        Map<String, Object> outputSummary = stageOutputSummary(version);
        if ("first".equals(normalizeFrameRole(frameRole))) {
            return preferRemote
                ? firstNonBlank(
                    stringValue(outputSummary.get("startFrameRemoteUrl")),
                    stringValue(outputSummary.get("firstFrameRemoteUrl")),
                    resolveGeneratedFrameRemoteUrl(version, "first"),
                    stringValue(outputSummary.get("startFrameUrl")),
                    stringValue(outputSummary.get("firstFrameUrl")),
                    stringValue(outputSummary.get("fileUrl")),
                    version.getDownloadUrl()
                )
                : firstNonBlank(
                    stringValue(outputSummary.get("startFrameUrl")),
                    stringValue(outputSummary.get("firstFrameUrl")),
                    stringValue(outputSummary.get("fileUrl")),
                    version.getDownloadUrl()
                );
        }
        return preferRemote
            ? firstNonBlank(
                stringValue(outputSummary.get("endFrameRemoteUrl")),
                stringValue(outputSummary.get("lastFrameRemoteUrl")),
                resolveGeneratedFrameRemoteUrl(version, "last"),
                resolveStageAssetRemoteUrl(version),
                stringValue(outputSummary.get("endFrameUrl")),
                stringValue(outputSummary.get("lastFrameUrl")),
                stringValue(outputSummary.get("fileUrl")),
                version.getDownloadUrl()
            )
            : firstNonBlank(
                stringValue(outputSummary.get("endFrameUrl")),
                stringValue(outputSummary.get("lastFrameUrl")),
                stringValue(outputSummary.get("fileUrl")),
                version.getDownloadUrl()
            );
    }

    private String resolveKeyframeFrameUrlForView(StageVersionEntity version, String frameRole, boolean preferRemote) {
        if (version == null) {
            return "";
        }
        Map<String, Object> outputSummary = stageOutputSummaryForView(version);
        if ("first".equals(normalizeFrameRole(frameRole))) {
            return preferRemote
                ? firstNonBlank(stringValue(outputSummary.get("startFrameRemoteUrl")), stringValue(outputSummary.get("firstFrameRemoteUrl")), stringValue(outputSummary.get("startFrameUrl")), stringValue(outputSummary.get("firstFrameUrl")))
                : firstNonBlank(stringValue(outputSummary.get("startFrameUrl")), stringValue(outputSummary.get("firstFrameUrl")));
        }
        return preferRemote
            ? firstNonBlank(stringValue(outputSummary.get("endFrameRemoteUrl")), stringValue(outputSummary.get("lastFrameRemoteUrl")), stringValue(outputSummary.get("endFrameUrl")), stringValue(outputSummary.get("lastFrameUrl")), stringValue(outputSummary.get("fileUrl")))
            : firstNonBlank(stringValue(outputSummary.get("endFrameUrl")), stringValue(outputSummary.get("lastFrameUrl")), stringValue(outputSummary.get("fileUrl")));
    }

    private void markSelectedKeyframeFrame(String workflowId, int clipIndex, String versionId, String frameRole) {
        String key = selectionKey(frameRole);
        for (StageVersionEntity item : workflowRepository.listStageVersions(workflowId)) {
            if (!WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())
                || intValue(item.getClipIndex(), 0) != clipIndex
                || VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item))) {
                continue;
            }
            Map<String, Object> outputSummary = new LinkedHashMap<>(stageOutputSummary(item));
            outputSummary.remove(key);
            if (item.getStageVersionId().equals(versionId)) {
                outputSummary.put(key, true);
            }
            item.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
            workflowRepository.saveStageVersion(item);
        }
    }

    private String selectionKey(String frameRole) {
        return "first".equals(normalizeFrameRole(frameRole)) ? "selectedFirstFrame" : "selectedLastFrame";
    }

    private String resolveGeneratedFrameRemoteUrl(StageVersionEntity version, String frameRole) {
        Map<String, Object> outputSummary = stageOutputSummary(version);
        for (Map<String, Object> frame : listMapValue(outputSummary.get("generatedFrames"))) {
            if (normalizeFrameRole(stringValue(frame.get("frameRole"))).equals(normalizeFrameRole(frameRole))) {
                String remoteUrl = stringValue(frame.get("remoteUrl"));
                if (!remoteUrl.isBlank()) {
                    return remoteUrl;
                }
            }
        }
        Map<String, Object> modelCallSummary = version == null ? Map.of() : WorkflowJsonSupport.readMap(version.getModelCallSummaryJson());
        String runId = "first".equals(normalizeFrameRole(frameRole))
            ? stringValue(modelCallSummary.get("startFrameRunId"))
            : stringValue(modelCallSummary.get("endFrameRunId"));
        return resolveRunRemoteSourceUrl(runId);
    }

    private String resolveStageAssetRemoteUrl(StageVersionEntity version) {
        if (version == null || isBlank(version.getMaterialAssetId())) {
            return "";
        }
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(version.getMaterialAssetId(), requiredUserId());
        return asset == null ? "" : stringValue(asset.getRemoteUrl());
    }

    private String resolveRunRemoteSourceUrl(String runId) {
        if (isBlank(runId)) {
            return "";
        }
        try {
            Map<String, Object> run = generationApplicationService.getRun(runId);
            Map<String, Object> result = mapValue(run.get("result"));
            Map<String, Object> metadata = mapValue(result.get("metadata"));
            return stringValue(metadata.get("remoteSourceUrl"));
        } catch (RuntimeException ignored) {
            return "";
        }
    }

    private Map<String, Object> stageOutputSummary(StageVersionEntity version) {
        return version == null ? Map.of() : WorkflowJsonSupport.readMap(version.getOutputSummaryJson());
    }

    private Map<String, Object> stageOutputSummaryForView(StageVersionEntity version) {
        Map<String, Object> summary = new LinkedHashMap<>(stageOutputSummary(version));
        if (version == null
            || !WorkflowConstants.STAGE_KEYFRAME.equals(version.getStageType())
            || intValue(version.getClipIndex(), 0) <= 1
            || VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(version))) {
            return summary;
        }
        String workflowId = stringValue(version.getWorkflowId());
        int clipIndex = intValue(version.getClipIndex(), 0);
        String continuityStartFrameUrl = resolveWorkflowClipStartFrameUrl(workflowId, clipIndex);
        String continuityStartFrameRemoteUrl = resolveWorkflowClipStartFrameRemoteUrl(workflowId, clipIndex);
        if (continuityStartFrameUrl.isBlank()) {
            return summary;
        }
        summary.put("startFrameUrl", continuityStartFrameUrl);
        summary.put("firstFrameUrl", continuityStartFrameUrl);
        if (!continuityStartFrameRemoteUrl.isBlank()) {
            summary.put("startFrameRemoteUrl", continuityStartFrameRemoteUrl);
            summary.put("firstFrameRemoteUrl", continuityStartFrameRemoteUrl);
        }
        List<Map<String, Object>> frames = new ArrayList<>(listMapValue(summary.get("generatedFrames")));
        if (frames.isEmpty()) {
            Map<String, Object> firstFrame = new LinkedHashMap<>();
            firstFrame.put("frameRole", "first");
            firstFrame.put("fileUrl", continuityStartFrameUrl);
            if (!continuityStartFrameRemoteUrl.isBlank()) {
                firstFrame.put("remoteUrl", continuityStartFrameRemoteUrl);
            }
            frames.add(firstFrame);
        } else {
            boolean updated = false;
            for (Map<String, Object> frame : frames) {
                if ("first".equals(normalizeFrameRole(stringValue(frame.get("frameRole"))))) {
                    frame.put("fileUrl", continuityStartFrameUrl);
                    if (!continuityStartFrameRemoteUrl.isBlank()) {
                        frame.put("remoteUrl", continuityStartFrameRemoteUrl);
                    }
                    updated = true;
                    break;
                }
            }
            if (!updated) {
                Map<String, Object> firstFrame = new LinkedHashMap<>();
                firstFrame.put("frameRole", "first");
                firstFrame.put("fileUrl", continuityStartFrameUrl);
                if (!continuityStartFrameRemoteUrl.isBlank()) {
                    firstFrame.put("remoteUrl", continuityStartFrameRemoteUrl);
                }
                frames.add(0, firstFrame);
            }
        }
        summary.put("generatedFrames", frames);
        summary.put("continuityResolvedFromCurrentSelection", true);
        return summary;
    }

    private Map<String, Object> stageInputSummary(StageVersionEntity version) {
        return version == null ? Map.of() : WorkflowJsonSupport.readMap(version.getInputSummaryJson());
    }

    private String stageVariantKind(StageVersionEntity version) {
        return firstNonBlank(
            stringValue(stageInputSummary(version).get("variantKind")),
            stringValue(stageOutputSummary(version).get("variantKind"))
        );
    }

    private boolean isCharacterSheetClipIndex(int clipIndex) {
        return clipIndex >= CHARACTER_SHEET_CLIP_INDEX_BASE;
    }

    private String extractGenerationFileUrl(Map<String, Object> result) {
        return firstNonBlank(
            stringValue(result.get("outputUrl")),
            stringValue(mapValue(result.get("metadata")).get("fileUrl"))
        );
    }

    private Map<String, Object> keyframeAssetMetadata(
        Map<String, Object> clip,
        Map<String, Object> endFrameRun,
        Map<String, Object> startFrameRun,
        String startFrameUrl,
        String startFrameRemoteUrl,
        String endFrameUrl,
        String endFrameRemoteUrl,
        String continuitySource
    ) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("clip", clip);
        metadata.put("frameRole", "last");
        metadata.put("runId", stringValue(endFrameRun.get("id")));
        metadata.put("startFrameRunId", stringValue(startFrameRun.get("id")));
        metadata.put("endFrameRunId", stringValue(endFrameRun.get("id")));
        metadata.put("startFrameUrl", startFrameUrl);
        metadata.put("firstFrameUrl", startFrameUrl);
        metadata.put("startFrameRemoteUrl", startFrameRemoteUrl);
        metadata.put("firstFrameRemoteUrl", startFrameRemoteUrl);
        metadata.put("endFrameUrl", endFrameUrl);
        metadata.put("lastFrameUrl", endFrameUrl);
        metadata.put("endFrameRemoteUrl", endFrameRemoteUrl);
        metadata.put("lastFrameRemoteUrl", endFrameRemoteUrl);
        metadata.put("continuitySource", continuitySource);
        return metadata;
    }

    private FrameGenerationResult generateKeyframeFrameSafely(
        StageWorkflowEntity workflow,
        int clipIndex,
        int versionNo,
        String frameRole,
        Map<String, Object> request,
        Map<String, Object> context
    ) {
        try {
            Map<String, Object> run = createLoggedGenerationRun(
                workflow,
                WorkflowConstants.STAGE_KEYFRAME,
                "workflow.keyframe.generate",
                request,
                context
            );
            Map<String, Object> result = mapValue(run.get("result"));
            String fileUrl = extractGenerationFileUrl(result);
            if (fileUrl.isBlank()) {
                return FrameGenerationResult.failure(frameRole, frameLabel(frameRole) + "关键帧生成结果为空");
            }
            return FrameGenerationResult.success(frameRole, run, result, fileUrl, resolveGeneratedMediaRemoteUrl(result));
        } catch (Exception ex) {
            return FrameGenerationResult.failure(frameRole, firstNonBlank(ex.getMessage(), frameLabel(frameRole) + "关键帧生成失败"));
        }
    }

    private List<String> frameFailureMessages(FrameGenerationResult... frames) {
        List<String> messages = new ArrayList<>();
        for (FrameGenerationResult frame : frames) {
            if (frame != null && !frame.available() && !frame.errorMessage().isBlank()) {
                messages.add(frameLabel(frame.frameRole()) + "失败：" + frame.errorMessage());
            }
        }
        return messages.isEmpty() ? List.of("关键帧生成失败") : messages;
    }

    private List<Map<String, Object>> frameFailures(FrameGenerationResult... frames) {
        List<Map<String, Object>> failures = new ArrayList<>();
        for (FrameGenerationResult frame : frames) {
            if (frame == null || frame.available() || frame.errorMessage().isBlank()) {
                continue;
            }
            Map<String, Object> failure = new LinkedHashMap<>();
            failure.put("frameRole", normalizeFrameRole(frame.frameRole()));
            failure.put("label", frameLabel(frame.frameRole()));
            failure.put("errorMessage", frame.errorMessage());
            failures.add(failure);
        }
        return failures;
    }

    private String frameLabel(String frameRole) {
        return "last".equals(normalizeFrameRole(frameRole)) ? "尾帧" : "首帧";
    }

    private List<Map<String, Object>> generatedKeyframeFrames(
        Map<String, Object> startFrameRun,
        Map<String, Object> startFrameResult,
        Map<String, Object> endFrameRun,
        Map<String, Object> endFrameResult,
        String startFrameUrl,
        String startFrameRemoteUrl,
        String endFrameUrl,
        String endFrameRemoteUrl
    ) {
        List<Map<String, Object>> frames = new ArrayList<>();
        if (!startFrameUrl.isBlank()) {
            Map<String, Object> first = new LinkedHashMap<>();
            first.put("frameRole", "first");
            first.put("runId", stringValue(startFrameRun.get("id")));
            first.put("fileUrl", startFrameUrl);
            first.put("remoteUrl", startFrameRemoteUrl);
            first.put("modelInfo", mapValue(startFrameResult.get("modelInfo")));
            frames.add(first);
        }
        if (!endFrameUrl.isBlank()) {
            Map<String, Object> last = new LinkedHashMap<>();
            last.put("frameRole", "last");
            last.put("runId", stringValue(endFrameRun.get("id")));
            last.put("fileUrl", endFrameUrl);
            last.put("remoteUrl", endFrameRemoteUrl);
            last.put("modelInfo", mapValue(endFrameResult.get("modelInfo")));
            frames.add(last);
        }
        return frames;
    }

    private record FrameGenerationResult(
        String frameRole,
        Map<String, Object> run,
        Map<String, Object> result,
        String fileUrl,
        String remoteUrl,
        String errorMessage
    ) {
        static FrameGenerationResult success(String frameRole, Map<String, Object> run, Map<String, Object> result, String fileUrl, String remoteUrl) {
            return new FrameGenerationResult(frameRole, run, result, fileUrl, remoteUrl, "");
        }

        static FrameGenerationResult reused(String frameRole, String fileUrl, String remoteUrl) {
            return new FrameGenerationResult(frameRole, Map.of(), Map.of(), fileUrl, remoteUrl, "");
        }

        static FrameGenerationResult failure(String frameRole, String errorMessage) {
            return new FrameGenerationResult(frameRole, Map.of(), Map.of(), "", "", errorMessage == null ? "" : errorMessage);
        }

        boolean available() {
            return !fileUrl.isBlank();
        }
    }

    private Map<String, Object> videoAssetMetadata(
        Map<String, Object> clip,
        Map<String, Object> run,
        Map<String, Object> metadata,
        String firstFrameUrl,
        String requestedLastFrameUrl,
        String resolvedLastFrameUrl
    ) {
        Map<String, Object> assetMetadata = new LinkedHashMap<>();
        assetMetadata.put("clip", clip);
        assetMetadata.put("runId", stringValue(run.get("id")));
        assetMetadata.put("firstFrameUrl", firstNonBlank(stringValue(metadata.get("firstFrameUrl")), firstFrameUrl));
        assetMetadata.put("requestedLastFrameUrl", firstNonBlank(stringValue(metadata.get("requestedLastFrameUrl")), requestedLastFrameUrl));
        assetMetadata.put("lastFrameUrl", resolvedLastFrameUrl);
        return assetMetadata;
    }

    private Map<String, Object> characterSheetAssetMetadata(
        CharacterSheetSlot slot,
        Map<String, Object> run,
        String fileUrl
    ) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        Map<String, Object> result = mapValue(run.get("result"));
        String remoteSourceUrl = resolveGeneratedMediaRemoteUrl(result);
        metadata.put("assetType", VARIANT_KIND_CHARACTER_SHEET);
        metadata.put("variantKind", VARIANT_KIND_CHARACTER_SHEET);
        metadata.put("characterName", slot.characterName());
        metadata.put("characterAppearance", slot.characterAppearance());
        metadata.put("runId", stringValue(run.get("id")));
        metadata.put("remoteSourceUrl", remoteSourceUrl);
        metadata.put("sheetUrl", fileUrl);
        metadata.put("fileUrl", fileUrl);
        return metadata;
    }

    private List<CharacterSheetSlot> matchedCharacterSheetSlots(StageVersionEntity storyboardVersion, Map<String, Object> clip) {
        List<CharacterSheetSlot> slots = characterSheetSlots(storyboardVersion);
        if (slots.isEmpty()) {
            return List.of();
        }
        String corpus = buildClipCharacterMatchCorpus(clip);
        if (corpus.isBlank()) {
            return List.of();
        }
        List<CharacterSheetSlot> matches = new ArrayList<>();
        for (CharacterSheetSlot slot : slots) {
            String characterName = trimmed(slot.characterName(), "");
            if (!characterName.isBlank() && corpus.contains(characterName)) {
                matches.add(slot);
            }
        }
        return matches;
    }

    private String buildClipCharacterMatchCorpus(Map<String, Object> clip) {
        if (clip == null || clip.isEmpty()) {
            return "";
        }
        return String.join(
            "\n",
            stringValue(clip.get("scene")),
            stringValue(clip.get("startFrame")),
            stringValue(clip.get("endFrame")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("lastFramePrompt")),
            stringValue(clip.get("actionPath")),
            stringValue(clip.get("motion")),
            stringValue(clip.get("videoPrompt"))
        );
    }

    private String buildCharacterConsistencyPrompt(List<CharacterReference> characterReferences) {
        if (characterReferences == null || characterReferences.isEmpty()) {
            return "";
        }
        List<String> parts = new ArrayList<>();
        parts.add("角色一致性绑定：");
        boolean hasCharacterReferenceImages = false;
        for (CharacterReference reference : characterReferences) {
            if (!reference.imageUrl().isBlank()) {
                hasCharacterReferenceImages = true;
            }
            parts.add("- " + reference.characterName() + "：" + firstNonBlank(reference.referenceAppearance(), reference.fallbackAppearance()));
        }
        if (hasCharacterReferenceImages) {
            parts.add("已附带当前选中的角色三视图参考图；脸型、五官、发型、服装、体型、年龄感、配饰必须以选中三视图为唯一准绳，不得回退到旧版本或自行重设计。");
        }
        parts.add("若镜头中出现上述角色，必须严格沿用对应外观锚点，禁止换脸、换发型、换服装、换年龄感。");
        return String.join("\n", parts);
    }

    private List<CharacterReference> resolveCharacterReferences(
        String workflowId,
        StageVersionEntity storyboardVersion,
        List<CharacterSheetSlot> matchedCharacterSlots
    ) {
        if (matchedCharacterSlots == null || matchedCharacterSlots.isEmpty()) {
            return List.of();
        }
        List<StageVersionEntity> stageVersions = workflowRepository.listStageVersions(workflowId);
        List<CharacterReference> references = new ArrayList<>();
        for (CharacterSheetSlot slot : matchedCharacterSlots) {
            StageVersionEntity selectedSheet = stageVersions.stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()))
                .filter(item -> intValue(item.getClipIndex(), 0) == slot.syntheticClipIndex())
                .filter(item -> intValue(item.getSelected(), 0) == 1)
                .filter(item -> storyboardVersion.getStageVersionId().equals(trimmed(item.getParentVersionId(), "")))
                .filter(item -> VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)))
                .findFirst()
                .orElse(null);
            String url = resolveCharacterSheetReferenceUrl(selectedSheet);
            references.add(new CharacterReference(
                slot.characterName(),
                firstNonBlank(slot.characterAppearance(), slot.characterDefinition()),
                resolveCharacterSheetAppearance(selectedSheet, slot),
                url
            ));
        }
        return references;
    }

    private String resolveCharacterSheetAppearance(StageVersionEntity version, CharacterSheetSlot slot) {
        if (version == null) {
            return "";
        }
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(version.getMaterialAssetId(), requiredUserId());
        Map<String, Object> assetMetadata = asset == null ? Map.of() : WorkflowJsonSupport.readMap(asset.getMetadataJson());
        Map<String, Object> outputSummary = stageOutputSummary(version);
        Map<String, Object> inputSummary = stageInputSummary(version);
        String assetDescription = firstNonBlank(
            stringValue(assetMetadata.get("description")),
            stringValue(assetMetadata.get("shapedPrompt")),
            stringValue(assetMetadata.get("prompt")),
            ""
        );
        String selectedSheetDescription = firstNonBlank(
            assetDescription,
            stringValue(outputSummary.get("characterAppearance")),
            stringValue(inputSummary.get("characterAppearance")),
            slot.characterAppearance(),
            slot.characterDefinition()
        );
        if (assetDescription.isBlank()) {
            return selectedSheetDescription;
        }
        return "以当前选中的三视图素材为准：" + selectedSheetDescription;
    }

    private String resolveCharacterSheetReferenceUrl(StageVersionEntity version) {
        if (version == null) {
            return "";
        }
        Map<String, Object> outputSummary = stageOutputSummary(version);
        return firstNonBlank(
            stringValue(outputSummary.get("remoteSourceUrl")),
            resolveStageAssetRemoteUrl(version),
            stringValue(outputSummary.get("sheetUrl")),
            stringValue(outputSummary.get("previewUrl")),
            stringValue(outputSummary.get("fileUrl")),
            stringValue(stageInputSummary(version).get("remoteSourceUrl")),
            trimmed(version.getPreviewUrl(), ""),
            trimmed(version.getDownloadUrl(), "")
        );
    }

    private List<String> mergeReferenceImageUrls(List<String> continuityReferenceImageUrls, List<String> characterReferenceImageUrls) {
        LinkedHashSet<String> urls = new LinkedHashSet<>();
        addReferenceImageUrls(urls, continuityReferenceImageUrls);
        addReferenceImageUrls(urls, characterReferenceImageUrls);
        return List.copyOf(urls);
    }

    private void addReferenceImageUrls(LinkedHashSet<String> collector, List<String> referenceImageUrls) {
        if (collector == null || referenceImageUrls == null) {
            return;
        }
        for (String url : referenceImageUrls) {
            if (url != null && !url.isBlank()) {
                collector.add(url.trim());
            }
        }
    }

    private Map<String, Object> toCharacterMatchRow(CharacterSheetSlot slot) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("characterName", slot.characterName());
        row.put("displayName", slot.characterName());
        row.put("appearanceSummary", slot.characterAppearance());
        row.put("appearance", slot.characterAppearance());
        row.put("syntheticClipIndex", slot.syntheticClipIndex());
        row.put("clipIndex", slot.syntheticClipIndex());
        return row;
    }

    private CharacterSheetSlot resolveCharacterSheetSlot(StageVersionEntity storyboardVersion, int clipIndex) {
        if (!isCharacterSheetClipIndex(clipIndex)) {
            return null;
        }
        return characterSheetSlots(storyboardVersion).stream()
            .filter(item -> item.syntheticClipIndex() == clipIndex)
            .findFirst()
            .orElseThrow(() -> badRequest("workflow_character_sheet_not_found", "未找到角色三视图槽位 #" + clipIndex));
    }

    private List<CharacterSheetSlot> characterSheetSlots(StageVersionEntity storyboardVersion) {
        String storyboardMarkdown = stringValue(stageOutputSummary(storyboardVersion).get("scriptMarkdown"));
        List<TaskStoryboardPlanner.CharacterDefinition> characterDefinitions = storyboardPlanner.extractCharacterDefinitions(storyboardMarkdown);
        List<CharacterSheetSlot> slots = new ArrayList<>();
        for (int index = 0; index < characterDefinitions.size(); index++) {
            TaskStoryboardPlanner.CharacterDefinition definition = characterDefinitions.get(index);
            slots.add(new CharacterSheetSlot(
                definition.name(),
                definition.appearance(),
                definition.definition(),
                CHARACTER_SHEET_CLIP_INDEX_BASE + index + 1
            ));
        }
        return slots;
    }

    private boolean hasCharacterSheetVersionForStoryboard(String workflowId, String storyboardVersionId, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .anyMatch(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())
                && intValue(item.getClipIndex(), 0) == clipIndex
                && storyboardVersionId.equals(trimmed(item.getParentVersionId(), ""))
                && VARIANT_KIND_CHARACTER_SHEET.equals(stageVariantKind(item)));
    }

    private StageWorkflowEntity requireWorkflow(String workflowId) {
        StageWorkflowEntity workflow = workflowRepository.findWorkflow(workflowId, requiredUserId());
        if (workflow == null) {
            throw notFound("workflow_not_found", "工作流不存在");
        }
        return workflow;
    }

    private StageVersionEntity requireStageVersion(String workflowId, String versionId, String expectedStageType) {
        StageVersionEntity version = workflowRepository.findStageVersion(workflowId, versionId);
        if (version == null) {
            throw notFound("stage_version_not_found", "阶段版本不存在");
        }
        if (!expectedStageType.isBlank() && !expectedStageType.equals(version.getStageType())) {
            throw badRequest("stage_version_type_mismatch", "阶段版本类型不匹配");
        }
        return version;
    }

    private StageVersionEntity requireSelectedStoryboard(StageWorkflowEntity workflow) {
        if (workflow.getSelectedStoryboardVersionId() == null || workflow.getSelectedStoryboardVersionId().isBlank()) {
            throw badRequest("workflow_storyboard_not_selected", "请先选中一个分镜版本");
        }
        return requireStageVersion(workflow.getWorkflowId(), workflow.getSelectedStoryboardVersionId(), WorkflowConstants.STAGE_STORYBOARD);
    }

    private StageVersionEntity requireSelectedStageVersion(String workflowId, String stageType, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> stageType.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex && intValue(item.getSelected(), 0) == 1)
            .findFirst()
            .orElseThrow(() -> badRequest("workflow_stage_not_selected", "镜头 #" + clipIndex + " 还没有选中的" + stageLabel(stageType) + "版本"));
    }

    private MaterialAssetEntity requireMaterialAsset(String assetId) {
        MaterialAssetEntity asset = workflowRepository.findMaterialAsset(assetId, requiredUserId());
        if (asset == null) {
            throw notFound("material_asset_not_found", "素材不存在");
        }
        return asset;
    }

    private Map<String, Object> requireStoryboardClip(StageVersionEntity storyboardVersion, int clipIndex) {
        return readClips(storyboardVersion).stream()
            .filter(item -> intValue(item.get("clipIndex"), 0) == clipIndex)
            .findFirst()
            .orElseThrow(() -> badRequest("workflow_clip_not_found", "未找到镜头 #" + clipIndex));
    }

    private List<Map<String, Object>> readClips(StageVersionEntity storyboardVersion) {
        return normalizeStoryboardClips(listMapValue(WorkflowJsonSupport.readMap(storyboardVersion.getOutputSummaryJson()).get("clips")));
    }

    private boolean hasNoSelectedVersion(String workflowId, String stageType, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .noneMatch(item -> stageType.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex && intValue(item.getSelected(), 0) == 1);
    }

    private Map<String, MaterialAssetEntity> loadAssetMap(List<StageVersionEntity> versions, String finalJoinAssetId, Long ownerUserId) {
        Set<String> assetIds = versions.stream()
            .map(StageVersionEntity::getMaterialAssetId)
            .filter(item -> item != null && !item.isBlank())
            .collect(Collectors.toCollection(LinkedHashSet::new));
        if (finalJoinAssetId != null && !finalJoinAssetId.isBlank()) {
            assetIds.add(finalJoinAssetId);
        }
        return workflowRepository.findMaterialAssetsByIds(assetIds, ownerUserId);
    }

    private Map<String, Object> awaitCompletedVideoRun(Map<String, Object> initialRun) {
        String currentStatus = normalizedRunStatus(initialRun);
        if (!isVideoRunActive(currentStatus)) {
            assertVideoRunSucceeded(initialRun, currentStatus);
            return initialRun;
        }
        String runId = stringValue(initialRun.get("id"));
        if (runId.isBlank()) {
            throw badRequest("video_run_missing_id", "视频运行标识缺失");
        }
        Map<String, Object> currentRun = initialRun;
        for (int poll = 0; poll < VIDEO_RUN_MAX_POLLS; poll++) {
            currentRun = generationApplicationService.getRun(runId);
            currentStatus = normalizedRunStatus(currentRun);
            if (!isVideoRunActive(currentStatus)) {
                assertVideoRunSucceeded(currentRun, currentStatus);
                return currentRun;
            }
            try {
                Thread.sleep(VIDEO_RUN_POLL_INTERVAL_MILLIS);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("video run wait interrupted", ex);
            }
        }
        throw badRequest("video_run_timeout", "视频生成等待超时，请稍后重试");
    }

    private boolean isVideoRunActive(String status) {
        return GenerationRunStatuses.isActive(status);
    }

    private void assertVideoRunSucceeded(Map<String, Object> run, String status) {
        if (GenerationRunStatuses.SUCCEEDED.equalsIgnoreCase(status)) {
            return;
        }
        String message = stringValue(mapValue(run.get("result")).get("error"));
        if (message.isBlank()) {
            message = "视频生成失败";
        }
        throw new GenerationProviderException(
            message,
            providerRequestFromRun(run),
            run,
            200
        );
    }

    private String normalizedRunStatus(Map<String, Object> run) {
        return stringValue(run.get("status")).toLowerCase(Locale.ROOT);
    }

    private record LoggedGenerationRun(String modelCallId, OffsetDateTime startedAt, Map<String, Object> run) {
    }

    private void validateCreateWorkflowRequest(CreateWorkflowRequest request) {
        if (request == null) {
            throw badRequest("workflow_request_invalid", "工作流请求不能为空");
        }
        requireNonBlank(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireNonBlank(request.imageModel(), "imageModel", "关键帧模型");
        requireNonBlank(request.videoModel(), "videoModel", "视频模型");
        validateDurationMode(request.durationMode(), request.minDurationSeconds(), request.maxDurationSeconds());
    }

    private void validateWorkflowSettingsRequest(UpdateWorkflowSettingsRequest request) {
        requireNonBlank(request.aspectRatio(), "aspectRatio", "画幅比例");
        requireNonBlank(request.stylePreset(), "stylePreset", "风格预设");
        requireNonBlank(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireNonBlank(request.imageModel(), "imageModel", "关键帧模型");
        requireNonBlank(request.videoModel(), "videoModel", "视频模型");
        requireNonBlank(request.videoSize(), "videoSize", "视频尺寸");
        validateDurationMode(request.durationMode(), request.minDurationSeconds(), request.maxDurationSeconds());
    }

    private void validateDurationMode(String durationMode, Integer minDurationSeconds, Integer maxDurationSeconds) {
        String normalized = trimmed(durationMode, "auto").toLowerCase(Locale.ROOT);
        if (!"auto".equals(normalized) && !"manual".equals(normalized)) {
            throw badRequest("workflow_duration_mode_invalid", "镜头时长模式必须是 auto 或 manual");
        }
        if ("manual".equals(normalized) && (minDurationSeconds == null || maxDurationSeconds == null)) {
            throw badRequest("workflow_duration_required", "手动时长模式必须填写最小时长和最大时长");
        }
    }

    private String normalizeDurationMode(String durationMode, Integer minDurationSeconds, Integer maxDurationSeconds) {
        String normalized = trimmed(durationMode, "").toLowerCase(Locale.ROOT);
        if ("manual".equals(normalized)) {
            return "manual";
        }
        if ("auto".equals(normalized)) {
            return "auto";
        }
        return minDurationSeconds == null && maxDurationSeconds == null ? "auto" : "manual";
    }

    private String workflowDurationMode(StageWorkflowEntity workflow) {
        String normalized = trimmed(workflow == null ? "" : workflow.getDurationMode(), "").toLowerCase(Locale.ROOT);
        if ("manual".equals(normalized) || "auto".equals(normalized)) {
            return normalized;
        }
        return "auto";
    }

    private void requireNonBlank(String value, String field, String label) {
        if (value == null || value.trim().isEmpty()) {
            throw badRequest("workflow_field_missing", label + "不能为空: " + field);
        }
    }

    private int normalizeRating(Integer value) {
        if (value == null || value < 1 || value > 5) {
            throw badRequest("invalid_rating", "评分必须在 1 到 5 之间");
        }
        return value;
    }

    private String normalizeRatingNote(String value) {
        String note = trimmed(value, "");
        if (note.length() > 1000) {
            throw badRequest("invalid_rating_note", "评分备注不能超过 1000 个字符");
        }
        return note;
    }

    private Long requiredUserId() {
        return SecurityCurrentUser.requireCurrentUserId();
    }

    private ApiException badRequest(String code, String message) {
        return new ApiException(HttpStatus.BAD_REQUEST, code, message);
    }

    private ApiException notFound(String code, String message) {
        return new ApiException(HttpStatus.NOT_FOUND, code, message);
    }

    private String workflowRelativeDir(String workflowId) {
        return "gen/workflows/" + workflowId;
    }

    private String stageTypeFolder(String stageType) {
        return switch (trimmed(stageType, "")) {
            case WorkflowConstants.STAGE_STORYBOARD -> "storyboards";
            case WorkflowConstants.STAGE_KEYFRAME -> "keyframes";
            case WorkflowConstants.STAGE_VIDEO -> "videos";
            default -> "library";
        };
    }

    private int nextJoinedVersionNo(StageWorkflowEntity workflow) {
        return workflowRepository.listMaterialAssets(workflow.getOwnerUserId()).stream()
            .filter(item -> workflow.getWorkflowId().equals(item.getWorkflowId()) && WorkflowConstants.STAGE_JOINED.equals(item.getStageType()))
            .map(MaterialAssetEntity::getVersionNo)
            .filter(item -> item != null && item > 0)
            .max(Integer::compareTo)
            .orElse(0) + 1;
    }

    private double sumSelectedVideoDuration(Collection<StageVersionEntity> versions) {
        double total = 0.0;
        for (StageVersionEntity version : versions) {
            total += doubleValue(WorkflowJsonSupport.readMap(version.getOutputSummaryJson()).get("durationSeconds"), 0.0);
        }
        return total;
    }

    private String resolveOriginProvider(String stageType, StageWorkflowEntity workflow) {
        return switch (trimmed(stageType, "")) {
            case WorkflowConstants.STAGE_STORYBOARD -> "text-model";
            case WorkflowConstants.STAGE_KEYFRAME -> "image-model";
            case WorkflowConstants.STAGE_VIDEO, WorkflowConstants.STAGE_JOINED -> "video-model";
            default -> "workflow";
        };
    }

    private String resolveOriginModel(String stageType, StageWorkflowEntity workflow) {
        return switch (trimmed(stageType, "")) {
            case WorkflowConstants.STAGE_STORYBOARD -> workflow.getTextAnalysisModel();
            case WorkflowConstants.STAGE_KEYFRAME -> workflow.getImageModel();
            case WorkflowConstants.STAGE_VIDEO, WorkflowConstants.STAGE_JOINED -> workflow.getVideoModel();
            default -> "";
        };
    }

    private String normalizeMaterialAssetType(String value) {
        String normalized = trimmed(value, "").toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "character_sheet", "character_three_view" -> VARIANT_KIND_CHARACTER_SHEET;
            case "scene" -> "scene";
            case "prop" -> "prop";
            case "free" -> "free";
            default -> throw badRequest("material_asset_type_invalid", "素材类型不支持");
        };
    }

    private String materialAssetType(MaterialAssetEntity asset) {
        Map<String, Object> metadata = WorkflowJsonSupport.readMap(asset.getMetadataJson());
        String metadataType = trimmed(stringValue(metadata.get("assetType")), "");
        if (!metadataType.isBlank()) {
            return normalizeMaterialAssetTypeOrWorkflow(metadataType);
        }
        String variantKind = trimmed(stringValue(metadata.get("variantKind")), "");
        if (!variantKind.isBlank()) {
            return normalizeMaterialAssetTypeOrWorkflow(variantKind);
        }
        String role = trimmed(asset.getAssetRole(), "");
        if (!role.isBlank()) {
            return normalizeMaterialAssetTypeOrWorkflow(role);
        }
        return "workflow";
    }

    private String normalizeMaterialAssetTypeOrWorkflow(String value) {
        String normalized = trimmed(value, "").toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "character_sheet", "character_three_view" -> VARIANT_KIND_CHARACTER_SHEET;
            case "scene" -> "scene";
            case "prop" -> "prop";
            case "free" -> "free";
            default -> "workflow";
        };
    }

    private String materialAssetRole(String assetType) {
        return normalizeMaterialAssetType(assetType);
    }

    private String defaultMaterialTitle(String assetType) {
        return switch (normalizeMaterialAssetType(assetType)) {
            case VARIANT_KIND_CHARACTER_SHEET -> "角色三视图素材";
            case "scene" -> "场景素材";
            case "prop" -> "道具素材";
            case "free" -> "自由模式素材";
            default -> "素材";
        };
    }

    private StageWorkflowEntity materialCenterContext(
        Long ownerUserId,
        String aspectRatio,
        List<String> styleKeywords,
        String textAnalysisModel,
        String imageModel
    ) {
        StageWorkflowEntity context = new StageWorkflowEntity();
        context.setWorkflowId("");
        context.setOwnerUserId(ownerUserId);
        context.setTitle("素材中心");
        context.setAspectRatio(trimmed(aspectRatio, "9:16"));
        context.setStylePreset(styleKeywords == null || styleKeywords.isEmpty() ? "material-center" : String.join(", ", styleKeywords));
        context.setGlobalPrompt("");
        context.setTextAnalysisModel(trimmed(textAnalysisModel, ""));
        context.setImageModel(trimmed(imageModel, ""));
        context.setVideoModel("");
        return context;
    }

    private List<String> externallyAccessibleReferenceImageUrls(List<String> referenceImageUrls) {
        return externallyAccessibleReferenceImageUrls(referenceImageUrls, false);
    }

    private List<String> externallyAccessibleReferenceImageUrls(List<String> referenceImageUrls, boolean allowLocalImageDataUri) {
        if (referenceImageUrls == null || referenceImageUrls.isEmpty()) {
            return List.of();
        }
        List<String> urls = new ArrayList<>();
        for (String referenceImageUrl : referenceImageUrls) {
            String normalizedUrl = externallyAccessibleMediaUrl(referenceImageUrl, "referenceImageUrl", allowLocalImageDataUri);
            if (normalizedUrl.isBlank()) {
                continue;
            }
            if (!urls.contains(normalizedUrl)) {
                urls.add(normalizedUrl);
            }
        }
        return urls;
    }

    private String externallyAccessibleMediaUrl(String url, String fieldName) {
        return externallyAccessibleMediaUrl(url, fieldName, false);
    }

    private String externallyAccessibleMediaUrl(String url, String fieldName, boolean allowLocalImageDataUri) {
        String normalized = trimmed(url, "");
        if (normalized.isBlank()) {
            return "";
        }
        if (isAbsoluteHttpUrl(normalized) || (allowLocalImageDataUri && isImageDataUri(normalized))) {
            return normalized;
        }
        if (normalized.startsWith(ApiPathConstants.STORAGE)) {
            String mappedUrl = storageProperties.buildExternallyAccessibleUrl(normalized);
            if (!mappedUrl.isBlank() && isAbsoluteHttpUrl(mappedUrl)) {
                return mappedUrl;
            }
            if (!mappedUrl.isBlank()) {
                throw badRequest(
                    "storage_public_base_url_invalid",
                    "JIANDOU_STORAGE_PUBLIC_BASE_URL 必须生成公网可访问的 http(s) URL"
                );
            }
            if (allowLocalImageDataUri) {
                try {
                    String dataUri = localMediaArtifactService.imageDataUriFromPublicUrl(normalized);
                    if (dataUri != null && !dataUri.isBlank()) {
                        return dataUri;
                    }
                } catch (RuntimeException ex) {
                    throw badRequest("local_reference_image_unavailable", fieldName + " 本地资源无法转换为参考图输入：" + ex.getMessage());
                }
                throw badRequest("local_reference_image_unavailable", fieldName + " 本地资源无法转换为参考图输入");
            }
            throw badRequest(
                "storage_public_base_url_missing",
                fieldName + " 是本地存储地址，请先配置 JIANDOU_STORAGE_PUBLIC_BASE_URL 后再调用远端模型"
            );
        }
        throw badRequest("media_url_not_public", fieldName + " 必须是公网可访问的 http(s) URL");
    }

    private String compatibleVideoFrameUrl(String url, String fieldName) {
        String normalized = trimmed(url, "");
        if (normalized.isBlank()) {
            return "";
        }
        if (isAbsoluteHttpUrl(normalized) || isImageDataUri(normalized)) {
            return normalized;
        }
        if (normalized.startsWith(ApiPathConstants.STORAGE)) {
            try {
                String dataUri = localMediaArtifactService.imageDataUriFromPublicUrl(normalized);
                if (dataUri != null && !dataUri.isBlank()) {
                    return dataUri;
                }
            } catch (RuntimeException ex) {
                throw badRequest("local_video_frame_unavailable", fieldName + " 本地资源无法转换为视频首尾帧输入：" + ex.getMessage());
            }
            throw badRequest("local_video_frame_unavailable", fieldName + " 本地资源无法转换为视频首尾帧输入");
        }
        throw badRequest("media_url_not_public", fieldName + " 必须是公网可访问的 http(s) URL 或本地 /storage 图片");
    }

    private boolean isImageDataUri(String url) {
        String normalized = trimmed(url, "").toLowerCase(Locale.ROOT);
        return normalized.startsWith("data:image/") && normalized.contains(";base64,");
    }

    private boolean isAbsoluteHttpUrl(String url) {
        try {
            URI uri = URI.create(trimmed(url, ""));
            String scheme = uri.getScheme();
            if (scheme == null || uri.getHost() == null) {
                return false;
            }
            String lowerScheme = scheme.toLowerCase(Locale.ROOT);
            return "http".equals(lowerScheme) || "https".equals(lowerScheme);
        } catch (IllegalArgumentException ex) {
            return false;
        }
    }

    private Map<String, Object> buildMaterialGenerationRunRequest(
        Long ownerUserId,
        String assetType,
        String title,
        String description,
        List<String> styleKeywords,
        List<String> referenceImageUrls,
        String aspectRatio,
        String textAnalysisModel,
        String imageModel,
        Integer seed,
        WorkflowStageGenerationStrategy strategy,
        int[] dimensions
    ) {
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", buildMaterialGenerationPrompt(assetType, title, description, styleKeywords, !referenceImageUrls.isEmpty()));
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", assetType);
        if ("free".equals(normalizeMaterialAssetType(assetType))) {
            input.put("promptPassthrough", true);
        }
        if (!referenceImageUrls.isEmpty()) {
            input.put("referenceImageUrl", referenceImageUrls.get(0));
            input.put("referenceImageUrls", referenceImageUrls);
        }
        if (seed != null && imageModelSupportsSeed(imageModel, strategy)) {
            input.put("seed", seed);
        }
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", strategy.runKind());
        request.put("auth", Map.of("userId", ownerUserId));
        request.put("input", input);
        request.put("model", strategy.modelSection(textAnalysisModel));
        request.put("options", Map.of("stylePreset", styleKeywords == null || styleKeywords.isEmpty() ? "material-center" : String.join(", ", styleKeywords)));
        request.put("storage", Map.of(
            "relativeDir", "gen/material-center/" + assetType,
            "fileStem", assetType + "-" + randomId(),
            "requireRemoteSourceUrl", false
        ));
        request.put("metadata", Map.of(
            "assetType", assetType,
            "title", title,
            "aspectRatio", aspectRatio,
            "imageSize", dimensions[0] + "x" + dimensions[1],
            "relatedWorkflowId", "material-center",
            "stageStrategy", strategy.metadata()
        ));
        return request;
    }

    private String buildMaterialGenerationPrompt(
        String assetType,
        String title,
        String description,
        List<String> styleKeywords,
        boolean hasReferences
    ) {
        if ("free".equals(normalizeMaterialAssetType(assetType))) {
            return trimmed(description, "");
        }
        List<String> parts = new ArrayList<>();
        parts.add("素材标题：" + title);
        parts.add("素材描述：" + description);
        if (styleKeywords != null && !styleKeywords.isEmpty()) {
            parts.add("画风关键词：" + String.join(", ", styleKeywords));
        }
        if (hasReferences) {
            parts.add("参考图要求：严格沿用参考图中的主体结构、外观锚点、材质和关键比例，不要重新设计核心主体。");
        }
        switch (normalizeMaterialAssetType(assetType)) {
            case VARIANT_KIND_CHARACTER_SHEET -> {
                parts.add("生成类型：角色三视图设定图。");
                parts.add("必须输出同一角色的正面、侧面、背面三视图，放在同一张图中。");
                parts.add("三个视图都必须是完整从头到脚全身像，人物整体缩小并居中，头顶、双手、鞋子、脚底四周保留清晰留白，不得裁切或超出图片外。");
                parts.add("禁止半身像、胸像、近景特写、肖像照或过度放大构图；三个视图横向等距排列在同一张画布内。");
                parts.add("使用标准中性站姿，身体直立，双臂自然下垂或微微离身，双手空置，不做动作戏、剧情动作、表演动作或复杂姿势。");
                parts.add("只保留稳定穿戴配饰；禁止手拿、背负、牵引、互动或携带任何道具、武器、包袋、手机、文件、杯子、伞、花束等物体。");
                parts.add("脸、发型、服装、体型、年龄感和配饰保持一致。");
                parts.add("背景使用纯净浅色或纯白背景，不出现文字、箭头、水印、logo、说明标签或复杂场景。");
            }
            case "scene" -> {
                parts.add("生成类型：场景概念图。");
                parts.add("重点呈现空间布局、场景锚点、光线、材质、可供后续镜头复用的环境关系。");
                parts.add("避免出现无关人物，不添加文字、水印或说明标签。");
            }
            case "prop" -> {
                parts.add("生成类型：道具设定图。");
                parts.add("重点呈现道具主体、材质、比例、细节、可识别轮廓和干净背景。");
                parts.add("只突出一个主要道具，不添加文字、水印或说明标签。");
            }
            default -> { }
        }
        return String.join("\n", parts);
    }

    private Map<String, Object> materialGenerationMetadata(
        String assetType,
        String title,
        String description,
        List<String> styleKeywords,
        List<String> referenceAssetIds,
        List<String> referenceImageUrls,
        String aspectRatio,
        String imageSize,
        Map<String, Object> run,
        String remoteUrl
    ) {
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("assetType", normalizeMaterialAssetType(assetType));
        metadata.put("title", title);
        metadata.put("description", description);
        metadata.put("styleKeywords", styleKeywords);
        metadata.put("referenceAssetIds", referenceAssetIds);
        metadata.put("referenceImageUrls", referenceImageUrls);
        metadata.put("aspectRatio", aspectRatio);
        metadata.put("imageSize", firstNonBlank(imageSize, stringValue(mapValue(result.get("metadata")).get("requestedSize"))));
        metadata.put("runId", stringValue(run.get("id")));
        metadata.put("remoteSourceUrl", remoteUrl);
        metadata.put("prompt", stringValue(result.get("prompt")));
        metadata.put("shapedPrompt", stringValue(result.get("shapedPrompt")));
        metadata.put("modelInfo", mapValue(result.get("modelInfo")));
        return metadata;
    }

    private Map<String, Object> boundMaterialMetadata(MaterialAssetEntity sourceAsset, String variantKind) {
        Map<String, Object> sourceMetadata = WorkflowJsonSupport.readMap(sourceAsset.getMetadataJson());
        Map<String, Object> metadata = new LinkedHashMap<>(sourceMetadata);
        metadata.put("variantKind", variantKind);
        metadata.put("assetType", normalizeMaterialAssetTypeOrWorkflow(variantKind));
        metadata.put("sourceMaterialAssetId", sourceAsset.getMaterialAssetId());
        metadata.put("sourceAssetType", materialAssetType(sourceAsset));
        return metadata;
    }

    private Map<String, Object> withRemoteUploadMetadata(String metadataJson, String remotePath) {
        Map<String, Object> metadata = new LinkedHashMap<>(WorkflowJsonSupport.readMap(metadataJson));
        metadata.put("remoteSourceUrl", remotePath);
        metadata.put("remotePath", remotePath);
        metadata.put("remoteUploadedAt", OffsetDateTime.now(ZoneOffset.UTC).toString());
        return metadata;
    }

    private int[] dimensionsFromAspectRatio(String aspectRatio) {
        if ("16:9".equals(trimmed(aspectRatio, ""))) {
            return new int[] {1824, 1024};
        }
        if ("1:1".equals(trimmed(aspectRatio, ""))) {
            return new int[] {1024, 1024};
        }
        return new int[] {1024, 1824};
    }

    private int[] materialGenerationDimensions(String assetType, String aspectRatio, String imageSize) {
        int[] parsedImageSize = dimensionsFromImageSize(imageSize);
        if (parsedImageSize[0] > 0 && parsedImageSize[1] > 0) {
            return parsedImageSize;
        }
        if (VARIANT_KIND_CHARACTER_SHEET.equals(normalizeMaterialAssetType(assetType))) {
            return new int[] {1824, 1024};
        }
        return dimensionsFromAspectRatio(aspectRatio);
    }

    private int[] dimensionsFromImageSize(String imageSize) {
        String normalized = trimmed(imageSize, "").toLowerCase(Locale.ROOT).replace('*', 'x');
        String[] parts = normalized.split("x");
        if (parts.length != 2) {
            return new int[] {0, 0};
        }
        try {
            int width = Integer.parseInt(parts[0].trim());
            int height = Integer.parseInt(parts[1].trim());
            return width > 0 && height > 0 ? new int[] {width, height} : new int[] {0, 0};
        } catch (NumberFormatException ex) {
            return new int[] {0, 0};
        }
    }

    private List<?> listObjectValue(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private List<String> normalizeStringList(Collection<?> values) {
        if (values == null) {
            return List.of();
        }
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (Object item : values) {
            String value = stringValue(item).trim();
            if (!value.isBlank()) {
                normalized.add(value);
            }
        }
        return new ArrayList<>(normalized);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listMapValue(Object value) {
        if (value instanceof List<?> list) {
            return (List<Map<String, Object>>) list;
        }
        return List.of();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private String stageLabel(String stageType) {
        return switch (trimmed(stageType, "")) {
            case WorkflowConstants.STAGE_KEYFRAME -> "关键帧";
            case WorkflowConstants.STAGE_VIDEO -> "视频";
            default -> "阶段";
        };
    }

    private String defaultVideoSize(String aspectRatio) {
        return "16:9".equals(trimmed(aspectRatio, "")) ? "1280*720" : "720*1280";
    }

    private String composeVisualPrompt(StageWorkflowEntity workflow, String prompt) {
        String normalizedPrompt = trimmed(prompt, "");
        String globalPrompt = workflow == null ? "" : trimmed(workflow.getGlobalPrompt(), "");
        if (globalPrompt.isBlank()) {
            return normalizedPrompt;
        }
        return joinPromptSections("全局画风要求：" + globalPrompt, normalizedPrompt);
    }

    private String joinPromptSections(String... sections) {
        List<String> parts = new ArrayList<>();
        if (sections == null) {
            return "";
        }
        for (String section : sections) {
            String normalized = trimmed(section, "");
            if (!normalized.isBlank()) {
                parts.add(normalized);
            }
        }
        return String.join("\n", parts);
    }

    private String resolveGeneratedMediaRemoteUrl(Map<String, Object> result) {
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String remoteUrl = firstNonBlank(
            stringValue(metadata.get("remoteSourceUrl")),
            stringValue(metadata.get("sourceUrl"))
        );
        if (!remoteUrl.isBlank()) {
            return generatedMediaReferenceUrl(remoteUrl, "generated remoteSourceUrl");
        }
        String fileUrl = firstNonBlank(
            stringValue(result.get("outputUrl")),
            stringValue(metadata.get("fileUrl")),
            stringValue(metadata.get("outputUrl"))
        );
        return generatedMediaReferenceUrl(fileUrl, "generated fileUrl");
    }

    private String generatedMediaReferenceUrl(String url, String fieldName) {
        String normalized = trimmed(url, "");
        if (normalized.isBlank() || isAbsoluteHttpUrl(normalized) || isImageDataUri(normalized)) {
            return normalized;
        }
        if (normalized.startsWith(ApiPathConstants.STORAGE)) {
            String mappedUrl = storageProperties.buildExternallyAccessibleUrl(normalized);
            return !mappedUrl.isBlank() && isAbsoluteHttpUrl(mappedUrl) ? mappedUrl : normalized;
        }
        return externallyAccessibleMediaUrl(normalized, fieldName);
    }

    private String normalizeFrameRole(String value) {
        return "last".equalsIgnoreCase(trimmed(value, "first")) ? "last" : "first";
    }

    private String randomId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    private String trimmed(String value, String fallback) {
        if (value == null) {
            return fallback == null ? "" : fallback.trim();
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? (fallback == null ? "" : fallback.trim()) : normalized;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private Object firstNonBlankObject(Object... values) {
        if (values == null) {
            return null;
        }
        for (Object value : values) {
            if (value instanceof String text) {
                if (!text.isBlank()) {
                    return text;
                }
                continue;
            }
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private String typeValue(String value) {
        return value == null ? "" : value.trim();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return fallback;
    }

    private double doubleValue(Object value, double fallback) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value != null) {
            try {
                return Double.parseDouble(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return fallback;
    }

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return "true".equalsIgnoreCase(stringValue(value)) || "1".equals(stringValue(value));
    }

    private String format(OffsetDateTime value) {
        return value == null ? null : value.toString();
    }

    private int safeLength(String value) {
        return value == null ? 0 : value.trim().length();
    }

    private String truncate(String value, int max) {
        String text = trimmed(value, "");
        if (text.length() <= max) {
            return text;
        }
        return text.substring(0, max) + "...";
    }

    private String fileNameFromUrl(String url) {
        String normalized = stringValue(url).replaceAll("[?#].*$", "");
        int index = normalized.lastIndexOf('/');
        return index >= 0 ? normalized.substring(index + 1) : normalized;
    }

    private String fileExt(String url) {
        String fileName = fileNameFromUrl(url);
        int index = fileName.lastIndexOf('.');
        return index >= 0 ? fileName.substring(index + 1) : "";
    }

    private Long fileSize(String fileUrl) {
        String absolutePath = localMediaArtifactService.resolveAbsolutePath(fileUrl);
        if (absolutePath.isBlank()) {
            return 0L;
        }
        try {
            return Files.size(Path.of(absolutePath));
        } catch (Exception ex) {
            return 0L;
        }
    }

    private record CharacterSheetSlot(String characterName, String characterAppearance, String characterDefinition, int syntheticClipIndex) {}
    private record CharacterReference(String characterName, String fallbackAppearance, String referenceAppearance, String imageUrl) {}
}
