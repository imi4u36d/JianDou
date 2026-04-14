package com.jiandou.api.generation;

import com.jiandou.api.media.LocalMediaArtifactService.TextArtifact;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class GenerationRunFactory {

    private static final List<String> VIDEO_SUCCESS_STATES = List.of("SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED");
    private static final List<String> VIDEO_FAILED_STATES = List.of("FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR");

    private final ModelRuntimePropertiesResolver modelResolver;
    private final PromptTemplateResolver promptTemplateResolver;
    private final CompatibleTextModelClient textModelClient;
    private final RemoteMediaGenerationClient remoteMediaGenerationClient;
    private final GenerationRunSupport support;

    public GenerationRunFactory(
        ModelRuntimePropertiesResolver modelResolver,
        PromptTemplateResolver promptTemplateResolver,
        CompatibleTextModelClient textModelClient,
        RemoteMediaGenerationClient remoteMediaGenerationClient,
        GenerationRunSupport support
    ) {
        this.modelResolver = modelResolver;
        this.promptTemplateResolver = promptTemplateResolver;
        this.textModelClient = textModelClient;
        this.remoteMediaGenerationClient = remoteMediaGenerationClient;
        this.support = support;
    }

    public Map<String, Object> createProbeRun(String runId, Map<String, Object> request) {
        String requestedModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        List<Map<String, Object>> callChain = new ArrayList<>();
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("requestedModel", requestedModel);
        metadata.put("resolvedModel", profile.modelName());
        metadata.put("provider", profile.provider());
        metadata.put("family", "text");
        metadata.put("mode", "probe");
        metadata.put("endpointHost", profile.endpointHost());
        metadata.put("checkedAt", support.nowIso());
        metadata.put("configSource", profile.source());
        if (!profile.ready()) {
            metadata.put("latencyMs", 0);
            metadata.put("messagePreview", "text model config missing");
            callChain.add(support.callLog("probe", "probe.config_missing", "error", "文本模型配置不完整。", Map.of("source", profile.source())));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", "probe");
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, "probe", request, result, "resultProbe");
        }
        try {
            TextModelResponse response = textModelClient.generateText(
                profile,
                "你是模型探活助手。只返回 OK。",
                "请确认你可以正常接收文本请求，只输出 OK。",
                0.0,
                16
            );
            metadata.put("latencyMs", response.latencyMs());
            metadata.put("endpointHost", response.endpointHost());
            metadata.put("messagePreview", support.truncateText(response.text(), 80));
            callChain.add(support.callLog("probe", "probe.completed", "success", "文本模型探活已完成。", Map.of(
                "latencyMs", response.latencyMs(),
                "responsesApi", response.responsesApi()
            )));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", "probe");
            result.put("ready", true);
            result.put("latencyMs", response.latencyMs());
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, "probe", request, result, "resultProbe");
        } catch (RuntimeException ex) {
            metadata.put("latencyMs", 0);
            metadata.put("messagePreview", support.truncateText(ex.getMessage(), 120));
            callChain.add(support.callLog("probe", "probe.failed", "error", "文本模型探活失败。", Map.of("error", support.truncateText(ex.getMessage(), 240))));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", "probe");
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, "probe", request, result, "resultProbe");
        }
    }

    public Map<String, Object> createScriptRun(String runId, Map<String, Object> request) {
        String sourceText = support.nestedValue(request, "input", "text", "");
        String visualStyle = support.nestedValue(request, "options", "visualStyle", "AI 自动决策");
        String requestedModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        String prompt = buildScriptUserPrompt(sourceText, visualStyle);
        List<Map<String, Object>> callChain = new ArrayList<>();
        String scriptMarkdown;
        GenerationRunSupport.TextGenerationAttempt scriptAttempt = null;
        if (sourceText.isBlank()) {
            scriptMarkdown = buildFallbackScriptMarkdown(sourceText, visualStyle);
            callChain.add(support.callLog("script", "script.fallback", "retry", "输入为空，返回本地占位脚本。", Map.of("source", "spring-local")));
        } else {
            scriptAttempt = support.generateTextWithFallback(
                profile,
                "script",
                buildScriptSystemPrompt(),
                prompt,
                support.boundedTemperature(profile.temperature(), 0.1, 0.4),
                Math.max(800, profile.maxTokens()),
                callChain
            );
            TextModelResponse response = scriptAttempt.response();
            scriptMarkdown = support.stripMarkdownFence(response.text());
            callChain.add(support.callLog("script", "script.requested", "success", "脚本生成请求已发送到文本模型。", Map.of(
                "provider", scriptAttempt.profile().provider(),
                "modelName", scriptAttempt.profile().modelName(),
                "endpointHost", response.endpointHost()
            )));
            callChain.add(support.callLog("script", "script.completed", "success", "脚本生成已完成。", Map.of(
                "latencyMs", response.latencyMs(),
                "responsesApi", response.responsesApi(),
                "responseId", response.responseId()
            )));
        }
        TextArtifact markdownArtifact = support.writeTextArtifact(runId, request, "script.md", scriptMarkdown);
        Map<String, Object> modelInfo = support.buildModelInfo(
            scriptAttempt == null ? profile : scriptAttempt.profile(),
            requestedModel,
            "script",
            scriptAttempt == null ? null : scriptAttempt.response(),
            "spring-text-script"
        );
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("visualStyle", visualStyle);
        metadata.put("scriptMarkdown", scriptMarkdown);
        metadata.put("fileUrl", markdownArtifact.publicUrl());
        metadata.put("configSource", profile.source());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", "script");
        result.put("sourceText", sourceText);
        result.put("visualStyle", visualStyle);
        result.put("prompt", prompt);
        result.put("outputFormat", "markdown");
        result.put("scriptMarkdown", scriptMarkdown);
        result.put("markdownPath", markdownArtifact.absolutePath());
        result.put("markdownUrl", markdownArtifact.publicUrl());
        result.put("mimeType", "text/markdown");
        result.put("callChain", callChain);
        result.put("metadata", metadata);
        result.put("modelInfo", modelInfo);
        return support.runEnvelope(runId, "script", request, result, "resultScript");
    }

    public Map<String, Object> createImageRun(String runId, Map<String, Object> request) {
        String prompt = support.nestedValue(request, "input", "prompt", "");
        String referenceImageUrl = support.nestedValue(request, "input", "referenceImageUrl", "");
        String frameRole = support.normalizeFrameRole(support.nestedValue(request, "input", "frameRole", "first"));
        int width = support.nestedInt(request, "input", "width", 1024);
        int height = support.nestedInt(request, "input", "height", 1024);
        Integer requestedSeed = support.nestedNullableInt(request, "input", "seed");
        String stylePreset = support.nestedValue(request, "options", "stylePreset", modelResolver.value("catalog.defaults", "style_preset", "cinematic"));
        String textModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        String requestedVisionModel = support.requiredModel(support.nestedValue(request, "model", "visionModel", ""), "visionModel", "视觉模型");
        String requestedImageModel = support.requiredModel(support.nestedValue(request, "model", "providerModel", ""), "providerModel", "关键帧模型");
        ModelRuntimeProfile textProfile = modelResolver.resolveTextProfile(textModel);
        ModelRuntimeProfile visionProfile = modelResolver.resolveTextProfile(requestedVisionModel);
        MediaProviderProfile imageProfile = modelResolver.resolveImageProfile(requestedImageModel);
        Integer appliedVisionSeed = modelResolver.supportsSeed(requestedVisionModel) ? requestedSeed : null;
        Integer appliedImageSeed = modelResolver.supportsSeed(requestedImageModel) ? requestedSeed : null;
        List<Map<String, Object>> callChain = new ArrayList<>();
        TextModelResponse visionResponse = null;
        String visionAnalysisNotes = "";
        if (!referenceImageUrl.isBlank()) {
            visionResponse = textModelClient.generateVisionText(
                visionProfile,
                buildVisionAnalysisSystemPrompt("image"),
                buildVisionAnalysisUserPrompt("image", prompt, stylePreset),
                List.of(referenceImageUrl),
                0.2,
                480,
                appliedVisionSeed
            );
            visionAnalysisNotes = support.stripMarkdownFence(visionResponse.text());
            callChain.add(support.callLog("vision", "image.reference_analyzed", "success", "视觉模型已完成参考帧分析。", Map.of(
                "latencyMs", visionResponse.latencyMs(),
                "endpointHost", visionResponse.endpointHost(),
                "modelName", visionProfile.modelName()
            )));
        }
        GenerationRunSupport.TextGenerationAttempt keyframeAttempt = prompt.isBlank() ? null : support.generateTextWithFallback(
            textProfile,
            "image.keyframe_prompt",
            buildKeyframePromptSystemPrompt(),
            buildKeyframePromptUserPrompt(prompt, stylePreset, width, height, frameRole, visionAnalysisNotes),
            support.boundedTemperature(textProfile.temperature(), 0.1, 0.25),
            Math.min(Math.max(textProfile.maxTokens() / 2, 320), 1400),
            callChain
        );
        TextModelResponse keyframeResponse = keyframeAttempt == null ? null : keyframeAttempt.response();
        String keyframePrompt = keyframeResponse == null ? prompt : support.stripMarkdownFence(keyframeResponse.text());
        if (keyframeResponse != null) {
            callChain.add(support.callLog("prompt", "image.keyframe_prompt_generated", "success", "关键帧提示词已通过文本模型生成。", Map.of(
                "latencyMs", keyframeResponse.latencyMs(),
                "endpointHost", keyframeResponse.endpointHost(),
                "modelName", keyframeAttempt.profile().modelName(),
                "frameRole", frameRole
            )));
        }
        String negativePrompt = buildNegativePrompt("image");
        String shapedPrompt = support.appendNegativePrompt(keyframePrompt, negativePrompt);
        RemoteImageGenerationResult remoteImage = remoteMediaGenerationClient.generateSeedreamImage(
            imageProfile,
            requestedImageModel,
            shapedPrompt,
            width,
            height,
            appliedImageSeed
        );
        GenerationRunSupport.BinaryArtifact imageArtifact = support.writeBinaryArtifact(
            runId,
            request,
            "image",
            support.extensionFromMimeOrUrl(remoteImage.mimeType(), remoteImage.remoteSourceUrl(), "image"),
            remoteImage.data()
        );
        callChain.add(support.callLog("generation", "image.generated", "success", "远端图片已生成并保存到本地存储。", Map.of(
            "provider", remoteImage.provider(),
            "providerModel", remoteImage.providerModel(),
            "endpointHost", remoteImage.endpointHost()
        )));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", "image");
        result.put("prompt", prompt);
        result.put("frameRole", frameRole);
        result.put("keyframePrompt", keyframePrompt);
        result.put("shapedPrompt", shapedPrompt);
        result.put("negativePrompt", negativePrompt);
        result.put("outputUrl", imageArtifact.publicUrl());
        result.put("mimeType", remoteImage.mimeType());
        result.put("width", width);
        result.put("height", height);
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("stylePreset", stylePreset);
        metadata.put("outputUrl", imageArtifact.publicUrl());
        metadata.put("fileUrl", imageArtifact.publicUrl());
        metadata.put("source", "remote:" + remoteImage.providerModel());
        metadata.put("remoteSourceUrl", remoteImage.remoteSourceUrl());
        metadata.put("frameRole", frameRole);
        metadata.put("keyframePrompt", keyframePrompt);
        metadata.put("textAnalysisProvider", textProfile.provider());
        metadata.put("textAnalysisModel", textProfile.modelName());
        metadata.put("keyframePromptProvider", keyframeAttempt == null ? textProfile.provider() : keyframeAttempt.profile().provider());
        metadata.put("keyframePromptModel", keyframeAttempt == null ? textProfile.modelName() : keyframeAttempt.profile().modelName());
        metadata.put("promptRewriteProvider", keyframeAttempt == null ? textProfile.provider() : keyframeAttempt.profile().provider());
        metadata.put("promptRewriteModel", keyframeAttempt == null ? textProfile.modelName() : keyframeAttempt.profile().modelName());
        metadata.put("promptRewriteSkipped", true);
        metadata.put("visionAnalysisProvider", visionProfile.provider());
        metadata.put("visionAnalysisModel", visionProfile.modelName());
        metadata.put("visionAnalysisEndpointHost", visionResponse == null ? visionProfile.endpointHost() : visionResponse.endpointHost());
        metadata.put("visionAnalysisNotes", visionAnalysisNotes);
        metadata.put("referenceImageUrl", referenceImageUrl);
        metadata.put("requestedSeed", requestedSeed);
        metadata.put("visionAnalysisSeed", appliedVisionSeed);
        metadata.put("imageGenerationSeed", appliedImageSeed);
        metadata.put("watermark", false);
        metadata.put("configSource", imageProfile.source());
        metadata.put("provider", remoteImage.provider());
        metadata.put("providerModel", remoteImage.providerModel());
        metadata.put("requestedSize", remoteImage.requestedSize());
        result.put("metadata", metadata);
        result.put("modelInfo", support.buildMediaModelInfo(
            textProfile,
            keyframeAttempt == null ? textProfile : keyframeAttempt.profile(),
            visionProfile,
            imageProfile,
            requestedImageModel,
            "image",
            keyframeResponse,
            visionResponse,
            remoteImage.providerModel(),
            remoteImage.endpointHost(),
            "",
            "spring-remote-image"
        ));
        result.put("callChain", callChain);
        return support.runEnvelope(runId, "image", request, result, "resultImage");
    }

    public Map<String, Object> createVideoRun(String runId, Map<String, Object> request) {
        String prompt = support.nestedValue(request, "input", "prompt", "");
        int[] dimensions = support.parseDimensions(
            support.nestedValue(request, "input", "videoSize", ""),
            support.nestedInt(request, "input", "width", 720),
            support.nestedInt(request, "input", "height", 1280)
        );
        int width = dimensions[0];
        int height = dimensions[1];
        int requestedDurationSeconds = support.nestedInt(request, "input", "durationSeconds", 8);
        int requestedMinDurationSeconds = support.nestedInt(request, "input", "minDurationSeconds", requestedDurationSeconds);
        int requestedMaxDurationSeconds = support.nestedInt(request, "input", "maxDurationSeconds", requestedDurationSeconds);
        Integer requestedSeed = support.nestedNullableInt(request, "input", "seed");
        String stylePreset = support.nestedValue(request, "options", "stylePreset", modelResolver.value("catalog.defaults", "style_preset", "cinematic"));
        String textModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        String requestedVisionModel = support.requiredModel(support.nestedValue(request, "model", "visionModel", ""), "visionModel", "视觉模型");
        String requestedVideoModel = support.requiredModel(support.nestedValue(request, "model", "providerModel", ""), "providerModel", "视频模型");
        int durationSeconds = normalizeVideoDurationSeconds(
            requestedVideoModel,
            requestedDurationSeconds,
            requestedMinDurationSeconds,
            requestedMaxDurationSeconds
        );
        String firstFrameUrl = support.nestedValue(request, "input", "firstFrameUrl", "");
        String lastFrameUrl = support.nestedValue(request, "input", "lastFrameUrl", "");
        boolean generateAudio = support.nestedBoolean(request, "input", "generateAudio", true);
        boolean returnLastFrame = support.nestedBoolean(request, "input", "returnLastFrame", true);
        ModelRuntimeProfile textProfile = modelResolver.resolveTextProfile(textModel);
        ModelRuntimeProfile visionProfile = modelResolver.resolveTextProfile(requestedVisionModel);
        MediaProviderProfile videoProfile = modelResolver.resolveVideoProfile(requestedVideoModel);
        Integer appliedVisionSeed = modelResolver.supportsSeed(requestedVisionModel) ? requestedSeed : null;
        Integer appliedVideoSeed = modelResolver.supportsSeed(requestedVideoModel) ? requestedSeed : null;
        List<Map<String, Object>> callChain = new ArrayList<>();
        TextModelResponse visionResponse = null;
        String visionAnalysisNotes = "";
        if (!firstFrameUrl.isBlank()) {
            List<String> images = new ArrayList<>();
            images.add(firstFrameUrl);
            if (!lastFrameUrl.isBlank()) {
                images.add(lastFrameUrl);
            }
            visionResponse = textModelClient.generateVisionText(
                visionProfile,
                buildVisionAnalysisSystemPrompt("video"),
                buildVisionAnalysisUserPrompt("video", prompt, stylePreset),
                images,
                0.2,
                640,
                appliedVisionSeed
            );
            visionAnalysisNotes = support.stripMarkdownFence(visionResponse.text());
            callChain.add(support.callLog("vision", "video.reference_analyzed", "success", "视觉模型已完成首尾帧分析。", Map.of(
                "latencyMs", visionResponse.latencyMs(),
                "endpointHost", visionResponse.endpointHost(),
                "modelName", visionProfile.modelName()
            )));
        }
        String negativePrompt = buildNegativePrompt("video");
        String shapedPrompt = support.appendNegativePrompt(prompt, negativePrompt);
        boolean cameraFixed = support.nestedBoolean(request, "input", "cameraFixed", support.inferSeedanceCameraFixed(shapedPrompt, videoProfile.cameraFixed()));
        boolean watermark = support.nestedBoolean(request, "input", "watermark", videoProfile.watermark());

        RemoteVideoTaskSubmission submission = "seedance".equalsIgnoreCase(videoProfile.provider())
            ? remoteMediaGenerationClient.submitSeedanceVideoTask(
                videoProfile,
                requestedVideoModel,
                shapedPrompt,
                width,
                height,
                durationSeconds,
                firstFrameUrl,
                lastFrameUrl,
                appliedVideoSeed,
                cameraFixed,
                watermark,
                returnLastFrame,
                generateAudio
            )
            : remoteMediaGenerationClient.submitDashscopeVideoTask(
                videoProfile,
                requestedVideoModel,
                shapedPrompt,
                width,
                height,
                durationSeconds,
                appliedVideoSeed
            );

        callChain.add(support.callLog("generation", "video.submitted", "running", "远端视频任务已提交。", Map.of(
            "provider", submission.provider(),
            "providerModel", submission.providerModel(),
            "taskId", submission.taskId(),
            "endpointHost", submission.endpointHost(),
            "taskEndpointHost", submission.taskEndpointHost()
        )));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", "video");
        result.put("prompt", prompt);
        result.put("shapedPrompt", shapedPrompt);
        result.put("negativePrompt", negativePrompt);
        result.put("outputUrl", "");
        result.put("thumbnailUrl", !firstFrameUrl.isBlank() ? firstFrameUrl : "");
        result.put("mimeType", "video/mp4");
        result.put("durationSeconds", durationSeconds);
        result.put("width", width);
        result.put("height", height);
        result.put("hasAudio", generateAudio);
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("outputUrl", "");
        metadata.put("fileUrl", "");
        metadata.put("posterUrl", !firstFrameUrl.isBlank() ? firstFrameUrl : "");
        metadata.put("videoSize", support.nestedValue(request, "input", "videoSize", ""));
        metadata.put("source", "remote:" + submission.providerModel());
        metadata.put("hasAudio", generateAudio);
        metadata.put("textAnalysisProvider", textProfile.provider());
        metadata.put("textAnalysisModel", textProfile.modelName());
        metadata.put("visionAnalysisProvider", visionProfile.provider());
        metadata.put("visionAnalysisModel", visionProfile.modelName());
        metadata.put("visionAnalysisEndpointHost", visionResponse == null ? visionProfile.endpointHost() : visionResponse.endpointHost());
        metadata.put("visionAnalysisNotes", visionAnalysisNotes);
        metadata.put("configSource", videoProfile.source());
        metadata.put("remoteSourceUrl", "");
        metadata.put("provider", submission.provider());
        metadata.put("providerModel", submission.providerModel());
        metadata.put("requestedModel", requestedVideoModel);
        metadata.put("taskId", submission.taskId());
        metadata.put("firstFrameUrl", submission.firstFrameUrl());
        metadata.put("requestedLastFrameUrl", submission.requestedLastFrameUrl());
        metadata.put("lastFrameUrl", "");
        metadata.put("returnLastFrame", submission.returnLastFrame());
        metadata.put("generateAudio", submission.generateAudio());
        metadata.put("requestedDurationSeconds", requestedDurationSeconds);
        metadata.put("appliedDurationSeconds", durationSeconds);
        metadata.put("requestedSeed", requestedSeed);
        metadata.put("visionAnalysisSeed", appliedVisionSeed);
        metadata.put("videoGenerationSeed", appliedVideoSeed);
        metadata.put("cameraFixed", cameraFixed);
        metadata.put("watermark", watermark);
        metadata.put("taskStatus", "SUBMITTED");
        metadata.put("storageRelativeDir", support.storageRelativeDir(request, runId));
        metadata.put("storageFileStem", support.storageFileStem(request, "video"));
        metadata.put("nextPollAt", System.currentTimeMillis());
        result.put("metadata", metadata);
        result.put("modelInfo", support.buildMediaModelInfo(
            textProfile,
            null,
            visionProfile,
            videoProfile,
            requestedVideoModel,
            "video",
            null,
            visionResponse,
            submission.providerModel(),
            submission.endpointHost(),
            submission.taskEndpointHost(),
            "spring-remote-video-async"
        ));
        result.put("callChain", callChain);
        return support.runEnvelope(runId, "video", request, result, "resultVideo", "running");
    }

    public Map<String, Object> refreshVideoRun(Map<String, Object> run) {
        if (!"video".equalsIgnoreCase(support.stringValue(run.get("kind")))) {
            return run;
        }
        String status = support.stringValue(run.get("status")).toLowerCase(Locale.ROOT);
        if (!"running".equals(status) && !"queued".equals(status) && !"submitted".equals(status)) {
            return run;
        }
        Map<String, Object> result = support.mapValue(run.get("result"));
        if (result.isEmpty()) {
            return run;
        }
        Map<String, Object> metadata = support.mapValue(result.get("metadata"));
        String taskId = support.stringValue(metadata.get("taskId"));
        String requestedModel = support.firstNonBlank(
            support.stringValue(metadata.get("requestedModel")),
            support.stringValue(metadata.get("providerModel"))
        );
        if (taskId.isBlank() || requestedModel.isBlank()) {
            return run;
        }
        long nextPollAt = longValue(metadata.get("nextPollAt"), 0L);
        long now = System.currentTimeMillis();
        if (nextPollAt > now) {
            return run;
        }
        MediaProviderProfile profile = modelResolver.resolveVideoProfile(requestedModel);
        RemoteTaskQueryResult query = isSeedanceProvider(profile.provider())
            ? remoteMediaGenerationClient.querySeedanceTask(profile, taskId)
            : remoteMediaGenerationClient.queryDashscopeTask(profile, taskId);
        String remoteStatus = support.stringValue(query.status()).toUpperCase(Locale.ROOT);
        metadata.put("taskStatus", remoteStatus);
        if (!support.stringValue(query.message()).isBlank()) {
            metadata.put("taskMessage", query.message());
        }
        List<Map<String, Object>> callChain = mutableCallChain(result.get("callChain"));
        if (VIDEO_SUCCESS_STATES.contains(remoteStatus)) {
            String videoUrl = support.stringValue(query.videoUrl());
            if (videoUrl.isBlank()) {
                metadata.put("nextPollAt", now + Math.max(1, profile.pollIntervalSeconds()) * 1000L);
                callChain.add(support.callLog("generation", "video.poll.pending_url", "running", "任务已完成但暂未返回视频地址。", Map.of(
                    "taskId", taskId,
                    "status", remoteStatus
                )));
                result.put("callChain", callChain);
                result.put("metadata", metadata);
                run.put("result", result);
                run.put("resultVideo", result);
                support.updateRunStatus(run, "running");
                return run;
            }
            String storageRelativeDir = support.firstNonBlank(support.stringValue(metadata.get("storageRelativeDir")), "gen/_runs/" + support.stringValue(run.get("id")));
            String storageFileStem = support.firstNonBlank(support.stringValue(metadata.get("storageFileStem")), "video");
            GenerationRunSupport.BinaryArtifact artifact = support.materializeBinaryArtifact(
                support.stringValue(run.get("id")),
                storageRelativeDir,
                storageFileStem,
                videoUrl
            );
            result.put("outputUrl", artifact.publicUrl());
            result.put("mimeType", artifact.mimeType());
            result.put("hasAudio", support.nestedBoolean(Map.of("meta", metadata), "meta", "generateAudio", true));
            metadata.put("outputUrl", artifact.publicUrl());
            metadata.put("fileUrl", artifact.publicUrl());
            metadata.put("remoteSourceUrl", videoUrl);
            metadata.put("lastFrameUrl", extractLastFrameUrl(query.payload()));
            metadata.put("nextPollAt", null);
            callChain.add(support.callLog("generation", "video.completed", "success", "远端视频已完成并落盘。", Map.of(
                "taskId", taskId,
                "status", remoteStatus,
                "outputUrl", artifact.publicUrl()
            )));
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            run.put("result", result);
            run.put("resultVideo", result);
            support.updateRunStatus(run, "succeeded");
            return run;
        }
        if (VIDEO_FAILED_STATES.contains(remoteStatus)) {
            String message = support.firstNonBlank(support.stringValue(query.message()), "远端视频生成失败");
            result.put("error", message);
            metadata.put("nextPollAt", null);
            callChain.add(support.callLog("generation", "video.failed", "error", "远端视频任务失败。", Map.of(
                "taskId", taskId,
                "status", remoteStatus,
                "error", message
            )));
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            run.put("result", result);
            run.put("resultVideo", result);
            support.updateRunStatus(run, "failed");
            return run;
        }
        metadata.put("nextPollAt", now + Math.max(1, profile.pollIntervalSeconds()) * 1000L);
        callChain.add(support.callLog("generation", "video.polling", "running", "远端视频任务处理中。", Map.of(
            "taskId", taskId,
            "status", remoteStatus
        )));
        result.put("callChain", callChain);
        result.put("metadata", metadata);
        run.put("result", result);
        run.put("resultVideo", result);
        support.updateRunStatus(run, "running");
        return run;
    }

    private int normalizeVideoDurationSeconds(
        String requestedVideoModel,
        int requestedDurationSeconds,
        int requestedMinDurationSeconds,
        int requestedMaxDurationSeconds
    ) {
        int normalizedRequested = Math.max(1, requestedDurationSeconds);
        int normalizedMin = Math.max(1, Math.min(requestedMinDurationSeconds, requestedMaxDurationSeconds));
        int normalizedMax = Math.max(normalizedMin, Math.max(requestedMinDurationSeconds, requestedMaxDurationSeconds));
        Map<String, String> section = modelResolver.section("model.models.\"" + requestedVideoModel + "\"");
        List<Integer> supportedDurations = support.parseIntegerList(section.get("supported_durations"), List.of());
        if (supportedDurations.isEmpty()) {
            return normalizedRequested;
        }
        List<Integer> inRange = supportedDurations.stream()
            .filter(candidate -> candidate >= normalizedMin && candidate <= normalizedMax)
            .toList();
        if (!inRange.isEmpty()) {
            return closestSupportedDuration(inRange, normalizedRequested);
        }
        return closestSupportedDuration(supportedDurations, normalizedRequested);
    }

    private int closestSupportedDuration(List<Integer> candidates, int requestedDurationSeconds) {
        int resolved = candidates.get(0);
        int smallestDistance = Math.abs(resolved - requestedDurationSeconds);
        for (int candidate : candidates) {
            int distance = Math.abs(candidate - requestedDurationSeconds);
            if (distance < smallestDistance || (distance == smallestDistance && candidate > resolved)) {
                resolved = candidate;
                smallestDistance = distance;
            }
        }
        return resolved;
    }

    private String buildScriptSystemPrompt() {
        String configuredPrompt = promptTemplateResolver.systemPrompt("script", "short_drama_script");
        if (!configuredPrompt.isBlank()) {
            return configuredPrompt;
        }
        return """
            你是一位影视分镜脚本助手。请将输入中文内容转为可用于图生视频生产的分镜脚本表格。
            要求：
            1. 使用中文输出，保留剧情语义，不虚构超出原文的关键设定。
            2. 每个镜头同时给出 Seedream 关键帧提示词与 Seedance 动态提示词。
            3. 明确人物、景别、动作、镜头运动、光线与情绪落点。
            4. 不输出 JSON，不输出代码块，直接输出 markdown。
            """;
    }

    private String buildScriptUserPrompt(String sourceText, String visualStyle) {
        String styleLine = "AI 自动决策".equalsIgnoreCase(visualStyle) || visualStyle.isBlank()
            ? "请根据题材自动选择并保持统一风格。"
            : "额外视觉风格要求：" + visualStyle + "。";
        return """
            # Input Data
            %s

            【小说内容】：
            %s

            ---

            请开始分析并生成脚本：
            """.formatted(styleLine, sourceText);
    }

    private String buildFallbackScriptMarkdown(String sourceText, String visualStyle) {
        String normalizedText = sourceText == null ? "" : sourceText.trim();
        String preview = normalizedText.isEmpty()
            ? "暂无文本输入"
            : normalizedText.substring(0, Math.min(120, normalizedText.length()));
        return String.join("\n",
            "# 分镜脚本",
            "",
            "- 视觉风格: " + visualStyle,
            "- 生成方式: Spring 本地兜底",
            "",
            "## 原文摘要",
            preview,
            "",
            "## 镜头建议",
            "1. 开场镜头：建立人物关系和冲突背景。",
            "2. 推进镜头：承接主要动作、情绪和叙事转折。",
            "3. 收束镜头：完成情绪落点并保持声音连续。"
        );
    }

    private String buildKeyframePromptSystemPrompt() {
        String configuredPrompt = promptTemplateResolver.systemPrompt("core", "keyframe_prompt_generator");
        if (!configuredPrompt.isBlank()) {
            return configuredPrompt;
        }
        return """
            你是影视关键帧提示词设计师。请把输入分镜改写成适合关键帧生成的一段中文提示词。
            输出要求：具体、可执行、强调人物一致性与物理合理性，只输出一段提示词。
            """;
    }

    private String buildKeyframePromptUserPrompt(
        String prompt,
        String stylePreset,
        int width,
        int height,
        String frameRole,
        String visionAnalysisNotes
    ) {
        String roleLine = "last".equals(frameRole)
            ? "当前要生成尾帧关键帧。"
            : "当前要生成首帧关键帧。";
        String analysisLine = visionAnalysisNotes == null || visionAnalysisNotes.isBlank()
            ? ""
            : "\n参考图连续性分析：" + visionAnalysisNotes.trim();
        return """
            请基于下面整段分镜信息，生成一段更适合关键帧出图的中文提示词。
            风格预设：%s。
            输出尺寸：%dx%d。
            关键帧类型：%s。%s%s

            整段分镜信息：
            %s
            """.formatted(stylePreset, width, height, "last".equals(frameRole) ? "尾帧" : "首帧", roleLine, analysisLine, prompt);
    }

    private String buildVisionAnalysisSystemPrompt(String mediaKind) {
        return """
            你是影视连续性审校助手。结合用户剧情与图片输出两行内容：
            1. 画面确认：当前画面关键可保留事实。
            2. 连续性要求：后续%s生成必须保持或修正的要点。
            """.formatted("video".equals(mediaKind) ? "视频" : "图片");
    }

    private String buildVisionAnalysisUserPrompt(String mediaKind, String prompt, String stylePreset) {
        return """
            请结合图片分析当前视觉内容，并为后续%s生成提炼约束。
            风格预设：%s。
            剧情任务：
            %s
            """.formatted("video".equals(mediaKind) ? "视频" : "图片", stylePreset, prompt);
    }

    private String buildNegativePrompt(String mediaKind) {
        String videoOnly = "video".equals(mediaKind)
            ? "不要新增对白，不要口型和说话主体错位。"
            : "不要把脚本文字、镜头编号直接画进画面。";
        return "禁止字幕、水印、比例失调、手指异常、五官崩坏、角色互换、穿模、空间透视错乱。" + videoOnly;
    }

    private boolean isSeedanceProvider(String provider) {
        return support.stringValue(provider).toLowerCase(Locale.ROOT).contains("seedance");
    }

    private String extractLastFrameUrl(Map<String, Object> payload) {
        if (payload == null) {
            return "";
        }
        String value = support.firstNonBlank(
            support.stringValue(payload.get("last_frame_url")),
            support.stringValue(payload.get("lastFrameUrl"))
        );
        if (!value.isBlank()) {
            return value;
        }
        Map<String, Object> output = support.mapValue(payload.get("output"));
        return support.firstNonBlank(
            support.stringValue(output.get("last_frame_url")),
            support.stringValue(output.get("lastFrameUrl"))
        );
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> mutableCallChain(Object raw) {
        List<Map<String, Object>> items = new ArrayList<>();
        if (!(raw instanceof List<?> list)) {
            return items;
        }
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    row.put(String.valueOf(entry.getKey()), entry.getValue());
                }
                items.add(row);
            }
        }
        return items;
    }

    private long longValue(Object value, long fallback) {
        try {
            return Long.parseLong(String.valueOf(value).trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }
}
