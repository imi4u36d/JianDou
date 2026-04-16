package com.jiandou.api.generation.orchestration;

import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.GenerationRunKinds;
import com.jiandou.api.generation.GenerationRunStatuses;
import com.jiandou.api.generation.RemoteImageGenerationResult;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.RemoteVideoTaskSubmission;
import com.jiandou.api.generation.TextModelResponse;
import com.jiandou.api.generation.image.ImageGenerationRequest;
import com.jiandou.api.generation.image.ImageModelProvider;
import com.jiandou.api.generation.image.ImageModelProviderRegistry;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.runtime.PromptTemplateResolver;
import com.jiandou.api.generation.text.TextCompletionInvocation;
import com.jiandou.api.generation.text.TextModelProviderRegistry;
import com.jiandou.api.generation.text.VisionCompletionInvocation;
import com.jiandou.api.generation.video.VideoGenerationRequest;
import com.jiandou.api.generation.video.VideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.media.LocalMediaArtifactService.TextArtifact;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * 生成运行工厂。
 */
@Component
public class GenerationRunFactory {

    private static final List<String> VIDEO_SUCCESS_STATES = List.of("SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED");
    private static final List<String> VIDEO_FAILED_STATES = List.of("FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR");

    private final ModelRuntimePropertiesResolver modelResolver;
    private final PromptTemplateResolver promptTemplateResolver;
    private final TextModelProviderRegistry textModelProviderRegistry;
    private final ImageModelProviderRegistry imageModelProviderRegistry;
    private final VideoModelProviderRegistry videoModelProviderRegistry;
    private final GenerationRunSupport support;

    /**
     * 创建新的生成运行工厂。
     * @param modelResolver 模型解析器值
     * @param promptTemplateResolver 提示词模板解析器值
     * @param textModelClient 文本模型客户端值
     * @param imageModelProviderRegistry 图片模型 provider 注册表值
     * @param videoModelProviderRegistry 视频模型 provider 注册表值
     * @param support 支持值
     */
    public GenerationRunFactory(
        ModelRuntimePropertiesResolver modelResolver,
        PromptTemplateResolver promptTemplateResolver,
        TextModelProviderRegistry textModelProviderRegistry,
        ImageModelProviderRegistry imageModelProviderRegistry,
        VideoModelProviderRegistry videoModelProviderRegistry,
        GenerationRunSupport support
    ) {
        this.modelResolver = modelResolver;
        this.promptTemplateResolver = promptTemplateResolver;
        this.textModelProviderRegistry = textModelProviderRegistry;
        this.imageModelProviderRegistry = imageModelProviderRegistry;
        this.videoModelProviderRegistry = videoModelProviderRegistry;
        this.support = support;
    }

    /**
     * 创建探测运行。
     * @param runId 运行标识值
     * @param request 请求体
     * @return 处理结果
     */
    public Map<String, Object> createProbeRun(String runId, Map<String, Object> request) {
        String requestedModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        List<Map<String, Object>> callChain = new ArrayList<>();
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("requestedModel", requestedModel);
        metadata.put("resolvedModel", profile.modelName());
        metadata.put("provider", profile.provider());
        metadata.put("family", GenerationModelKinds.TEXT);
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
            result.put("kind", GenerationRunKinds.PROBE);
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, GenerationRunKinds.PROBE, request, result, "resultProbe");
        }
        try {
            TextModelResponse response = textModelProviderRegistry.resolve(profile).generate(
                profile,
                new TextCompletionInvocation(
                    "你是模型探活助手。只返回 OK。",
                    "请确认你可以正常接收文本请求，只输出 OK。",
                    0.0,
                    16
                )
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
            result.put("kind", GenerationRunKinds.PROBE);
            result.put("ready", true);
            result.put("latencyMs", response.latencyMs());
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, GenerationRunKinds.PROBE, request, result, "resultProbe");
        } catch (RuntimeException ex) {
            metadata.put("latencyMs", 0);
            metadata.put("messagePreview", support.truncateText(ex.getMessage(), 120));
            callChain.add(support.callLog("probe", "probe.failed", "error", "文本模型探活失败。", Map.of("error", support.truncateText(ex.getMessage(), 240))));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", GenerationRunKinds.PROBE);
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return support.runEnvelope(runId, GenerationRunKinds.PROBE, request, result, "resultProbe");
        }
    }

    /**
     * 创建脚本运行。
     * @param runId 运行标识值
     * @param request 请求体
     * @return 处理结果
     */
    public Map<String, Object> createScriptRun(String runId, Map<String, Object> request) {
        String sourceText = support.nestedValue(request, "input", "text", "");
        String visualStyle = support.nestedValue(request, "options", "visualStyle", "AI 自动决策");
        String requestedModel = support.requiredModel(support.nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        if (sourceText.isBlank()) {
            throw new IllegalArgumentException("脚本输入文本不能为空");
        }
        String prompt = buildScriptUserPrompt(sourceText, visualStyle);
        List<Map<String, Object>> callChain = new ArrayList<>();
        GenerationRunSupport.TextGenerationAttempt scriptAttempt = support.generateTextWithFallback(
            profile,
            "script",
            buildScriptSystemPrompt(),
            prompt,
            support.boundedTemperature(profile.temperature(), 0.1, 0.4),
            Math.max(800, profile.maxTokens()),
            callChain
        );
        TextModelResponse response = scriptAttempt.response();
        String scriptMarkdown = support.stripMarkdownFence(response.text());
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
        TextArtifact markdownArtifact = support.writeTextArtifact(runId, request, "script.md", scriptMarkdown);
        Map<String, Object> modelInfo = support.buildModelInfo(
            scriptAttempt.profile(),
            requestedModel,
            "script",
            scriptAttempt.response(),
            "spring-text-script"
        );
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("visualStyle", visualStyle);
        metadata.put("scriptMarkdown", scriptMarkdown);
        metadata.put("fileUrl", markdownArtifact.publicUrl());
        metadata.put("configSource", profile.source());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", GenerationRunKinds.SCRIPT);
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
        return support.runEnvelope(runId, GenerationRunKinds.SCRIPT, request, result, "resultScript");
    }

    /**
     * 创建图像运行。
     * @param runId 运行标识值
     * @param request 请求体
     * @return 处理结果
     */
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
        MediaProviderProfile imageProfile = modelResolver.resolveMediaProfile(requestedImageModel, GenerationModelKinds.IMAGE);
        Integer appliedImageSeed = imageProfile.supportsSeed() ? requestedSeed : null;
        List<Map<String, Object>> callChain = new ArrayList<>();
        GenerationRunSupport.TextGenerationAttempt keyframeAttempt = null;
        String keyframePrompt = prompt;
        String negativePrompt = "";
        String shapedPrompt = keyframePrompt;
        ImageModelProvider imageModelProvider = imageModelProviderRegistry.resolve(imageProfile);
        RemoteImageGenerationResult remoteImage = imageModelProvider.generate(
            imageProfile,
            new ImageGenerationRequest(
                requestedImageModel,
                shapedPrompt,
                width,
                height,
                appliedImageSeed
            )
        );
        GenerationRunSupport.BinaryArtifact imageArtifact = support.writeBinaryArtifact(
            runId,
            request,
            GenerationModelKinds.IMAGE,
            support.extensionFromMimeOrUrl(remoteImage.mimeType(), remoteImage.remoteSourceUrl(), GenerationModelKinds.IMAGE),
            remoteImage.data()
        );
        callChain.add(support.callLog("generation", "image.generated", "success", "远端图片已生成并保存到本地存储。", Map.of(
            "provider", remoteImage.provider(),
            "providerModel", remoteImage.providerModel(),
            "endpointHost", remoteImage.endpointHost()
        )));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", GenerationRunKinds.IMAGE);
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
            GenerationModelKinds.IMAGE,
            null,
            null,
            remoteImage.providerModel(),
            remoteImage.endpointHost(),
            "",
            "spring-remote-image"
        ));
        result.put("callChain", callChain);
        return support.runEnvelope(runId, GenerationRunKinds.IMAGE, request, result, "resultImage");
    }

    /**
     * 创建视频运行。
     * @param runId 运行标识值
     * @param request 请求体
     * @return 处理结果
     */
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
        MediaProviderProfile videoProfile = modelResolver.resolveMediaProfile(requestedVideoModel, GenerationModelKinds.VIDEO);
        int durationSeconds = normalizeVideoDurationSeconds(
            videoProfile,
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
        Integer appliedVisionSeed = visionProfile.supportsSeed() ? requestedSeed : null;
        Integer appliedVideoSeed = videoProfile.supportsSeed() ? requestedSeed : null;
        List<Map<String, Object>> callChain = new ArrayList<>();
        TextModelResponse visionResponse = null;
        String visionAnalysisNotes = "";
        if (!firstFrameUrl.isBlank()) {
            List<String> images = new ArrayList<>();
            images.add(firstFrameUrl);
            if (!lastFrameUrl.isBlank()) {
                images.add(lastFrameUrl);
            }
            visionResponse = textModelProviderRegistry.resolve(visionProfile).generate(
                visionProfile,
                new VisionCompletionInvocation(
                    buildVisionAnalysisSystemPrompt("video"),
                    buildVisionAnalysisUserPrompt("video", prompt, stylePreset),
                    0.2,
                    640,
                    images,
                    appliedVisionSeed
                )
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
        VideoModelProvider videoModelProvider = videoModelProviderRegistry.resolve(videoProfile);
        RemoteVideoTaskSubmission submission = videoModelProvider.submit(
            videoProfile,
            new VideoGenerationRequest(
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
        result.put("kind", GenerationRunKinds.VIDEO);
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
            GenerationModelKinds.VIDEO,
            null,
            visionResponse,
            submission.providerModel(),
            submission.endpointHost(),
            submission.taskEndpointHost(),
            "spring-remote-video-async"
        ));
        result.put("callChain", callChain);
        return support.runEnvelope(runId, GenerationRunKinds.VIDEO, request, result, "resultVideo", GenerationRunStatuses.RUNNING);
    }

    /**
     * 处理refresh视频运行。
     * @param run 运行值
     * @return 处理结果
     */
    public Map<String, Object> refreshVideoRun(Map<String, Object> run) {
        if (!GenerationRunKinds.VIDEO.equalsIgnoreCase(support.stringValue(run.get("kind")))) {
            return run;
        }
        String status = support.stringValue(run.get("status")).toLowerCase(Locale.ROOT);
        if (!GenerationRunStatuses.isActive(status)) {
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
        VideoModelProvider videoModelProvider = videoModelProviderRegistry.resolve(profile);
        RemoteTaskQueryResult query = videoModelProvider.query(profile, taskId);
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
                support.updateRunStatus(run, GenerationRunStatuses.RUNNING);
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
            support.updateRunStatus(run, GenerationRunStatuses.SUCCEEDED);
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
            support.updateRunStatus(run, GenerationRunStatuses.FAILED);
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
        support.updateRunStatus(run, GenerationRunStatuses.RUNNING);
        return run;
    }

    /**
     * 规范化视频时长Seconds。
     * @param requestedVideoModel requested视频模型值
     * @param requestedDurationSeconds requested时长Seconds值
     * @param requestedMinDurationSeconds requested最小时长Seconds值
     * @param requestedMaxDurationSeconds requested最大时长Seconds值
     * @return 处理结果
     */
    private int normalizeVideoDurationSeconds(
        MediaProviderProfile videoProfile,
        int requestedDurationSeconds,
        int requestedMinDurationSeconds,
        int requestedMaxDurationSeconds
    ) {
        int normalizedRequested = Math.max(1, requestedDurationSeconds);
        int normalizedMin = Math.max(1, Math.min(requestedMinDurationSeconds, requestedMaxDurationSeconds));
        int normalizedMax = Math.max(normalizedMin, Math.max(requestedMinDurationSeconds, requestedMaxDurationSeconds));
        List<Integer> supportedDurations = videoProfile.supportedDurations();
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

    /**
     * 处理closestSupported时长。
     * @param candidates candidates值
     * @param requestedDurationSeconds requested时长Seconds值
     * @return 处理结果
     */
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

    /**
     * 构建脚本系统提示词。
     * @return 处理结果
     */
    private String buildScriptSystemPrompt() {
        String configuredPrompt = promptTemplateResolver.systemPrompt("script", "short_drama_script");
        if (configuredPrompt.isBlank()) {
            throw new IllegalStateException("short_drama_script system prompt missing or blank in config/prompts/script.yml");
        }
        return configuredPrompt;
    }

    /**
     * 构建脚本User提示词。
     * @param sourceText 来源文本值
     * @param visualStyle visual风格值
     * @return 处理结果
     */
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

            请严格遵循 system prompt 的输出格式与规则，不要输出解释性文字。
            """.formatted(styleLine, sourceText);
    }

    /**
     * 构建视觉分析系统提示词。
     * @param mediaKind 媒体类型值
     * @return 处理结果
     */
    private String buildVisionAnalysisSystemPrompt(String mediaKind) {
        return """
            你是影视连续性审校助手。结合用户剧情与图片输出两行内容：
            1. 画面确认：当前画面关键可保留事实。
            2. 连续性要求：后续%s生成必须保持或修正的要点。
            """.formatted("video".equals(mediaKind) ? "视频" : "图片");
    }

    /**
     * 构建视觉分析User提示词。
     * @param mediaKind 媒体类型值
     * @param prompt 提示词值
     * @param stylePreset 风格预设值
     * @return 处理结果
     */
    private String buildVisionAnalysisUserPrompt(String mediaKind, String prompt, String stylePreset) {
        return """
            请结合图片分析当前视觉内容，并为后续%s生成提炼约束。
            风格预设：%s。
            剧情任务：
            %s
            """.formatted("video".equals(mediaKind) ? "视频" : "图片", stylePreset, prompt);
    }

    /**
     * 构建Negative提示词。
     * @param mediaKind 媒体类型值
     * @return 处理结果
     */
    private String buildNegativePrompt(String mediaKind) {
        String videoOnly = GenerationModelKinds.VIDEO.equals(mediaKind)
            ? "不要新增对白，不要口型和说话主体错位，不要在片段前0.5秒和后0.5秒安排人声对白或独白，不要出现违背基本物理规律的动作、重力、碰撞、液体、烟雾或光影表现。"
            : "不要把脚本文字、镜头编号直接画进画面，不要出现违背基本物理规律的人体姿态、重力关系或空间透视。";
        return "禁止字幕、水印、比例失调、手指异常、五官崩坏、角色互换、穿模、空间透视错乱。" + videoOnly;
    }

    /**
     * 处理extractLastFrameURL。
     * @param payload 附加负载数据
     * @return 处理结果
     */
    private String extractLastFrameUrl(Map<String, Object> payload) {
        String direct = findNestedString(payload, "last_frame_url", "lastFrameUrl");
        if (!direct.isBlank()) {
            return direct;
        }
        return findNestedRoleUrl(payload, "last_frame");
    }

    /**
     * 查找嵌套String。
     * @param value 待处理的值
     * @param keys keys值
     * @return 处理结果
     */
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

    /**
     * 查找嵌套RoleURL。
     * @param value 待处理的值
     * @param role role值
     * @return 处理结果
     */
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

    /**
     * 处理mutable调用Chain。
     * @param raw 原始值
     * @return 处理结果
     */
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

    /**
     * 处理long值。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private long longValue(Object value, long fallback) {
        try {
            return Long.parseLong(String.valueOf(value).trim());
        } catch (Exception ignored) {
            return fallback;
        }
    }
}
