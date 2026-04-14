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
        String requestedImageModel = support.requiredModel(support.nestedValue(request, "model", "providerModel", ""), "providerModel", "关键帧模型");
        ModelRuntimeProfile textProfile = modelResolver.resolveTextProfile(textModel);
        MediaProviderProfile imageProfile = modelResolver.resolveImageProfile(requestedImageModel);
        Integer appliedImageSeed = modelResolver.supportsSeed(requestedImageModel) ? requestedSeed : null;
        List<Map<String, Object>> callChain = new ArrayList<>();
        GenerationRunSupport.TextGenerationAttempt keyframeAttempt = null;
        String keyframePrompt = prompt;
        String negativePrompt = "";
        String shapedPrompt = keyframePrompt;
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
        metadata.put("visionAnalysisSkipped", true);
        metadata.put("referenceImageUrl", referenceImageUrl);
        metadata.put("requestedSeed", requestedSeed);
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
            null,
            imageProfile,
            requestedImageModel,
            "image",
            null,
            null,
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
        metadata.put("providerLastFrameUrl", "");
        metadata.put("lastFrameUrl", "");
        metadata.put("last_frame_url", "");
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
            String providerLastFrameUrl = extractLastFrameUrl(query.payload());
            String resolvedLastFrameUrl = support.firstNonBlank(
                providerLastFrameUrl,
                support.stringValue(metadata.get("requestedLastFrameUrl"))
            );
            metadata.put("providerPayload", query.payload());
            metadata.put("providerLastFrameUrl", providerLastFrameUrl);
            metadata.put("lastFrameUrl", resolvedLastFrameUrl);
            metadata.put("last_frame_url", resolvedLastFrameUrl);
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
            ### 🤖 AI 短剧脚本专家指令 (System Prompt)

            **Role:** 你是一位资深的 AI 短剧导演和编剧，擅长将小说、散文或故事大纲转化为具备**高度视觉一致性**、**精准分镜语言**和**节奏感**的视频生产脚本。

            **Task:**
            根据用户输入的文本，输出一份结构化的剧本。剧本必须包含：角色档案、场景设定、分镜详细描述（含 Prompt 指令）以及音效设计。

            **Constraints:**
            1. **视觉风格一致性：** 始终保持统一风格；若用户未指定，请根据题材、情绪和场景自行决策最合适的视觉方向，并在全片保持一致。
            2. **角色锚点：** 为每个角色建立固定的外貌描述词，确保在每个分镜中一致。
            3. **分镜语言：** 使用专业术语（全景、特写、俯拍、推拉摇移）。
            4. **输出格式：** 使用 Markdown 表格。
            5. **长文本覆盖：** 输入为长篇小说或长故事时，必须覆盖主线剧情的开端、发展、转折、高潮、结局，不得只输出前几段内容。
            6. **无关内容剔除：** 对正文中出现的《题外话》、疑似作者留言、读者互动、更新说明、章节广告等非剧情内容，先剔除后再进行角色提取与分镜生成。
            7. **对话还原优先：** 必须尽量还原原文中的人物对白，优先保留原句原意；仅在篇幅受限时做最小必要压缩，不得改写成摘要口吻。
            8. **完整分镜推进：** 必须按原文叙事顺序逐段推进分镜，不得跨段跳写或用一句话概括整章；关键冲突、反转、高潮段落应拆成多镜头。
            9. **镜头细节密度：** 每个分镜都要写清角色、动作、情绪变化、环境和镜头调度；有台词时优先写原句，并且每一句都必须标注说话者，不得只写裸句。
            10. **对话情感分析：** 只要该镜头存在对白或人物独白，必须额外输出“情绪/情感分析”列，概括说话者的主导情感、强度和潜台词驱动力；禁止只复述台词表面意思。
            11. **对白时序缓冲：** 若镜头内存在对白或独白，尽量不要把人声放在该段视频的前 0.5 秒和后 0.5 秒；优先把台词落在镜头中段，给开头和结尾留出动作或环境声缓冲。
            12. **物理合理性：** 画面中的动作、重心、碰撞、布料/头发摆动、液体、烟雾、光影和镜头运动必须符合基本物理规律；除非原文明确是超自然/幻想设定，否则不得出现不合理悬浮、瞬移、穿模、无因果位移等内容。即便是幻想设定，也要保持内部逻辑自洽。
            13. **长度受限策略：** 若输出长度受限，优先保留剧情推进信息、关键对白和情感判断，再压缩修饰性描写，不得省略关键台词和转折信息。
            14. **前后衔接连续：** 相邻分镜在剧情、动作和声音上必须连贯；禁止“上一镜声音戛然而止、下一镜新声音立刻硬切出现”的不连续情况，需给出自然过渡（如尾音延续、环境音桥接、渐入渐出、J-cut/L-cut）。

            #### **工作流程：**

            **第一步：角色与环境档案 (Profile)**
            - 提取文中所有核心角色，定义其：姓名、年龄、具体长相（发型、瞳色、服装）、性格特征。
            - 定义核心场景的视觉基调（如：午后阳光下的教室、阴冷的古堡室内）。

            **第二步：脚本生成 (Script)**
            生成包含以下列的表格：
            - **镜号**
            - **剧情节点/场景**
            - **景别/镜头运动** (如：特写/推镜头)
            - **视觉描述 (AI 绘图 Prompt)**：必须包含角色名、具体动作、环境细节、光影氛围。
            - **情绪/情感分析**（若该镜头有对白或独白，必须填写角色当前主导情绪、情感强度、潜台词或心理动机；无台词时可概括人物外显情绪）
            - **对话/独白**（仅保留人物对白或人物独白；每一句都必须写成“角色名：台词”或“独白：台词”，不写旁白、画外音或解说配音）
            - **音效/BGM 建议**（需写明与前后镜头的声音衔接方式；若有对白/独白，要体现前 0.5 秒和后 0.5 秒尽量留白或仅保留环境声）
            - **建议时长**（必须写成具体几s）
            - 镜号需连续递增，并严格按剧情推进顺序排列；若文本很长，先保证剧情与对白覆盖完整，再保证镜头细节密度与转场连贯性。

            #### **输出示例格式：**

            **【角色档案】**
            * **角色 A：** [姓名]，[外貌细节描述]，[核心标签]。

            **【分镜脚本】**
            | 镜号 | 剧情节点/场景 | 景别 | 视觉描述 (Visual Prompt) | 情绪/情感分析 | 对话/独白 | 音效/BGM | 建议时长 |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            | 001 | 开端·森林清晨 | 远景 | 晨曦照进森林，光点在草地上跳跃，日系手绘感，清新明亮，草叶与薄雾运动自然，受晨风影响符合物理逻辑。 | 平静里带一丝苏醒后的惘然，情绪强度低，像在试探周遭是否安全。 | 独白：清晨，林间起风。 | 前 0.5 秒仅保留轻风与鸟鸣，中段进入独白，尾 0.5 秒回到环境声并自然延续到下一镜 | 6秒 |
            | 002 | 苏醒·角色初登场 | 特写 | [角色名] 睁开眼，淡褐色双眸，长发散乱，露出惊讶的神色，呼吸起伏和发丝摆动自然。 | 惊惧和困惑迅速上升，情绪强度中高，潜台词是“我不该出现在这里”。 | [角色名]：这...这是哪里？ | 开头 0.5 秒承接上一镜风声与呼吸声，中段说出台词，结尾 0.5 秒只留喘息和 BGM 轻微上扬，避免硬切 | 4秒 |

            请根据用户给出的正文直接产出最终脚本，不要输出额外解释。
            """;
    }

    private String buildScriptUserPrompt(String sourceText, String visualStyle) {
        String styleLine = "AI 自动决策".equalsIgnoreCase(visualStyle) || visualStyle.isBlank()
            ? "请根据题材自动选择并保持统一风格。"
            : "额外视觉风格要求：" + visualStyle + "。";
        return """
            # 任务输入
            %s

            【小说内容】：
            %s

            ---

            请输出可直接进入分镜解析流程的 markdown，不要输出解释性文字。
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
            "## 【角色档案】",
            "* **角色 A：** 主体，依据正文补足外貌细节与核心标签。",
            "",
            "## 【场景设定】",
            "- 风格：" + visualStyle,
            "- 生成方式：Spring 本地兜底。",
            "",
            "## 原文摘要",
            preview,
            "",
            "## 【分镜脚本】",
            "| 镜号 | 剧情节点/场景 | 景别/镜头运动 | 视觉描述 (Visual Prompt) | 情绪/情感分析 | 对话/独白 | 音效/BGM | 建议时长 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| 001 | 开场建立人物与环境 | 中景/平稳推进 | 主角置身核心场景，人物外观稳定，动作与环境关系清楚，光影风格统一，运动与重心符合物理规律。 | 克制而低压的观察状态，情绪强度低，仍在试探环境。 | 独白：…… | 前0.5秒先铺环境底噪，中段进入独白，尾0.5秒回落到环境声并自然延续到下一镜。 | 6s |"
        );
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
            ? "不要新增对白，不要口型和说话主体错位，不要在片段前0.5秒和后0.5秒安排人声对白或独白，不要出现违背基本物理规律的动作、重力、碰撞、液体、烟雾或光影表现。"
            : "不要把脚本文字、镜头编号直接画进画面，不要出现违背基本物理规律的人体姿态、重力关系或空间透视。";
        return "禁止字幕、水印、比例失调、手指异常、五官崩坏、角色互换、穿模、空间透视错乱。" + videoOnly;
    }

    private boolean isSeedanceProvider(String provider) {
        return support.stringValue(provider).toLowerCase(Locale.ROOT).contains("seedance");
    }

    private String extractLastFrameUrl(Map<String, Object> payload) {
        String direct = findNestedString(payload, "last_frame_url", "lastFrameUrl");
        if (!direct.isBlank()) {
            return direct;
        }
        return findNestedRoleUrl(payload, "last_frame");
    }

    @SuppressWarnings("unchecked")
    private String findNestedString(Object value, String... keys) {
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> map = (Map<String, Object>) rawMap;
            for (String key : keys) {
                Object candidate = map.get(key);
                if (candidate instanceof String text && !text.isBlank()) {
                    return text.trim();
                }
                if (candidate instanceof Map<?, ?> nestedMap) {
                    String nested = findNestedString(nestedMap, "url", "href", "uri");
                    if (!nested.isBlank()) {
                        return nested;
                    }
                }
            }
            for (Object nested : map.values()) {
                String resolved = findNestedString(nested, keys);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String resolved = findNestedString(item, keys);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private String findNestedRoleUrl(Object value, String role) {
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> map = (Map<String, Object>) rawMap;
            String currentRole = support.stringValue(map.get("role")).toLowerCase(Locale.ROOT);
            if (role.equals(currentRole)) {
                Object imageUrl = map.get("image_url");
                if (imageUrl == null) {
                    imageUrl = map.get("imageUrl");
                }
                String resolved = findNestedString(imageUrl, "url", "href", "uri");
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
            for (Object nested : map.values()) {
                String resolved = findNestedRoleUrl(nested, role);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String resolved = findNestedRoleUrl(item, role);
                if (!resolved.isBlank()) {
                    return resolved;
                }
            }
        }
        return "";
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
