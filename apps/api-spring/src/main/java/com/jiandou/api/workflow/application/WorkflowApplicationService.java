package com.jiandou.api.workflow.application;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.auth.security.SecurityCurrentUser;
import com.jiandou.api.common.exception.ApiException;
import com.jiandou.api.generation.GenerationRunStatuses;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.workflow.WorkflowConstants;
import com.jiandou.api.workflow.infrastructure.WorkflowJsonSupport;
import com.jiandou.api.workflow.infrastructure.mybatis.MaterialAssetTagEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import com.jiandou.api.workflow.web.dto.CreateWorkflowRequest;
import com.jiandou.api.workflow.web.dto.RateStageVersionRequest;
import com.jiandou.api.workflow.web.dto.RateWorkflowRequest;
import com.jiandou.api.workflow.web.dto.ReuseMaterialRequest;
import com.jiandou.api.workflow.web.dto.UpdateMaterialAssetRatingRequest;
import com.jiandou.api.workflow.web.dto.UpdateMaterialAssetTagsRequest;
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
    private static final String VARIANT_KIND_CHARACTER_SHEET = "character_sheet";

    private final WorkflowRepository workflowRepository;
    private final GenerationApplicationService generationApplicationService;
    private final TaskStoryboardPlanner storyboardPlanner;
    private final LocalMediaArtifactService localMediaArtifactService;

    public WorkflowApplicationService(
        WorkflowRepository workflowRepository,
        GenerationApplicationService generationApplicationService,
        TaskStoryboardPlanner storyboardPlanner,
        LocalMediaArtifactService localMediaArtifactService
    ) {
        this.workflowRepository = workflowRepository;
        this.generationApplicationService = generationApplicationService;
        this.storyboardPlanner = storyboardPlanner;
        this.localMediaArtifactService = localMediaArtifactService;
    }

    public Map<String, Object> createWorkflow(CreateWorkflowRequest request) {
        Long ownerUserId = requiredUserId();
        validateCreateWorkflowRequest(request);
        StageWorkflowEntity workflow = new StageWorkflowEntity();
        workflow.setWorkflowId("wf_" + randomId());
        workflow.setOwnerUserId(ownerUserId);
        workflow.setTitle(trimmed(request.title(), "未命名工作流"));
        workflow.setTranscriptText(trimmed(request.transcriptText(), ""));
        workflow.setGlobalPrompt(trimmed(request.globalPrompt(), ""));
        workflow.setAspectRatio(trimmed(request.aspectRatio(), "9:16"));
        workflow.setStylePreset(trimmed(request.stylePreset(), "cinematic"));
        workflow.setTextAnalysisModel(trimmed(request.textAnalysisModel(), ""));
        workflow.setVisionModel(trimmed(request.visionModel(), ""));
        workflow.setImageModel(trimmed(request.imageModel(), ""));
        workflow.setVideoModel(trimmed(request.videoModel(), ""));
        workflow.setVideoSize(trimmed(request.videoSize(), defaultVideoSize(workflow.getAspectRatio())));
        Integer keyframeSeed = request.keyframeSeed() != null ? request.keyframeSeed() : request.seed();
        Integer videoSeed = request.videoSeed() != null ? request.videoSeed() : request.seed();
        workflow.setTaskSeed(resolvedSharedSeed(keyframeSeed, videoSeed, request.seed()));
        workflow.setKeyframeSeed(keyframeSeed);
        workflow.setVideoSeed(videoSeed);
        workflow.setMinDurationSeconds(request.minDurationSeconds() == null ? 5 : request.minDurationSeconds());
        workflow.setMaxDurationSeconds(request.maxDurationSeconds() == null ? Math.max(5, workflow.getMinDurationSeconds()) : Math.max(request.maxDurationSeconds(), request.minDurationSeconds() == null ? 5 : request.minDurationSeconds()));
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

    public List<Map<String, Object>> listWorkflows() {
        Long ownerUserId = requiredUserId();
        List<StageWorkflowEntity> workflows = workflowRepository.listWorkflows(ownerUserId);
        Map<String, List<StageVersionEntity>> versionMap = new LinkedHashMap<>();
        for (StageWorkflowEntity workflow : workflows) {
            versionMap.put(workflow.getWorkflowId(), workflowRepository.listStageVersions(workflow.getWorkflowId()));
        }
        return workflows.stream().map(workflow -> toWorkflowSummary(workflow, versionMap.getOrDefault(workflow.getWorkflowId(), List.of()))).toList();
    }

    public Map<String, Object> getWorkflow(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId);
        Map<String, MaterialAssetEntity> assetMap = loadAssetMap(versions, workflow.getFinalJoinAssetId(), workflow.getOwnerUserId());
        Map<String, List<MaterialAssetTagEntity>> tagMap = workflowRepository.listTagsByAssetIds(assetMap.keySet());
        return toWorkflowDetail(workflow, versions, assetMap, tagMap);
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
            markMaterialAssetDeleted(version.getMaterialAssetId());
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
            "transcriptLength", safeLength(workflow.getTranscriptText()),
            "globalPrompt", workflow.getGlobalPrompt()
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
        syncAssetTags(asset, version, workflow, List.of());
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
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        String continuitySource = clipIndex == 1 ? "generated_start_frame" : "previous_clip_end_frame";
        Map<String, Object> startFrameRun = Map.of();
        Map<String, Object> startFrameResult = Map.of();
        String startFrameUrl = "";
        String startFrameRemoteUrl = "";
        if (clipIndex == 1) {
            Map<String, Object> startFrameRequest = buildKeyframeRunRequest(
                workflow,
                clip,
                clipIndex,
                versionNo,
                firstNonBlank(stringValue(clip.get("startFrame")), stringValue(clip.get("firstFramePrompt"))),
                "",
                "first",
                "clip" + clipIndex + "-first-v" + versionNo
            );
            startFrameRun = createLoggedGenerationRun(
                workflow,
                WorkflowConstants.STAGE_KEYFRAME,
                "workflow.keyframe.generate",
                startFrameRequest,
                Map.of("clipIndex", clipIndex, "versionNo", versionNo, "frameRole", "first")
            );
            startFrameResult = mapValue(startFrameRun.get("result"));
            startFrameUrl = extractGenerationFileUrl(startFrameResult);
            if (startFrameUrl.isBlank()) {
                throw badRequest("workflow_keyframe_empty", "首帧关键帧生成结果为空");
            }
            startFrameRemoteUrl = resolveGeneratedMediaRemoteUrl(startFrameResult);
        } else {
            startFrameUrl = resolveWorkflowClipStartFrameUrl(workflowId, clipIndex);
            startFrameRemoteUrl = resolveWorkflowClipStartFrameRemoteUrl(workflowId, clipIndex);
            if (startFrameUrl.isBlank()) {
                continuitySource = "previous_clip_end_frame_missing";
            }
        }
        Map<String, Object> keyframeRequest = buildKeyframeRunRequest(
            workflow,
            clip,
            clipIndex,
            versionNo,
            firstNonBlank(stringValue(clip.get("endFrame")), stringValue(clip.get("lastFramePrompt"))),
            startFrameUrl,
            "last",
            "clip" + clipIndex + "-last-v" + versionNo
        );
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            "workflow.keyframe.generate",
            keyframeRequest,
            Map.of("clipIndex", clipIndex, "versionNo", versionNo, "frameRole", "last", "continuitySource", continuitySource)
        );
        Map<String, Object> result = mapValue(run.get("result"));
        String fileUrl = extractGenerationFileUrl(result);
        if (fileUrl.isBlank()) {
            throw badRequest("workflow_keyframe_empty", "尾帧关键帧生成结果为空");
        }
        String endFrameRemoteUrl = resolveGeneratedMediaRemoteUrl(result);
        MaterialAssetEntity asset = createMaterialAsset(
            workflow,
            WorkflowConstants.STAGE_KEYFRAME,
            clipIndex,
            versionNo,
            "image",
            workflow.getTitle() + " 关键帧 #" + clipIndex + " V" + versionNo,
            fileUrl,
            fileUrl,
            stringValue(result.getOrDefault("mimeType", "image/png")),
            0.0,
            intValue(result.get("width"), 0),
            intValue(result.get("height"), 0),
            false,
            stringValue(mapValue(result.get("metadata")).get("taskId")),
            endFrameRemoteUrl,
            keyframeAssetMetadata(clip, run, startFrameRun, startFrameUrl, startFrameRemoteUrl, fileUrl, endFrameRemoteUrl, continuitySource)
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
        version.setSelected(hasNoSelectedVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex) ? 1 : 0);
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
        keyframeInputSummary.put("startFrameUrl", startFrameUrl);
        keyframeInputSummary.put("firstFrameUrl", startFrameUrl);
        keyframeInputSummary.put("startFrameRemoteUrl", startFrameRemoteUrl);
        keyframeInputSummary.put("firstFrameRemoteUrl", startFrameRemoteUrl);
        keyframeInputSummary.put("endFrameUrl", fileUrl);
        keyframeInputSummary.put("lastFrameUrl", fileUrl);
        keyframeInputSummary.put("endFrameRemoteUrl", endFrameRemoteUrl);
        keyframeInputSummary.put("lastFrameRemoteUrl", endFrameRemoteUrl);
        keyframeInputSummary.put("continuitySource", continuitySource);
        Integer keyframeSeed = resolvedKeyframeSeed(workflow);
        if (keyframeSeed != null) {
            keyframeInputSummary.put("seed", keyframeSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(keyframeInputSummary));
        Map<String, Object> outputSummary = new LinkedHashMap<>();
        outputSummary.put("clip", clip);
        outputSummary.put("fileUrl", fileUrl);
        outputSummary.put("startFrameUrl", startFrameUrl);
        outputSummary.put("firstFrameUrl", startFrameUrl);
        outputSummary.put("startFrameRemoteUrl", startFrameRemoteUrl);
        outputSummary.put("firstFrameRemoteUrl", startFrameRemoteUrl);
        outputSummary.put("endFrameUrl", fileUrl);
        outputSummary.put("lastFrameUrl", fileUrl);
        outputSummary.put("endFrameRemoteUrl", endFrameRemoteUrl);
        outputSummary.put("lastFrameRemoteUrl", endFrameRemoteUrl);
        outputSummary.put("continuitySource", continuitySource);
        outputSummary.put("width", intValue(result.get("width"), 0));
        outputSummary.put("height", intValue(result.get("height"), 0));
        outputSummary.put("generatedFrames", generatedKeyframeFrames(startFrameRun, startFrameResult, run, result, startFrameUrl, startFrameRemoteUrl, fileUrl, endFrameRemoteUrl));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(outputSummary));
        Map<String, Object> modelCallSummary = new LinkedHashMap<>();
        modelCallSummary.put("runId", stringValue(run.get("id")));
        modelCallSummary.put("endFrameRunId", stringValue(run.get("id")));
        modelCallSummary.put("modelInfo", mapValue(result.get("modelInfo")));
        if (!stringValue(startFrameRun.get("id")).isBlank()) {
            modelCallSummary.put("startFrameRunId", stringValue(startFrameRun.get("id")));
            modelCallSummary.put("startFrameModelInfo", mapValue(startFrameResult.get("modelInfo")));
        }
        modelCallSummary.put("endFrameModelInfo", mapValue(result.get("modelInfo")));
        version.setModelCallSummaryJson(WorkflowJsonSupport.write(modelCallSummary));
        version.setIsDeleted(0);
        workflowRepository.saveStageVersion(version);
        if (version.getSelected() == 1) {
            syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, version.getStageVersionId());
            workflow.setCurrentStage(WorkflowConstants.STAGE_VIDEO);
            workflow.setStatus(WorkflowConstants.STATUS_READY);
            workflowRepository.saveWorkflow(workflow);
        }
        syncMaterialAssetSelection(asset.getMaterialAssetId(), version.getSelected() == 1);
        syncAssetTags(asset, version, workflow, List.of());
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

    public Map<String, Object> generateVideo(String workflowId, int clipIndex) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        StageVersionEntity storyboardVersion = requireSelectedStoryboard(workflow);
        StageVersionEntity keyframeVersion = requireSelectedStageVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        Map<String, Object> clip = requireStoryboardClip(storyboardVersion, clipIndex);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_VIDEO, clipIndex);
        String firstFrameUrl = resolveWorkflowVideoFirstFrameUrl(workflowId, clipIndex, keyframeVersion);
        String lastFrameUrl = resolveWorkflowVideoLastFrameUrl(keyframeVersion);
        Map<String, Object> videoRequest = buildVideoRunRequest(workflow, clip, clipIndex, versionNo, firstFrameUrl, lastFrameUrl);
        Map<String, Object> run = createLoggedGenerationRun(
            workflow,
            WorkflowConstants.STAGE_VIDEO,
            "workflow.video.generate",
            videoRequest,
            Map.of("clipIndex", clipIndex, "versionNo", versionNo)
        );
        run = awaitCompletedVideoRun(run);
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
        syncAssetTags(asset, version, workflow, List.of());
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
        syncAssetTags(asset, null, workflow, List.of());
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
            syncAssetTags(asset, version, requireWorkflow(workflowId), customTagValues(asset.getMaterialAssetId()));
        }
        return getWorkflow(workflowId);
    }

    public List<Map<String, Object>> listMaterialAssets(
        String q,
        String type,
        String tag,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex
    ) {
        Long ownerUserId = requiredUserId();
        List<MaterialAssetEntity> assets = workflowRepository.listMaterialAssets(ownerUserId);
        Map<String, List<MaterialAssetTagEntity>> tagMap = workflowRepository.listTagsByAssetIds(
            assets.stream().map(MaterialAssetEntity::getMaterialAssetId).collect(Collectors.toCollection(LinkedHashSet::new))
        );
        return assets.stream()
            .filter(item -> matchesMaterialFilters(item, tagMap.getOrDefault(item.getMaterialAssetId(), List.of()), q, type, tag, minRating, model, aspectRatio, clipIndex))
            .map(item -> toMaterialAssetRow(item, tagMap.getOrDefault(item.getMaterialAssetId(), List.of())))
            .toList();
    }

    public Map<String, Object> getMaterialAsset(String assetId) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        return toMaterialAssetRow(asset, workflowRepository.listTags(assetId));
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
        syncAssetTags(asset, version, asset.getWorkflowId().isBlank() ? null : requireWorkflow(asset.getWorkflowId()), customTagValues(assetId));
        return getMaterialAsset(assetId);
    }

    public Map<String, Object> updateMaterialAssetTags(String assetId, UpdateMaterialAssetTagsRequest request) {
        MaterialAssetEntity asset = requireMaterialAsset(assetId);
        StageVersionEntity version = workflowRepository.findStageVersionByMaterialAssetId(assetId);
        StageWorkflowEntity workflow = asset.getWorkflowId() == null || asset.getWorkflowId().isBlank() ? null : requireWorkflow(asset.getWorkflowId());
        syncAssetTags(asset, version, workflow, normalizeCustomTags(request.tags()));
        return getMaterialAsset(assetId);
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
            sourceWorkflow.getGlobalPrompt(),
            sourceWorkflow.getAspectRatio(),
            sourceWorkflow.getStylePreset(),
            sourceWorkflow.getTextAnalysisModel(),
            sourceWorkflow.getVisionModel(),
            sourceWorkflow.getImageModel(),
            sourceWorkflow.getVideoModel(),
            sourceWorkflow.getVideoSize(),
            sourceWorkflow.getKeyframeSeed(),
            sourceWorkflow.getVideoSeed(),
            sourceWorkflow.getTaskSeed(),
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
        syncAssetTags(clonedAsset, cloned, targetWorkflow, customTagValues(sourceAsset.getMaterialAssetId()));
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
        List<MaterialAssetTagEntity> tags,
        String q,
        String type,
        String tag,
        Integer minRating,
        String model,
        String aspectRatio,
        Integer clipIndex
    ) {
        if (!typeValue(type).isBlank() && !typeValue(type).equalsIgnoreCase(trimmed(asset.getStageType(), ""))) {
            return false;
        }
        if (minRating != null && (asset.getUserRating() == null || asset.getUserRating() < minRating)) {
            return false;
        }
        if (!typeValue(model).isBlank() && !trimmed(asset.getOriginModel(), "").toLowerCase(Locale.ROOT).contains(typeValue(model).toLowerCase(Locale.ROOT))) {
            return false;
        }
        if (!typeValue(aspectRatio).isBlank() && tags.stream().noneMatch(item -> "aspectRatio".equals(item.getTagKey()) && typeValue(aspectRatio).equalsIgnoreCase(item.getTagValue()))) {
            return false;
        }
        if (clipIndex != null && intValue(asset.getClipIndex(), 0) != clipIndex) {
            return false;
        }
        if (!typeValue(tag).isBlank() && tags.stream().noneMatch(item -> item.getTagValue() != null && item.getTagValue().toLowerCase(Locale.ROOT).contains(typeValue(tag).toLowerCase(Locale.ROOT)))) {
            return false;
        }
        String keyword = typeValue(q).toLowerCase(Locale.ROOT);
        if (!keyword.isBlank()) {
            String haystack = String.join(" ",
                trimmed(asset.getTitle(), ""),
                trimmed(asset.getStageType(), ""),
                trimmed(asset.getOriginModel(), ""),
                trimmed(asset.getWorkflowId(), "")
            ).toLowerCase(Locale.ROOT);
            if (!haystack.contains(keyword)) {
                return false;
            }
        }
        return true;
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
        row.put("storyboardVersionCount", versions.stream().filter(item -> WorkflowConstants.STAGE_STORYBOARD.equals(item.getStageType())).count());
        row.put("keyframeVersionCount", versions.stream().filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())).count());
        row.put("videoVersionCount", versions.stream().filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType())).count());
        return row;
    }

    private Map<String, Object> toWorkflowDetail(
        StageWorkflowEntity workflow,
        List<StageVersionEntity> versions,
        Map<String, MaterialAssetEntity> assetMap,
        Map<String, List<MaterialAssetTagEntity>> tagMap
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", workflow.getWorkflowId());
        row.put("title", workflow.getTitle());
        row.put("transcriptText", workflow.getTranscriptText());
        row.put("globalPrompt", workflow.getGlobalPrompt());
        row.put("aspectRatio", workflow.getAspectRatio());
        row.put("stylePreset", workflow.getStylePreset());
        row.put("textAnalysisModel", workflow.getTextAnalysisModel());
        row.put("visionModel", workflow.getVisionModel());
        row.put("imageModel", workflow.getImageModel());
        row.put("videoModel", workflow.getVideoModel());
        row.put("videoSize", workflow.getVideoSize());
        row.put("keyframeSeed", resolvedKeyframeSeed(workflow));
        row.put("videoSeed", resolvedVideoSeed(workflow));
        row.put("seed", resolvedSharedSeed(workflow));
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
            .map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()), tagMap.getOrDefault(item.getMaterialAssetId(), List.of())))
            .toList();
        row.put("storyboardVersions", storyboardRows);
        StageVersionEntity selectedStoryboard = storyboardVersions.stream().filter(item -> intValue(item.getSelected(), 0) == 1).findFirst().orElse(null);
        row.put(
            "characterSheets",
            selectedStoryboard == null ? List.of() : buildCharacterSheetRows(selectedStoryboard, versions, assetMap, tagMap)
        );
        List<Map<String, Object>> clips = selectedStoryboard == null ? List.of() : readClips(selectedStoryboard);
        List<Map<String, Object>> clipSlots = new ArrayList<>();
        for (Map<String, Object> clip : clips) {
            int clipIndex = intValue(clip.get("clipIndex"), 0);
            List<StageVersionEntity> keyframeVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
                .sorted(Comparator.comparing(StageVersionEntity::getVersionNo).reversed())
                .toList();
            List<StageVersionEntity> videoVersions = versions.stream()
                .filter(item -> WorkflowConstants.STAGE_VIDEO.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
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
            slot.put("keyframeVersions", keyframeVersions.stream().map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()), tagMap.getOrDefault(item.getMaterialAssetId(), List.of()))).toList());
            slot.put("videoVersions", videoVersions.stream().map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()), tagMap.getOrDefault(item.getMaterialAssetId(), List.of()))).toList());
            clipSlots.add(slot);
        }
        row.put("clipSlots", clipSlots);
        row.put("finalResult", isBlank(workflow.getFinalJoinAssetId()) ? null : toMaterialAssetRow(assetMap.get(workflow.getFinalJoinAssetId()), tagMap.getOrDefault(workflow.getFinalJoinAssetId(), List.of())));
        return row;
    }

    private List<Map<String, Object>> buildCharacterSheetRows(
        StageVersionEntity storyboardVersion,
        List<StageVersionEntity> versions,
        Map<String, MaterialAssetEntity> assetMap,
        Map<String, List<MaterialAssetTagEntity>> tagMap
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
                    .map(item -> toStageVersionRow(item, assetMap.get(item.getMaterialAssetId()), tagMap.getOrDefault(item.getMaterialAssetId(), List.of())))
                    .toList()
            );
            rows.add(row);
        }
        return rows;
    }

    private Map<String, Object> toStageVersionRow(StageVersionEntity version, MaterialAssetEntity asset, List<MaterialAssetTagEntity> tags) {
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
        row.put("asset", asset == null ? null : toMaterialAssetRow(asset, tags));
        return row;
    }

    private Map<String, Object> toMaterialAssetRow(MaterialAssetEntity asset, List<MaterialAssetTagEntity> tags) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", asset.getMaterialAssetId());
        row.put("workflowId", asset.getWorkflowId());
        row.put("stageType", asset.getStageType());
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
        row.put("remoteUrl", asset.getRemoteUrl());
        row.put("metadata", WorkflowJsonSupport.readMap(asset.getMetadataJson()));
        row.put("createdAt", format(asset.getCreateTime()));
        row.put("updatedAt", format(asset.getUpdateTime()));
        row.put("tags", tags.stream().map(this::toTagRow).toList());
        return row;
    }

    private Map<String, Object> toTagRow(MaterialAssetTagEntity tag) {
        return Map.of(
            "id", tag.getAssetTagId(),
            "tagType", tag.getTagType(),
            "tagKey", tag.getTagKey(),
            "tagValue", tag.getTagValue()
        );
    }

    private void syncWorkflowStageAssetSelection(String workflowId, String stageType, int clipIndex, String selectedVersionId) {
        List<StageVersionEntity> versions = workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> stageType.equals(item.getStageType()) && intValue(item.getClipIndex(), 0) == clipIndex)
            .toList();
        for (StageVersionEntity item : versions) {
            MaterialAssetEntity asset = workflowRepository.findMaterialAsset(item.getMaterialAssetId(), requiredUserId());
            if (asset == null) {
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
            if (asset == null) {
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
        workflowRepository.saveMaterialAssetTags(assetId, List.of());
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

    private void syncAssetTags(MaterialAssetEntity asset, StageVersionEntity version, StageWorkflowEntity workflow, List<String> customTags) {
        if (asset == null) {
            return;
        }
        List<MaterialAssetTagEntity> tags = new ArrayList<>();
        addSystemTag(tags, asset, "stageType", trimmed(asset.getStageType(), ""));
        addSystemTag(tags, asset, "mediaType", trimmed(asset.getMediaType(), ""));
        addSystemTag(tags, asset, "model", trimmed(asset.getOriginModel(), ""));
        addSystemTag(tags, asset, "clipIndex", String.valueOf(intValue(asset.getClipIndex(), 0)));
        addSystemTag(tags, asset, "selected", intValue(asset.getSelectedForNext(), 0) == 1 ? "selected" : "unselected");
        if (workflow != null) {
            addSystemTag(tags, asset, "style", trimmed(workflow.getStylePreset(), ""));
            addSystemTag(tags, asset, "aspectRatio", trimmed(workflow.getAspectRatio(), ""));
        }
        if (asset.getUserRating() != null) {
            addSystemTag(tags, asset, "ratingBucket", asset.getUserRating() + "star");
        }
        for (String value : normalizeCustomTags(customTags)) {
            MaterialAssetTagEntity tag = new MaterialAssetTagEntity();
            tag.setAssetTagId("atag_" + randomId());
            tag.setMaterialAssetId(asset.getMaterialAssetId());
            tag.setTagType("custom");
            tag.setTagKey("custom");
            tag.setTagValue(value);
            tag.setIsDeleted(0);
            tags.add(tag);
        }
        workflowRepository.saveMaterialAssetTags(asset.getMaterialAssetId(), tags);
    }

    private void addSystemTag(List<MaterialAssetTagEntity> tags, MaterialAssetEntity asset, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        MaterialAssetTagEntity tag = new MaterialAssetTagEntity();
        tag.setAssetTagId("atag_" + randomId());
        tag.setMaterialAssetId(asset.getMaterialAssetId());
        tag.setTagType("system");
        tag.setTagKey(key);
        tag.setTagValue(value);
        tag.setIsDeleted(0);
        tags.add(tag);
    }

    private List<String> customTagValues(String assetId) {
        return workflowRepository.listTags(assetId).stream()
            .filter(item -> "custom".equals(item.getTagType()))
            .map(MaterialAssetTagEntity::getTagValue)
            .toList();
    }

    private Map<String, Object> buildStoryboardRunRequest(StageWorkflowEntity workflow, int versionNo) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("kind", "script");
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", Map.of(
            "text", !trimmed(workflow.getTranscriptText(), "").isBlank() ? workflow.getTranscriptText() : firstNonBlank(workflow.getGlobalPrompt(), workflow.getTitle())
        ));
        request.put("model", Map.of(
            "textAnalysisModel", workflow.getTextAnalysisModel()
        ));
        request.put("options", Map.of(
            "visualStyle", firstNonBlank(workflow.getStylePreset(), "cinematic")
        ));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/storyboards",
            "fileName", "storyboard-v" + versionNo + ".md"
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
        String modelCallId = "mdlcall_" + randomId();
        OffsetDateTime startedAt = OffsetDateTime.now();
        Map<String, Object> requestPayload = new LinkedHashMap<>();
        requestPayload.put("modelCallId", modelCallId);
        requestPayload.put("workflowId", workflow.getWorkflowId());
        requestPayload.put("workflowTitle", workflow.getTitle());
        requestPayload.put("request", request);
        requestPayload.putAll(context == null ? Map.of() : context);
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
            return run;
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
        Map<String, Object> requestPayload = new LinkedHashMap<>();
        requestPayload.put("workflowId", workflow.getWorkflowId());
        requestPayload.put("workflowTitle", workflow.getTitle());
        requestPayload.put("stage", stage);
        requestPayload.put("operation", operation);
        requestPayload.put("context", context == null ? Map.of() : context);
        requestPayload.put("request", request == null ? Map.of() : request);
        Map<String, Object> responsePayload = new LinkedHashMap<>();
        responsePayload.put("workflowId", workflow.getWorkflowId());
        responsePayload.put("stage", stage);
        responsePayload.put("context", context == null ? Map.of() : context);
        if (error == null) {
            responsePayload.put("run", run == null ? Map.of() : run);
        } else {
            responsePayload.put("errorType", error.getClass().getName());
            responsePayload.put("errorMessage", firstNonBlank(error.getMessage(), "unknown"));
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("modelCallId", modelCallId);
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
        row.put("httpStatus", error == null ? 200 : 0);
        row.put("responseCode", error == null ? 200 : 0);
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
            stringValue(mapValue(result.get("metadata")).get("remoteSourceUrl")),
            characterSheetAssetMetadata(slot, run, fileUrl)
        );
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
        Integer keyframeSeed = resolvedKeyframeSeed(workflow);
        if (keyframeSeed != null) {
            inputSummary.put("seed", keyframeSeed);
        }
        version.setInputSummaryJson(WorkflowJsonSupport.write(inputSummary));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "variantKind", VARIANT_KIND_CHARACTER_SHEET,
            "clipIndex", clipIndex,
            "characterName", slot.characterName(),
            "characterDefinition", slot.characterDefinition(),
            "characterAppearance", slot.characterAppearance(),
            "fileUrl", fileUrl,
            "sheetUrl", fileUrl,
            "previewUrl", fileUrl,
            "width", intValue(result.get("width"), 0),
            "height", intValue(result.get("height"), 0)
        )));
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
        syncAssetTags(asset, version, workflow, List.of());
    }

    private String buildCharacterSheetPrompt(StageWorkflowEntity workflow, CharacterSheetSlot slot) {
        return String.join(
            "\n",
            visualStyleConstraintBlock(workflow),
            "人物绑定：",
            "- 角色：" + slot.characterName(),
            "- 角色完整定义：" + slot.characterDefinition(),
            "- 外观唯一依据：" + slot.characterAppearance(),
            "生成要求：",
            "- 只出现这一个角色，不要出现其他人物、宠物或路人。",
            "- 输出同一角色的三视图设定图：正面、侧面、背面，放在同一张图中。",
            "- 三个视图都必须是完整的从头到脚全身像，头顶与脚底完整入镜，不能裁切脸部、头发、手臂、腿部或脚部。",
            "- 三个视图必须保持同一张脸、同一发型、同一服装、同一年龄、同一体型、同一配饰。",
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
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        int[] dimensions = dimensionsFromAspectRatio(workflow.getAspectRatio());
        input.put("prompt", prompt);
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", VARIANT_KIND_CHARACTER_SHEET);
        Integer keyframeSeed = resolvedKeyframeSeed(workflow);
        if (keyframeSeed != null) {
            input.put("seed", keyframeSeed);
        }
        request.put("kind", "image");
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", Map.of(
            "textAnalysisModel", workflow.getTextAnalysisModel(),
            "providerModel", workflow.getImageModel()
        ));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/keyframes",
            "fileStem", "character-" + slot.syntheticClipIndex() + "-sheet-v" + versionNo
        ));
        return request;
    }

    private Map<String, Object> buildKeyframeRunRequest(
        StageWorkflowEntity workflow,
        Map<String, Object> clip,
        int clipIndex,
        int versionNo,
        String prompt,
        String referenceImageUrl,
        String frameRole,
        String fileStem
    ) {
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", composeVisualPrompt(workflow, firstNonBlank(
            prompt,
            stringValue(clip.get("imagePrompt")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("lastFramePrompt")),
            stringValue(clip.get("videoPrompt")),
            stringValue(clip.get("scene"))
        )));
        int[] dimensions = dimensionsFromAspectRatio(workflow.getAspectRatio());
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", trimmed(frameRole, "first"));
        if (!isBlank(referenceImageUrl)) {
            input.put("referenceImageUrl", referenceImageUrl);
        }
        Integer keyframeSeed = resolvedKeyframeSeed(workflow);
        if (keyframeSeed != null) {
            input.put("seed", keyframeSeed);
        }
        request.put("kind", "image");
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", Map.of(
            "textAnalysisModel", workflow.getTextAnalysisModel(),
            "providerModel", workflow.getImageModel()
        ));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/keyframes",
            "fileStem", trimmed(fileStem, "clip" + clipIndex + "-" + trimmed(frameRole, "first") + "-v" + versionNo)
        ));
        return request;
    }

    private Map<String, Object> buildVideoRunRequest(
        StageWorkflowEntity workflow,
        Map<String, Object> clip,
        int clipIndex,
        int versionNo,
        String firstFrameUrl,
        String lastFrameUrl
    ) {
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", composeVisualPrompt(workflow, stringValue(clip.get("videoPrompt"))));
        input.put("videoSize", workflow.getVideoSize());
        input.put("durationSeconds", intValue(clip.get("targetDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("minDurationSeconds", intValue(clip.get("minDurationSeconds"), workflow.getMinDurationSeconds()));
        input.put("maxDurationSeconds", intValue(clip.get("maxDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("firstFrameUrl", firstFrameUrl);
        if (!isBlank(lastFrameUrl)) {
            input.put("lastFrameUrl", lastFrameUrl);
        }
        input.put("generateAudio", true);
        input.put("returnLastFrame", true);
        Integer videoSeed = resolvedVideoSeed(workflow);
        if (videoSeed != null) {
            input.put("seed", videoSeed);
        }
        request.put("kind", "video");
        request.put("auth", Map.of("userId", workflow.getOwnerUserId()));
        request.put("input", input);
        request.put("model", Map.of(
            "textAnalysisModel", workflow.getTextAnalysisModel(),
            "visionModel", workflow.getVisionModel(),
            "providerModel", workflow.getVideoModel()
        ));
        request.put("options", Map.of("stylePreset", workflow.getStylePreset()));
        request.put("storage", Map.of(
            "relativeDir", workflowRelativeDir(workflow.getWorkflowId()) + "/videos",
            "fileStem", "clip" + clipIndex + "-v" + versionNo
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
        asset.setThirdPartyUrl(remoteUrl);
        asset.setRemoteUrl(remoteUrl);
        asset.setMetadataJson(WorkflowJsonSupport.write(extraMetadata));
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
            int clipIndex = intValue(raw.get("clipIndex"), index + 1);
            String startFrame = firstNonBlank(
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
            row.put("firstFramePrompt", firstNonBlank(stringValue(raw.get("firstFramePrompt")), startFrame));
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
        Map<String, Object> outputSummary = stageOutputSummary(keyframeVersion);
        return firstNonBlank(
            stringValue(outputSummary.get("startFrameRemoteUrl")),
            stringValue(outputSummary.get("firstFrameRemoteUrl")),
            resolveGeneratedFrameRemoteUrl(keyframeVersion, "first"),
            stringValue(outputSummary.get("startFrameUrl")),
            stringValue(outputSummary.get("firstFrameUrl")),
            stringValue(outputSummary.get("fileUrl")),
            keyframeVersion.getDownloadUrl()
        );
    }

    private String resolveWorkflowVideoLastFrameUrl(StageVersionEntity keyframeVersion) {
        Map<String, Object> outputSummary = stageOutputSummary(keyframeVersion);
        return firstNonBlank(
            stringValue(outputSummary.get("endFrameRemoteUrl")),
            stringValue(outputSummary.get("lastFrameRemoteUrl")),
            resolveGeneratedFrameRemoteUrl(keyframeVersion, "last"),
            resolveStageAssetRemoteUrl(keyframeVersion),
            stringValue(outputSummary.get("endFrameUrl")),
            stringValue(outputSummary.get("lastFrameUrl")),
            stringValue(outputSummary.get("fileUrl")),
            keyframeVersion.getDownloadUrl()
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
        return workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())
                && intValue(item.getClipIndex(), 0) == clipIndex
                && intValue(item.getSelected(), 0) == 1)
            .findFirst()
            .map(this::resolveWorkflowVideoLastFrameUrl)
            .orElse("");
    }

    private String resolveSelectedKeyframeEndFrameRemoteUrl(String workflowId, int clipIndex) {
        return workflowRepository.listStageVersions(workflowId).stream()
            .filter(item -> WorkflowConstants.STAGE_KEYFRAME.equals(item.getStageType())
                && intValue(item.getClipIndex(), 0) == clipIndex
                && intValue(item.getSelected(), 0) == 1)
            .findFirst()
            .map(version -> firstNonBlank(
                stringValue(stageOutputSummary(version).get("endFrameRemoteUrl")),
                stringValue(stageOutputSummary(version).get("lastFrameRemoteUrl")),
                resolveGeneratedFrameRemoteUrl(version, "last"),
                resolveStageAssetRemoteUrl(version)
            ))
            .orElse("");
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
        Map<String, Object> last = new LinkedHashMap<>();
        last.put("frameRole", "last");
        last.put("runId", stringValue(endFrameRun.get("id")));
        last.put("fileUrl", endFrameUrl);
        last.put("remoteUrl", endFrameRemoteUrl);
        last.put("modelInfo", mapValue(endFrameResult.get("modelInfo")));
        frames.add(last);
        return frames;
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
        metadata.put("variantKind", VARIANT_KIND_CHARACTER_SHEET);
        metadata.put("characterName", slot.characterName());
        metadata.put("characterAppearance", slot.characterAppearance());
        metadata.put("runId", stringValue(run.get("id")));
        metadata.put("sheetUrl", fileUrl);
        metadata.put("fileUrl", fileUrl);
        return metadata;
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
        throw badRequest("video_run_failed", message);
    }

    private String normalizedRunStatus(Map<String, Object> run) {
        return stringValue(run.get("status")).toLowerCase(Locale.ROOT);
    }

    private void validateCreateWorkflowRequest(CreateWorkflowRequest request) {
        if (request == null) {
            throw badRequest("workflow_request_invalid", "工作流请求不能为空");
        }
        requireNonBlank(request.textAnalysisModel(), "textAnalysisModel", "文本模型");
        requireNonBlank(request.visionModel(), "visionModel", "视觉模型");
        requireNonBlank(request.imageModel(), "imageModel", "关键帧模型");
        requireNonBlank(request.videoModel(), "videoModel", "视频模型");
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
        Long userId = SecurityCurrentUser.currentUserId();
        if (userId == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "unauthorized", "请先登录");
        }
        return userId;
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

    private int[] dimensionsFromAspectRatio(String aspectRatio) {
        if ("16:9".equals(trimmed(aspectRatio, ""))) {
            return new int[] {1280, 720};
        }
        return new int[] {720, 1280};
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

    private List<String> normalizeCustomTags(List<String> values) {
        if (values == null) {
            return List.of();
        }
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String item : values) {
            String value = trimmed(item, "").toLowerCase(Locale.ROOT);
            if (!value.isBlank()) {
                normalized.add(value);
            }
        }
        return new ArrayList<>(normalized);
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
        String visualConstraint = visualStyleConstraintBlock(workflow);
        String normalizedPrompt = trimmed(prompt, "");
        if (visualConstraint.isBlank()) {
            return normalizedPrompt;
        }
        if (normalizedPrompt.isBlank()) {
            return visualConstraint;
        }
        return visualConstraint + "\n" + normalizedPrompt;
    }

    private String visualStyleConstraintBlock(StageWorkflowEntity workflow) {
        String globalPrompt = workflow == null ? "" : trimmed(workflow.getGlobalPrompt(), "");
        return globalPrompt.isBlank() ? "" : "全局画风要求：" + globalPrompt;
    }

    private String resolveGeneratedMediaRemoteUrl(Map<String, Object> result) {
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        return firstNonBlank(
            stringValue(metadata.get("remoteSourceUrl")),
            stringValue(metadata.get("sourceUrl"))
        );
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
}
