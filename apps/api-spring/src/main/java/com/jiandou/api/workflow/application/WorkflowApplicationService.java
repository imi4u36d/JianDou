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
        workflow.setTaskSeed(request.seed());
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

    public Map<String, Object> generateStoryboard(String workflowId) {
        StageWorkflowEntity workflow = requireWorkflow(workflowId);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_STORYBOARD, 0);
        Map<String, Object> run = generationApplicationService.createRun(buildStoryboardRunRequest(workflow, versionNo));
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
        Map<String, Object> clip = requireStoryboardClip(storyboardVersion, clipIndex);
        int versionNo = workflowRepository.nextStageVersionNo(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex);
        Map<String, Object> run = generationApplicationService.createRun(buildKeyframeRunRequest(workflow, clip, clipIndex, versionNo));
        Map<String, Object> result = mapValue(run.get("result"));
        String fileUrl = firstNonBlank(stringValue(result.get("outputUrl")), stringValue(mapValue(result.get("metadata")).get("fileUrl")));
        if (fileUrl.isBlank()) {
            throw badRequest("workflow_keyframe_empty", "关键帧生成结果为空");
        }
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
            stringValue(mapValue(result.get("metadata")).get("remoteSourceUrl")),
            Map.of(
                "clip", clip,
                "frameRole", stringValue(result.get("frameRole")),
                "runId", stringValue(run.get("id"))
            )
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
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "clipIndex", clipIndex,
            "imagePrompt", stringValue(clip.get("imagePrompt")),
            "firstFramePrompt", stringValue(clip.get("firstFramePrompt"))
        )));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "clip", clip,
            "fileUrl", fileUrl,
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
        requireStageVersion(workflowId, versionId, WorkflowConstants.STAGE_KEYFRAME);
        workflowRepository.markSelectedStageVersion(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, versionId);
        syncWorkflowStageAssetSelection(workflowId, WorkflowConstants.STAGE_KEYFRAME, clipIndex, versionId);
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
        String firstFrameUrl = keyframeVersion.getDownloadUrl();
        Map<String, Object> run = generationApplicationService.createRun(buildVideoRunRequest(workflow, clip, clipIndex, versionNo, firstFrameUrl));
        run = awaitCompletedVideoRun(run);
        Map<String, Object> result = mapValue(run.get("result"));
        Map<String, Object> metadata = mapValue(result.get("metadata"));
        String fileUrl = firstNonBlank(stringValue(result.get("outputUrl")), stringValue(metadata.get("fileUrl")));
        if (fileUrl.isBlank()) {
            throw badRequest("workflow_video_empty", "视频生成结果为空");
        }
        String resolvedLastFrameUrl = firstNonBlank(stringValue(metadata.get("lastFrameUrl")), stringValue(metadata.get("requestedLastFrameUrl")));
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
            Map.of(
                "clip", clip,
                "runId", stringValue(run.get("id")),
                "firstFrameUrl", firstNonBlank(stringValue(metadata.get("firstFrameUrl")), firstFrameUrl),
                "lastFrameUrl", resolvedLastFrameUrl
            )
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
        version.setInputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "clipIndex", clipIndex,
            "videoPrompt", stringValue(clip.get("videoPrompt")),
            "keyframeAssetId", keyframeVersion.getMaterialAssetId()
        )));
        version.setOutputSummaryJson(WorkflowJsonSupport.write(Map.of(
            "clip", clip,
            "fileUrl", fileUrl,
            "durationSeconds", doubleValue(result.get("durationSeconds"), 0.0),
            "lastFrameUrl", resolvedLastFrameUrl
        )));
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
        row.put("seed", workflow.getTaskSeed());
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

    private Map<String, Object> toStageVersionRow(StageVersionEntity version, MaterialAssetEntity asset, List<MaterialAssetTagEntity> tags) {
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
        row.put("inputSummary", WorkflowJsonSupport.readMap(version.getInputSummaryJson()));
        row.put("outputSummary", WorkflowJsonSupport.readMap(version.getOutputSummaryJson()));
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

    private Map<String, Object> buildKeyframeRunRequest(StageWorkflowEntity workflow, Map<String, Object> clip, int clipIndex, int versionNo) {
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", firstNonBlank(
            stringValue(clip.get("imagePrompt")),
            stringValue(clip.get("firstFramePrompt")),
            stringValue(clip.get("videoPrompt")),
            stringValue(clip.get("scene"))
        ));
        int[] dimensions = dimensionsFromAspectRatio(workflow.getAspectRatio());
        input.put("width", dimensions[0]);
        input.put("height", dimensions[1]);
        input.put("frameRole", "first");
        if (workflow.getTaskSeed() != null) {
            input.put("seed", workflow.getTaskSeed());
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
            "fileStem", "clip" + clipIndex + "-first-v" + versionNo
        ));
        return request;
    }

    private Map<String, Object> buildVideoRunRequest(StageWorkflowEntity workflow, Map<String, Object> clip, int clipIndex, int versionNo, String firstFrameUrl) {
        Map<String, Object> request = new LinkedHashMap<>();
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("prompt", stringValue(clip.get("videoPrompt")));
        input.put("videoSize", workflow.getVideoSize());
        input.put("durationSeconds", intValue(clip.get("targetDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("minDurationSeconds", intValue(clip.get("minDurationSeconds"), workflow.getMinDurationSeconds()));
        input.put("maxDurationSeconds", intValue(clip.get("maxDurationSeconds"), workflow.getMaxDurationSeconds()));
        input.put("firstFrameUrl", firstFrameUrl);
        input.put("generateAudio", true);
        input.put("returnLastFrame", true);
        if (workflow.getTaskSeed() != null) {
            input.put("seed", workflow.getTaskSeed());
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
            row.put("firstFramePrompt", shot.firstFramePrompt());
            row.put("lastFramePrompt", shot.lastFramePrompt());
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
        return clips;
    }

    private com.jiandou.api.task.TaskRecord mockWorkflowTask(StageWorkflowEntity workflow) {
        com.jiandou.api.task.TaskRecord task = new com.jiandou.api.task.TaskRecord();
        task.setId(workflow.getWorkflowId());
        task.setTitle(workflow.getTitle());
        task.setMinDurationSeconds(workflow.getMinDurationSeconds() == null ? 5 : workflow.getMinDurationSeconds());
        task.setMaxDurationSeconds(workflow.getMaxDurationSeconds() == null ? 5 : workflow.getMaxDurationSeconds());
        task.setTaskSeed(workflow.getTaskSeed());
        return task;
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
        return listMapValue(WorkflowJsonSupport.readMap(storyboardVersion.getOutputSummaryJson()).get("clips"));
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
}
