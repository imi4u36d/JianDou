package com.jiandou.api.generation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.media.LocalMediaArtifactService;
import com.jiandou.api.media.LocalMediaArtifactService.ImageArtifact;
import com.jiandou.api.media.LocalMediaArtifactService.TextArtifact;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class DefaultGenerationApplicationService implements GenerationApplicationService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final ConcurrentHashMap<String, Map<String, Object>> runs = new ConcurrentHashMap<>();
    private final Path generationRunsDir;
    private final ObjectMapper objectMapper;
    private final LocalMediaArtifactService localMediaArtifactService;
    private final ModelRuntimePropertiesResolver modelResolver;
    private final PromptTemplateResolver promptTemplateResolver;
    private final CompatibleTextModelClient textModelClient;
    private final RemoteMediaGenerationClient remoteMediaGenerationClient;

    public DefaultGenerationApplicationService(
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot,
        ObjectMapper objectMapper,
        LocalMediaArtifactService localMediaArtifactService,
        ModelRuntimePropertiesResolver modelResolver,
        PromptTemplateResolver promptTemplateResolver,
        CompatibleTextModelClient textModelClient,
        RemoteMediaGenerationClient remoteMediaGenerationClient
    ) {
        this.generationRunsDir = Paths.get(storageRoot).toAbsolutePath().normalize().resolve("gen").resolve("_runs");
        this.objectMapper = objectMapper;
        this.localMediaArtifactService = localMediaArtifactService;
        this.modelResolver = modelResolver;
        this.promptTemplateResolver = promptTemplateResolver;
        this.textModelClient = textModelClient;
        this.remoteMediaGenerationClient = remoteMediaGenerationClient;
    }

    @Override
    public Map<String, Object> catalog() {
        String defaultPlatform = modelResolver.value("platform.defaults", "default_platform", "douyin");
        String platformSection = "platform.platforms." + defaultPlatform;
        String defaultAspectRatio = firstNonBlank(
            modelResolver.value(platformSection, "default_aspect_ratio", ""),
            modelResolver.value("platform.defaults", "default_aspect_ratio", ""),
            modelResolver.value("pipeline", "default_aspect_ratio", "9:16"),
            "9:16"
        );
        String defaultStylePreset = firstNonBlank(
            modelResolver.value(platformSection, "default_style_preset", ""),
            modelResolver.value("platform.defaults", "default_style_preset", ""),
            modelResolver.value("catalog.defaults", "style_preset", "cinematic"),
            "cinematic"
        );
        String defaultVideoSize = firstNonBlank(
            modelResolver.value(platformSection, "default_video_size", ""),
            modelResolver.value("catalog.defaults", "video_size", "720*1280"),
            "720*1280"
        );
        int defaultVideoDurationSeconds = firstPositiveInt(
            modelResolver.intValue(platformSection, "default_video_duration_seconds", 0),
            modelResolver.intValue("catalog.defaults", "video_duration_seconds", 0),
            8
        );
        String defaultImageSize = modelResolver.value("catalog.defaults", "image_size", "1024x1024");
        List<Map<String, Object>> textModels = modelResolver.listModelsByKind("text");
        List<Map<String, Object>> visionModels = modelResolver.listModelsByKind("vision");
        List<Map<String, Object>> imageModels = modelResolver.listModelsByKind("image");
        List<Map<String, Object>> videoModels = enrichVideoModels(modelResolver.listModelsByKind("video"));
        List<String> videoModelNames = videoModels.stream()
            .map(item -> String.valueOf(item.getOrDefault("value", "")).trim())
            .filter(item -> !item.isBlank())
            .toList();
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("defaultPlatform", defaultPlatform);
        payload.put("defaultAspectRatio", defaultAspectRatio);
        payload.put("aspectRatios", aspectRatioOptions());
        payload.put("stylePresets", stylePresetOptions());
        payload.put("imageSizes", imageSizeOptions());
        payload.put("textAnalysisModels", textModels);
        payload.put("defaultTextAnalysisModel", null);
        payload.put("visionModels", visionModels);
        payload.put("defaultVisionModel", null);
        payload.put("imageModels", imageModels);
        payload.put("videoModels", videoModels);
        payload.put("defaultVideoModel", null);
        payload.put("videoSizes", videoSizeOptions(videoModels, videoModelNames));
        payload.put("videoDurations", videoDurationOptions(videoModels, videoModelNames));
        payload.put("defaultStylePreset", defaultStylePreset);
        payload.put("defaultImageSize", defaultImageSize);
        payload.put("defaultVideoSize", defaultVideoSize);
        payload.put("defaultVideoDurationSeconds", defaultVideoDurationSeconds);
        payload.put("configSource", modelResolver.configSource());
        return payload;
    }

    @Override
    public Map<String, Object> createRun(Map<String, Object> request) {
        String runId = "run_" + UUID.randomUUID().toString().replace("-", "");
        String kind = String.valueOf(request.getOrDefault("kind", "probe"));
        Map<String, Object> run = switch (kind.toLowerCase()) {
            case "probe" -> createProbeRun(runId, request);
            case "script" -> createScriptRun(runId, request);
            case "image" -> createImageRun(runId, request);
            case "video" -> createVideoRun(runId, request);
            default -> throw new UnsupportedGenerationKindException(kind);
        };
        runs.put(runId, run);
        persistRun(runId, run);
        return run;
    }

    @Override
    public List<Map<String, Object>> listRuns(int limit) {
        int resolvedLimit = Math.max(1, limit);
        try {
            if (!Files.exists(generationRunsDir)) {
                return List.of();
            }
            try (Stream<Path> paths = Files.list(generationRunsDir)) {
                return paths
                    .filter(Files::isDirectory)
                    .map(path -> loadPersistedRun(path.getFileName().toString()))
                    .filter(java.util.Objects::nonNull)
                    .sorted((left, right) -> String.valueOf(right.getOrDefault("updatedAt", ""))
                        .compareTo(String.valueOf(left.getOrDefault("updatedAt", ""))))
                    .limit(resolvedLimit)
                    .toList();
            }
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run list failed: " + ex.getMessage());
        }
    }

    @Override
    public Map<String, Object> getRun(String runId) {
        Map<String, Object> run = runs.get(runId);
        if (run != null) {
            return run;
        }
        Map<String, Object> persisted = loadPersistedRun(runId);
        if (persisted == null) {
            throw new GenerationRunNotFoundException(runId);
        }
        runs.put(runId, persisted);
        return persisted;
    }

    @Override
    public Map<String, Object> usage() {
        List<Map<String, Object>> items = modelResolver.listModelsByKind("text").stream()
            .map(model -> {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("model", String.valueOf(model.getOrDefault("value", "")).trim());
                item.put("label", String.valueOf(model.getOrDefault("label", model.getOrDefault("value", ""))).trim());
                item.put("used", 0);
                item.put("unit", "count");
                item.put("remaining", 0);
                item.put("remainingUnit", "count");
                item.put("provider", String.valueOf(model.getOrDefault("provider", "")).trim());
                item.put("source", modelResolver.configSource());
                return item;
            })
            .toList();
        return Map.of(
            "items", items,
            "generatedAt", nowIso(),
            "updatedAt", nowIso()
        );
    }

    private Map<String, Object> createProbeRun(String runId, Map<String, Object> request) {
        String requestedModel = requiredModel(nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        List<Map<String, Object>> callChain = new ArrayList<>();
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("requestedModel", requestedModel);
        metadata.put("resolvedModel", profile.modelName());
        metadata.put("provider", profile.provider());
        metadata.put("family", "text");
        metadata.put("mode", "probe");
        metadata.put("endpointHost", profile.endpointHost());
        metadata.put("checkedAt", nowIso());
        metadata.put("configSource", profile.source());
        if (!profile.ready()) {
            metadata.put("latencyMs", 0);
            metadata.put("messagePreview", "text model config missing");
            callChain.add(callLog("probe", "probe.config_missing", "error", "文本模型配置不完整。", Map.of("source", profile.source())));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", "probe");
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return runEnvelope(runId, "probe", request, result, "resultProbe");
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
            metadata.put("messagePreview", truncateText(response.text(), 80));
            callChain.add(callLog("probe", "probe.completed", "success", "文本模型探活已完成。", Map.of(
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
            return runEnvelope(runId, "probe", request, result, "resultProbe");
        } catch (RuntimeException ex) {
            metadata.put("latencyMs", 0);
            metadata.put("messagePreview", truncateText(ex.getMessage(), 120));
            callChain.add(callLog("probe", "probe.failed", "error", "文本模型探活失败。", Map.of("error", truncateText(ex.getMessage(), 240))));
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("runId", runId);
            result.put("kind", "probe");
            result.put("ready", false);
            result.put("latencyMs", 0);
            result.put("callChain", callChain);
            result.put("metadata", metadata);
            return runEnvelope(runId, "probe", request, result, "resultProbe");
        }
    }

    private Map<String, Object> createScriptRun(String runId, Map<String, Object> request) {
        String sourceText = nestedValue(request, "input", "text", "");
        String visualStyle = nestedValue(request, "options", "visualStyle", "AI 自动决策");
        String requestedModel = requiredModel(nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        ModelRuntimeProfile profile = modelResolver.resolveTextProfile(requestedModel);
        String prompt = buildScriptUserPrompt(sourceText, visualStyle);
        List<Map<String, Object>> callChain = new ArrayList<>();
        String scriptMarkdown;
        TextGenerationAttempt scriptAttempt = null;
        if (sourceText.isBlank()) {
            scriptMarkdown = buildFallbackScriptMarkdown(sourceText, visualStyle);
            callChain.add(callLog("script", "script.fallback", "retry", "输入为空，返回本地占位脚本。", Map.of("source", "spring-local")));
        } else {
            scriptAttempt = generateTextWithFallback(
                profile,
                "script",
                buildScriptSystemPrompt(),
                prompt,
                boundedTemperature(profile.temperature(), 0.1, 0.4),
                Math.max(800, profile.maxTokens()),
                callChain
            );
            TextModelResponse response = scriptAttempt.response();
            scriptMarkdown = stripMarkdownFence(response.text());
            callChain.add(callLog("script", "script.requested", "success", "脚本生成请求已发送到文本模型。", Map.of(
                "provider", scriptAttempt.profile().provider(),
                "modelName", scriptAttempt.profile().modelName(),
                "endpointHost", response.endpointHost()
            )));
            callChain.add(callLog("script", "script.completed", "success", "脚本生成已完成。", Map.of(
                "latencyMs", response.latencyMs(),
                "responsesApi", response.responsesApi(),
                "responseId", response.responseId()
            )));
        }
        TextArtifact markdownArtifact = writeTextArtifact(runId, request, "script.md", scriptMarkdown);
        Map<String, Object> modelInfo = buildModelInfo(
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
        return runEnvelope(runId, "script", request, result, "resultScript");
    }

    private Map<String, Object> createImageRun(String runId, Map<String, Object> request) {
        String prompt = nestedValue(request, "input", "prompt", "");
        String referenceImageUrl = nestedValue(request, "input", "referenceImageUrl", "");
        String frameRole = normalizeFrameRole(nestedValue(request, "input", "frameRole", "first"));
        int width = nestedInt(request, "input", "width", 1024);
        int height = nestedInt(request, "input", "height", 1024);
        Integer requestedSeed = nestedNullableInt(request, "input", "seed");
        String stylePreset = nestedValue(request, "options", "stylePreset", modelResolver.value("catalog.defaults", "style_preset", "cinematic"));
        String textModel = requiredModel(nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        String requestedVisionModel = requiredModel(nestedValue(request, "model", "visionModel", ""), "visionModel", "视觉模型");
        String requestedImageModel = requiredModel(nestedValue(request, "model", "providerModel", ""), "providerModel", "关键帧模型");
        ModelRuntimeProfile textProfile = modelResolver.resolveTextProfile(textModel);
        ModelRuntimeProfile visionProfile = modelResolver.resolveTextProfile(requestedVisionModel);
        MediaProviderProfile imageProfile = modelResolver.resolveImageProfile(requestedImageModel);
        Integer appliedVisionSeed = modelResolver.supportsSeed(requestedVisionModel) ? requestedSeed : null;
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
            visionAnalysisNotes = stripMarkdownFence(visionResponse.text());
            callChain.add(callLog("vision", "image.reference_analyzed", "success", "视觉模型已完成参考帧分析。", Map.of(
                "latencyMs", visionResponse.latencyMs(),
                "endpointHost", visionResponse.endpointHost(),
                "modelName", visionProfile.modelName()
            )));
        }
        TextGenerationAttempt keyframeAttempt = prompt.isBlank() ? null : generateTextWithFallback(
            textProfile,
            "image.keyframe_prompt",
            buildKeyframePromptSystemPrompt(),
            buildKeyframePromptUserPrompt(prompt, stylePreset, width, height, frameRole, visionAnalysisNotes),
            boundedTemperature(textProfile.temperature(), 0.1, 0.25),
            Math.min(Math.max(textProfile.maxTokens() / 2, 320), 1400),
            callChain
        );
        TextModelResponse keyframeResponse = keyframeAttempt == null ? null : keyframeAttempt.response();
        String keyframePrompt = keyframeResponse == null ? prompt : stripMarkdownFence(keyframeResponse.text());
        if (keyframeResponse != null) {
            callChain.add(callLog("prompt", "image.keyframe_prompt_generated", "success", "关键帧提示词已通过文本模型生成。", Map.of(
                "latencyMs", keyframeResponse.latencyMs(),
                "endpointHost", keyframeResponse.endpointHost(),
                "modelName", keyframeAttempt.profile().modelName(),
                "frameRole", frameRole
            )));
        }
        String negativePrompt = buildNegativePrompt("image");
        String shapedPrompt = appendNegativePrompt(keyframePrompt, negativePrompt);
        RemoteImageGenerationResult remoteImage = remoteMediaGenerationClient.generateSeedreamImage(
            imageProfile,
            requestedImageModel,
            shapedPrompt,
            width,
            height
        );
        BinaryArtifact imageArtifact = writeBinaryArtifact(
            runId,
            request,
            "image",
            extensionFromMimeOrUrl(remoteImage.mimeType(), remoteImage.remoteSourceUrl(), "image"),
            remoteImage.data()
        );
        callChain.add(callLog("generation", "image.generated", "success", "远端图片已生成并保存到本地存储。", Map.of(
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
        metadata.put("configSource", imageProfile.source());
        metadata.put("provider", remoteImage.provider());
        metadata.put("providerModel", remoteImage.providerModel());
        metadata.put("requestedSize", remoteImage.requestedSize());
        result.put("metadata", metadata);
        result.put("modelInfo", buildMediaModelInfo(
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
        return runEnvelope(runId, "image", request, result, "resultImage");
    }

    private Map<String, Object> createVideoRun(String runId, Map<String, Object> request) {
        String prompt = nestedValue(request, "input", "prompt", "");
        int[] dimensions = parseDimensions(
            nestedValue(request, "input", "videoSize", ""),
            nestedInt(request, "input", "width", 720),
            nestedInt(request, "input", "height", 1280)
        );
        int width = dimensions[0];
        int height = dimensions[1];
        int requestedDurationSeconds = nestedInt(request, "input", "durationSeconds", 8);
        Integer requestedSeed = nestedNullableInt(request, "input", "seed");
        String stylePreset = nestedValue(request, "options", "stylePreset", modelResolver.value("catalog.defaults", "style_preset", "cinematic"));
        String textModel = requiredModel(nestedValue(request, "model", "textAnalysisModel", ""), "textAnalysisModel", "文本模型");
        String requestedVisionModel = requiredModel(nestedValue(request, "model", "visionModel", ""), "visionModel", "视觉模型");
        String requestedVideoModel = requiredModel(nestedValue(request, "model", "providerModel", ""), "providerModel", "视频模型");
        int durationSeconds = normalizeVideoDurationSeconds(requestedVideoModel, requestedDurationSeconds);
        String firstFrameUrl = nestedValue(request, "input", "firstFrameUrl", "");
        String lastFrameUrl = nestedValue(request, "input", "lastFrameUrl", "");
        boolean generateAudio = nestedBoolean(request, "input", "generateAudio", true);
        boolean returnLastFrame = nestedBoolean(request, "input", "returnLastFrame", true);
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
            visionAnalysisNotes = stripMarkdownFence(visionResponse.text());
            callChain.add(callLog("vision", "video.reference_analyzed", "success", "视觉模型已完成首尾帧分析。", Map.of(
                "latencyMs", visionResponse.latencyMs(),
                "endpointHost", visionResponse.endpointHost(),
                "modelName", visionProfile.modelName()
            )));
        }
        TextGenerationAttempt rewriteAttempt = prompt.isBlank() ? null : generateTextWithFallback(
            textProfile,
            "video.prompt",
            buildVisualPromptSystemPrompt("video"),
            buildVisualPromptUserPrompt("video", prompt, stylePreset, width, height, durationSeconds, visionAnalysisNotes),
            boundedTemperature(textProfile.temperature(), 0.1, 0.3),
            Math.min(Math.max(textProfile.maxTokens() / 2, 320), 1400),
            callChain
        );
        TextModelResponse response = rewriteAttempt == null ? null : rewriteAttempt.response();
        String rewrittenPrompt = response == null ? prompt : stripMarkdownFence(response.text());
        String negativePrompt = buildNegativePrompt("video");
        String shapedPrompt = appendNegativePrompt(rewrittenPrompt, negativePrompt);
        if (response != null) {
            callChain.add(callLog("prompt", "video.prompt_rewritten", "success", "视频提示词已通过文本模型重写。", Map.of(
                "latencyMs", response.latencyMs(),
                "endpointHost", response.endpointHost(),
                "modelName", rewriteAttempt.profile().modelName()
            )));
        }
        RemoteVideoGenerationResult remoteVideo = "seedance".equalsIgnoreCase(videoProfile.provider())
            ? remoteMediaGenerationClient.generateSeedanceVideo(
                videoProfile,
                requestedVideoModel,
                shapedPrompt,
                width,
                height,
                durationSeconds,
                firstFrameUrl,
                lastFrameUrl,
                returnLastFrame,
                generateAudio
            )
            : remoteMediaGenerationClient.generateDashscopeVideo(
                videoProfile,
                requestedVideoModel,
                shapedPrompt,
                width,
                height,
                durationSeconds,
                appliedVideoSeed
            );
        BinaryArtifact videoArtifact = writeBinaryArtifact(
            runId,
            request,
            "video",
            extensionFromMimeOrUrl(remoteVideo.mimeType(), remoteVideo.remoteSourceUrl(), "video"),
            remoteVideo.data()
        );
        callChain.add(callLog("generation", "video.generated", "success", "远端视频已生成并保存到本地存储。", Map.of(
            "provider", remoteVideo.provider(),
            "providerModel", remoteVideo.providerModel(),
            "taskId", remoteVideo.taskId(),
            "endpointHost", remoteVideo.endpointHost(),
            "taskEndpointHost", remoteVideo.taskEndpointHost()
        )));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("runId", runId);
        result.put("kind", "video");
        result.put("prompt", prompt);
        result.put("shapedPrompt", shapedPrompt);
        result.put("negativePrompt", negativePrompt);
        result.put("outputUrl", videoArtifact.publicUrl());
        result.put("thumbnailUrl", !firstFrameUrl.isBlank() ? firstFrameUrl : "");
        result.put("mimeType", remoteVideo.mimeType());
        result.put("durationSeconds", remoteVideo.durationSeconds());
        result.put("width", width);
        result.put("height", height);
        result.put("hasAudio", remoteVideo.hasAudio());
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("outputUrl", videoArtifact.publicUrl());
        metadata.put("fileUrl", videoArtifact.publicUrl());
        metadata.put("posterUrl", !firstFrameUrl.isBlank() ? firstFrameUrl : "");
        metadata.put("videoSize", nestedValue(request, "input", "videoSize", ""));
        metadata.put("source", "remote:" + remoteVideo.providerModel());
        metadata.put("hasAudio", remoteVideo.hasAudio());
        metadata.put("textAnalysisProvider", textProfile.provider());
        metadata.put("textAnalysisModel", textProfile.modelName());
        metadata.put("promptRewriteProvider", rewriteAttempt == null ? textProfile.provider() : rewriteAttempt.profile().provider());
        metadata.put("promptRewriteModel", rewriteAttempt == null ? textProfile.modelName() : rewriteAttempt.profile().modelName());
        metadata.put("visionAnalysisProvider", visionProfile.provider());
        metadata.put("visionAnalysisModel", visionProfile.modelName());
        metadata.put("visionAnalysisEndpointHost", visionResponse == null ? visionProfile.endpointHost() : visionResponse.endpointHost());
        metadata.put("visionAnalysisNotes", visionAnalysisNotes);
        metadata.put("configSource", videoProfile.source());
        metadata.put("remoteSourceUrl", remoteVideo.remoteSourceUrl());
        metadata.put("provider", remoteVideo.provider());
        metadata.put("providerModel", remoteVideo.providerModel());
        metadata.put("taskId", remoteVideo.taskId());
        metadata.put("firstFrameUrl", remoteVideo.firstFrameUrl());
        metadata.put("requestedLastFrameUrl", remoteVideo.requestedLastFrameUrl());
        metadata.put("lastFrameUrl", remoteVideo.lastFrameUrl());
        metadata.put("returnLastFrame", remoteVideo.returnLastFrame());
        metadata.put("generateAudio", remoteVideo.generateAudio());
        metadata.put("requestedDurationSeconds", requestedDurationSeconds);
        metadata.put("appliedDurationSeconds", durationSeconds);
        metadata.put("requestedSeed", requestedSeed);
        metadata.put("visionAnalysisSeed", appliedVisionSeed);
        metadata.put("videoGenerationSeed", appliedVideoSeed);
        result.put("metadata", metadata);
        result.put("modelInfo", buildMediaModelInfo(
            textProfile,
            rewriteAttempt == null ? textProfile : rewriteAttempt.profile(),
            visionProfile,
            videoProfile,
            requestedVideoModel,
            "video",
            response,
            visionResponse,
            remoteVideo.providerModel(),
            remoteVideo.endpointHost(),
            remoteVideo.taskEndpointHost(),
            "spring-remote-video"
        ));
        result.put("callChain", callChain);
        return runEnvelope(runId, "video", request, result, "resultVideo");
    }

    private String buildScriptSystemPrompt() {
        String configuredPrompt = promptTemplateResolver.systemPrompt("script", "short_drama_script");
        if (!configuredPrompt.isBlank()) {
            return configuredPrompt;
        }
        return """
            你是资深电影导演、视觉分镜设计师，要把用户原文转成可直接用于视频生产的专业 Markdown 分镜脚本。

            角色能力：
            1. 深度解析文学文本，提炼角色、环境、动作、情绪和叙事节奏。
            2. 使用专业影视语言设计景别、角度、运镜、光影和声音逻辑。
            3. 将抽象情绪转化为具体的物理动作、表情细节和环境质感。

            角色连续性规则：
            1. 你必须为核心角色建立稳定的角色档案，并在不同镜头中保持一致。
            2. 每个角色都要尽量固化三类锚点：
               - visual_symbols：服装、发型、伤疤、首饰、道具、颜色等可见识别元素
               - behavioral_habits：习惯动作、微表情、步态、说话姿态、惯用手等
               - lighting_bias：专属光影倾向，如英雄光、侧逆光、阴影覆盖、通透高光等
            3. 除非原文明确发生变化，不得擅自改变同一角色的服装、发型、持物手、体型、年龄感、光影倾向。

            专业镜头词汇：
            - 景别：ELS (大远景), FS (全景), MS (中景), MCU (中近景), CU (特写), ECU (大特写)
            - 角度：Eye-level (平拍), Low Angle (仰拍), High Angle (俯拍), POV (主观视角), Dutch Angle (倾斜构图)
            - 运镜：Static (固定), Push in (推), Pull out (拉), Pan (摇), Track (移), Follow (跟)

            执行规则：
            1. 严格依据原文语义，不得新增原文没有的对白、角色、身份、关系、剧情或场景。
            2. 动作场面提高分镜密度，情感场面降低分镜密度；不要为了凑数量强行拆镜。
            3. 每一镜都必须包含环境质感描述，例如烟雾、尘埃、雨滴、潮气、光晕、布料纹理、空间颗粒感。
            4. 抽象情绪必须转成可视化的动作、构图和光影变化，禁止空泛描述。
            5. 人物表情、眼神、动作和语气必须符合语境；跨镜连续对白时，情绪和动作趋势保持连贯。
            6. 不得把 Markdown 标题、镜号、原文句子直接当成画面内文字。
            7. 每个分镜的 duration 必须严格落在 5-15 秒之间，不得低于 5 秒，也不得高于 15 秒。
            8. 不要输出解释、前言、JSON 或代码块，只输出最终 Markdown 脚本。

            输出要求：
            1. 先输出【角色档案】。
            2. 再输出 Markdown Table，列必须按以下顺序：
               | shot_no | shot_spec | movement | visual_content | audio | duration |
            3. 列定义如下：
               - shot_no：递增镜号，如 001
               - shot_spec：景别 + 角度
               - movement：运镜方式
               - visual_content：画面细节描述，必须包含角色动作、特定服饰、构图、光影、环境质感
               - audio：对白、旁白、音效 (SFX) 及 BGM
               - duration：预估秒数
            4. duration 列只能填写 5-15 秒范围内的数值或区间，如 5秒、8秒、10-12秒。
            5. 表格后追加一段 Director_Notes，写整体色调建议、滤镜偏好和剪辑风格说明。
            """;
    }

    private String buildScriptUserPrompt(String sourceText, String visualStyle) {
        String styleLine = "AI 自动决策".equalsIgnoreCase(visualStyle) || visualStyle.isBlank()
            ? "视觉风格：请你根据文本题材、情绪与人物关系，自行决定最适合的视频视觉风格，并保持全片统一。"
            : "视觉风格：" + visualStyle;
        return """
            请把下面的文本整理成短剧分镜脚本。
            %s
            不要为了凑数量硬拆镜头，也不要省略关键剧情转折。
            每个镜头至少写清：镜头编号、剧情摘要、人物与场景、动作与表情、台词或旁白、镜头语言、建议时长、声音与语气。
            禁止把 Markdown 标题、镜头编号或脚本原文当作画面内文字来描述。

            【原文开始】
            %s
            【原文结束】
            """.formatted(styleLine, sourceText);
    }

    private int normalizeVideoDurationSeconds(String requestedVideoModel, int requestedDurationSeconds) {
        int normalizedRequested = Math.max(1, requestedDurationSeconds);
        Map<String, String> section = modelResolver.section("model.models.\"" + requestedVideoModel + "\"");
        List<Integer> supportedDurations = parseIntegerList(section.get("supported_durations"), List.of());
        if (supportedDurations.isEmpty()) {
            return normalizedRequested;
        }
        for (int candidate : supportedDurations) {
            if (candidate >= normalizedRequested) {
                return candidate;
            }
        }
        return supportedDurations.get(supportedDurations.size() - 1);
    }

    private String buildKeyframePromptSystemPrompt() {
        String configuredPrompt = promptTemplateResolver.systemPrompt("core", "keyframe_prompt_generator");
        if (!configuredPrompt.isBlank()) {
            return configuredPrompt;
        }
        return """
            你是影视关键帧提示词设计师。你的任务是完整理解整段分镜信息，并把它改写成适合关键帧出图模型理解的一段中文提示词，用于生成单帧但高度可执行的首帧或尾帧。
            必须遵守：
            1. 先准确理解这一镜的完整信息：人物身份、服装、发型、道具、场景、景别、镜头运动、动作起势与落点、情绪变化、对白归属、环境细节、光线与空间关系。
            2. 如果生成首帧，画面要落在动作开始前或刚开始的稳定瞬间；如果生成尾帧，画面要落在动作完成后或情绪落点的稳定瞬间，不能使用中间混乱过渡态。
            3. 输出必须具体到主体人数、站位、完整身体朝向、手脚位置、视线方向、表情状态、服装层次、道具持有方式、前景中景后景、环境材质、光线方向、地面或支撑关系。
            4. 人物必须符合物理规律并被场景可靠承托，禁止漂浮、悬空、穿模、断肢、肢体缺失、身体裁断、多人粘连、器官错位、头身比异常、手脚数量错误。
            5. 除非分镜明确要求，默认优先生成完整人物或至少构图完整的主体，不要只出现半截身体、孤立手脚、无意义局部残片。
            6. 必须保持跨镜连续性：同一角色的服装、发型、体型、年龄感、惯用手、配饰和光影倾向不能跳变；不得新增脚本中没有的人物、道具、文字或对白。
            7. 不要使用空泛形容词替代具体画面，要直接给出可执行的画面描述。
            8. 只输出一段可直接用于关键帧生成的中文提示词，不要解释，不要标题，不要列表。
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
            ? "当前要生成这一镜的尾帧关键帧，请优先表现动作完成后的落点、情绪收束后的稳定瞬间。"
            : "当前要生成这一镜的首帧关键帧，请优先表现动作刚开始前后的稳定起始瞬间。";
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

    private String buildVisualPromptSystemPrompt(String mediaKind) {
        return """
            你是影视级生成提示词设计师。你的任务是把输入内容改写成适合%s模型理解的一段中文提示词。
            必须遵守：
            1. 只提炼画面与动作语义，不要复述脚本标题、镜头编号、Markdown 标记。
            2. 除非用户明确要求，画面里禁止出现任何文字、字幕、对白气泡、屏幕文案、水印。
            3. 风格贴近真实影视摄影，避免卡通感、游戏感和不真实夸张风格。
            4. 人物比例、身高、肢体、手部、五官必须正常，不得畸变。
            5. 禁止屋内下雨、额外人物、服装突变、发型突变、角色互换、无根据的新增对话。
            6. 人物表情必须符合语境；如果涉及说话氛围或配音，语气必须符合语境。
            7. 如果同一段话跨越多个镜头，应保持语气和神态一致。
            8. 输出必须尽量具体，明确人物造型、服装、发型、年龄感、动作起止、表情层次、视线方向、镜头运动、前景中景后景、环境细节、光影方向、材质和空间关系。
            9. 视频镜头不能空洞。若时长更长，必须同步增加动作节拍、表演变化、机位调度或环境反馈，禁止长时间空镜、站桩、无意义停顿。
            10. 图片关键帧必须符合物理规律与完整构图，避免人物漂浮、半截身体、断肢、残缺、多人粘连、器官错位和不受支撑的姿态。
            11. 优先输出能直接驱动画面的细节，不要使用“有氛围感”“很电影感”“情绪复杂”这类空泛词替代具体内容。
            12. 只输出一段可直接送入生成模型的中文提示词，不要解释，不要标题，不要列表。
            """.formatted("video".equals(mediaKind) ? "视频" : "图片");
    }

    private String buildVisualPromptUserPrompt(
        String mediaKind,
        String prompt,
        String stylePreset,
        int width,
        int height,
        int durationSeconds,
        String visionAnalysisNotes
    ) {
        String durationLine = "video".equals(mediaKind) ? "\n目标时长：" + durationSeconds + " 秒。" : "";
        String motionLine = "video".equals(mediaKind)
            ? "\n请强调首尾镜头连续、动作合理、口型与说话主体一致，不能生成脚本中不存在的对白。"
            : "\n请把它整理成可用于关键帧生成的单帧视觉提示词。";
        String analysisLine = visionAnalysisNotes == null || visionAnalysisNotes.isBlank()
            ? ""
            : "\n视觉参考分析：" + visionAnalysisNotes.trim();
        String densityLine = "video".equals(mediaKind)
            ? "\n内容密度要求：" + buildDurationDensityLine(durationSeconds)
            : "\n内容密度要求：单帧画面也要把主体、场景、光线、构图、材质、表情写具体。";
        return """
            请把下面内容改写为%s生成提示词。
            风格预设：%s。
            输出尺寸：%dx%d。%s%s%s%s

            原始内容：
            %s
            """.formatted("video".equals(mediaKind) ? "视频" : "图片", stylePreset, width, height, durationLine, motionLine, analysisLine, densityLine, prompt);
    }

    private String buildDurationDensityLine(int durationSeconds) {
        if (durationSeconds <= 6) {
            return "短镜头也必须有清晰主体动作和完成态，禁止只拍环境或人物静止停留。";
        }
        if (durationSeconds <= 10) {
            return "中段时长镜头必须有 2-3 个连续动作/表情节拍，内容量要明显高于短镜头。";
        }
        return "长镜头必须形成起势、推进、落点三段变化，动作、调度、表情或构图不能只有单一状态。";
    }

    private String buildVisionAnalysisSystemPrompt(String mediaKind) {
        return """
            你是影视连续性与画面审校助手。你需要阅读用户的剧情提示，并结合提供的图片进行视觉理解。
            必须遵守：
            1. 只根据图片里真实可见的内容和用户给出的剧情任务输出，不要臆造图片中不存在的细节。
            2. 重点判断人物身份、服装、发型、姿态、情绪、景别、场景、光线、天气、道具是否与剧情任务一致。
            3. 如果发现风险，优先指出：画面文字、字幕、水印、人物比例异常、角色混淆、装扮突变、场景不真实。
            4. 输出必须精简，服务于后续%s生成，不要写成散文。
            5. 只输出两部分：
               画面确认：一句话总结当前图片中最关键的可保留视觉事实。
               连续性要求：一句话给出后续生成必须保持或修正的要点。
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
            ? "不要新增对白，不要把A角色台词分配给B角色，不要口型和说话主体错位，不要镜头切换后人物装扮突变。"
            : "不要把脚本文字、对白原句、镜头编号直接画进画面，不要半截身体、孤立手脚、断肢、身体残缺、悬空人物、无支撑姿态。";
        return "禁止屋内下雨、画面文字、字幕、水印、对白气泡、人物比例失调、身高异常、四肢畸形、手指异常、五官崩坏、额外人物、服装突变、发型突变、角色互换、漂浮物体、不真实反射、过度卡通化、多人粘连、器官错位、空间透视错乱、穿模。"
            + videoOnly;
    }

    private String normalizeFrameRole(String frameRole) {
        return "last".equalsIgnoreCase(stringValue(frameRole)) ? "last" : "first";
    }

    private String appendNegativePrompt(String prompt, String negativePrompt) {
        if (prompt == null || prompt.isBlank()) {
            return "写实影视风格。负面约束：" + negativePrompt;
        }
        return prompt.trim() + "\n负面约束：" + negativePrompt;
    }

    private Map<String, Object> buildModelInfo(
        ModelRuntimeProfile profile,
        String requestedModel,
        String mediaKind,
        TextModelResponse response,
        String sourceTag
    ) {
        Map<String, Object> modelInfo = new LinkedHashMap<>();
        modelInfo.put("provider", profile.provider());
        modelInfo.put("modelName", profile.modelName());
        modelInfo.put("providerModel", profile.modelName());
        modelInfo.put("requestedModel", requestedModel);
        modelInfo.put("resolvedModel", profile.modelName());
        modelInfo.put("textAnalysisModel", profile.modelName());
        modelInfo.put("mediaKind", mediaKind);
        modelInfo.put("endpointHost", response == null ? profile.endpointHost() : response.endpointHost());
        modelInfo.put("configSource", profile.source());
        modelInfo.put("generationSource", sourceTag);
        return modelInfo;
    }

    private Map<String, Object> buildMediaModelInfo(
        ModelRuntimeProfile textProfile,
        ModelRuntimeProfile rewriteProfile,
        ModelRuntimeProfile visionProfile,
        MediaProviderProfile mediaProfile,
        String requestedModel,
        String mediaKind,
        TextModelResponse textResponse,
        TextModelResponse visionResponse,
        String resolvedModel,
        String endpointHost,
        String taskEndpointHost,
        String sourceTag
    ) {
        Map<String, Object> modelInfo = new LinkedHashMap<>();
        modelInfo.put("provider", mediaProfile.provider());
        modelInfo.put("modelName", resolvedModel);
        modelInfo.put("providerModel", resolvedModel);
        modelInfo.put("requestedModel", requestedModel);
        modelInfo.put("resolvedModel", resolvedModel);
        modelInfo.put("textAnalysisModel", textProfile.modelName());
        modelInfo.put("textAnalysisProvider", textProfile.provider());
        modelInfo.put("textAnalysisEndpointHost", textProfile.endpointHost());
        modelInfo.put("promptRewriteModel", rewriteProfile.modelName());
        modelInfo.put("promptRewriteProvider", rewriteProfile.provider());
        modelInfo.put("promptRewriteEndpointHost", textResponse == null ? rewriteProfile.endpointHost() : textResponse.endpointHost());
        modelInfo.put("visionAnalysisModel", visionProfile.modelName());
        modelInfo.put("visionAnalysisProvider", visionProfile.provider());
        modelInfo.put("visionAnalysisEndpointHost", visionResponse == null ? visionProfile.endpointHost() : visionResponse.endpointHost());
        modelInfo.put("mediaKind", mediaKind);
        modelInfo.put("endpointHost", endpointHost);
        modelInfo.put("taskEndpointHost", taskEndpointHost);
        modelInfo.put("configSource", mediaProfile.source());
        modelInfo.put("generationSource", sourceTag);
        return modelInfo;
    }

    private List<Map<String, Object>> enrichVideoModels(List<Map<String, Object>> items) {
        List<Map<String, Object>> normalizedItems = new ArrayList<>();
        for (Map<String, Object> item : items) {
            Map<String, Object> row = new LinkedHashMap<>(item);
            String modelName = String.valueOf(row.getOrDefault("value", "")).trim();
            Map<String, String> section = modelResolver.section("model.models.\"" + modelName + "\"");
            row.put("generationMode", firstNonBlank(section.get("generation_mode"), "i2v"));
            row.put("supportedSizes", parseStringList(section.get("supported_sizes"), List.of("720*1280", "1280*720")));
            row.put("supportedDurations", parseIntegerList(section.get("supported_durations"), List.of(4, 6, 8, 10, 12)));
            normalizedItems.add(row);
        }
        return normalizedItems;
    }

    private List<Map<String, Object>> aspectRatioOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.aspect_ratios")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", firstNonBlank(section.values().get("label"), section.name()));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "9:16", "label", "竖版 9:16"));
            items.add(Map.of("value", "16:9", "label", "横版 16:9"));
        }
        return items;
    }

    private List<Map<String, Object>> stylePresetOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.style_presets")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("key", section.name());
            row.put("label", firstNonBlank(section.values().get("label"), section.name()));
            row.put("description", firstNonBlank(section.values().get("description"), ""));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("key", "cinematic", "label", "电影写实", "description", "贴近真实影视剧照与镜头语言"));
            items.add(Map.of("key", "drama", "label", "短剧冲突", "description", "更强调人物冲突和情绪推进"));
        }
        return items;
    }

    private List<Map<String, Object>> imageSizeOptions() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.image_sizes")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", firstNonBlank(section.values().get("label"), section.name()));
            row.put("width", positiveInt(section.values().get("width"), 0));
            row.put("height", positiveInt(section.values().get("height"), 0));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "1024x1024", "label", "1:1 · 1024x1024", "width", 1024, "height", 1024));
            items.add(Map.of("value", "720x1280", "label", "9:16 · 720x1280", "width", 720, "height", 1280));
        }
        return items;
    }

    private List<Map<String, Object>> videoSizeOptions(List<Map<String, Object>> videoModels, List<String> videoModelNames) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.video_sizes")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", section.name());
            row.put("label", firstNonBlank(section.values().get("label"), section.name()));
            row.put("width", positiveInt(section.values().get("width"), 0));
            row.put("height", positiveInt(section.values().get("height"), 0));
            row.put("supportedModels", modelsSupportingSize(videoModels, section.name(), videoModelNames));
            items.add(row);
        }
        if (items.isEmpty()) {
            items.add(Map.of("value", "720*1280", "label", "720 x 1280", "width", 720, "height", 1280, "supportedModels", videoModelNames));
            items.add(Map.of("value", "1280*720", "label", "1280 x 720", "width", 1280, "height", 720, "supportedModels", videoModelNames));
        }
        return items;
    }

    private List<Map<String, Object>> videoDurationOptions(List<Map<String, Object>> videoModels, List<String> videoModelNames) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (ModelRuntimePropertiesResolver.ConfigSection section : modelResolver.listSections("catalog.video_durations")) {
            int duration = positiveInt(section.name(), 0);
            if (duration <= 0) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("value", duration);
            row.put("label", firstNonBlank(section.values().get("label"), duration + " 秒"));
            row.put("supportedModels", modelsSupportingDuration(videoModels, duration, videoModelNames));
            items.add(row);
        }
        if (items.isEmpty()) {
            for (int duration : List.of(4, 6, 8, 10, 12)) {
                items.add(Map.of("value", duration, "label", duration + " 秒", "supportedModels", videoModelNames));
            }
        }
        return items;
    }

    private List<String> modelsSupportingSize(List<Map<String, Object>> videoModels, String size, List<String> fallback) {
        List<String> matched = new ArrayList<>();
        String normalizedSize = normalizeValue(size);
        for (Map<String, Object> videoModel : videoModels) {
            for (String supportedSize : stringList(videoModel.get("supportedSizes"))) {
                if (normalizeValue(supportedSize).equals(normalizedSize)) {
                    matched.add(String.valueOf(videoModel.getOrDefault("value", "")).trim());
                    break;
                }
            }
        }
        return matched.isEmpty() ? fallback : matched;
    }

    private List<String> modelsSupportingDuration(List<Map<String, Object>> videoModels, int duration, List<String> fallback) {
        List<String> matched = new ArrayList<>();
        for (Map<String, Object> videoModel : videoModels) {
            for (Integer supportedDuration : integerList(videoModel.get("supportedDurations"))) {
                if (supportedDuration != null && supportedDuration == duration) {
                    matched.add(String.valueOf(videoModel.getOrDefault("value", "")).trim());
                    break;
                }
            }
        }
        return matched.isEmpty() ? fallback : matched;
    }

    private List<String> parseStringList(String raw, List<String> fallback) {
        List<String> items = new ArrayList<>();
        if (raw != null) {
            for (String part : raw.split(",")) {
                String normalized = part == null ? "" : part.trim();
                if (!normalized.isBlank()) {
                    items.add(normalized);
                }
            }
        }
        return items.isEmpty() ? fallback : items;
    }

    private List<Integer> parseIntegerList(String raw, List<Integer> fallback) {
        List<Integer> items = new ArrayList<>();
        if (raw != null) {
            for (String part : raw.split(",")) {
                int parsed = positiveInt(part, 0);
                if (parsed > 0) {
                    items.add(parsed);
                }
            }
        }
        return items.isEmpty() ? fallback : items;
    }

    private List<String> stringList(Object value) {
        if (value instanceof List<?> items) {
            List<String> results = new ArrayList<>();
            for (Object item : items) {
                String normalized = String.valueOf(item == null ? "" : item).trim();
                if (!normalized.isBlank()) {
                    results.add(normalized);
                }
            }
            return results;
        }
        return List.of();
    }

    private List<Integer> integerList(Object value) {
        if (value instanceof List<?> items) {
            List<Integer> results = new ArrayList<>();
            for (Object item : items) {
                int parsed = positiveInt(item == null ? "" : String.valueOf(item), 0);
                if (parsed > 0) {
                    results.add(parsed);
                }
            }
            return results;
        }
        return List.of();
    }

    private int positiveInt(String raw, int fallback) {
        try {
            int value = Integer.parseInt(String.valueOf(raw).trim());
            return value > 0 ? value : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private int firstPositiveInt(int... values) {
        for (int value : values) {
            if (value > 0) {
                return value;
            }
        }
        return 0;
    }

    private String normalizeValue(String value) {
        return value == null ? "" : value.trim().toLowerCase();
    }

    private String requiredModel(String value, String fieldName, String label) {
        String normalized = value == null ? "" : value.trim();
        if (!normalized.isBlank()) {
            return normalized;
        }
        throw new IllegalArgumentException("请先选择" + label + "（" + fieldName + "）");
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private TextGenerationAttempt generateTextWithFallback(
        ModelRuntimeProfile primaryProfile,
        String stage,
        String systemPrompt,
        String userPrompt,
        double temperature,
        int maxTokens,
        List<Map<String, Object>> callChain
    ) {
        try {
            return new TextGenerationAttempt(
                primaryProfile,
                textModelClient.generateText(primaryProfile, systemPrompt, userPrompt, temperature, maxTokens)
            );
        } catch (RuntimeException primaryEx) {
            String fallbackModel = primaryProfile.fallbackModel();
            if (fallbackModel == null || fallbackModel.isBlank() || fallbackModel.equalsIgnoreCase(primaryProfile.modelName())) {
                throw primaryEx;
            }
            callChain.add(callLog(stage, stage + ".fallback", "retry", "主文本模型失败，尝试回退到备用模型。", Map.of(
                "requestedModel", primaryProfile.modelName(),
                "fallbackModel", fallbackModel,
                "error", truncateText(primaryEx.getMessage(), 240)
            )));
            ModelRuntimeProfile fallbackProfile = modelResolver.resolveTextProfile(fallbackModel);
            return new TextGenerationAttempt(
                fallbackProfile,
                textModelClient.generateText(fallbackProfile, systemPrompt, userPrompt, temperature, maxTokens)
            );
        }
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

    private Map<String, Object> runEnvelope(String runId, String kind, Map<String, Object> request, Map<String, Object> result, String specificResultKey) {
        String now = nowIso();
        Map<String, Object> run = new LinkedHashMap<>();
        run.put("id", runId);
        run.put("kind", kind);
        run.put("status", "succeeded");
        run.put("createdAt", now);
        run.put("updatedAt", now);
        run.put("input", mapValue(request.get("input")));
        run.put("model", mapValue(request.get("model")));
        run.put("options", mapValue(request.get("options")));
        run.put("result", result);
        run.put(specificResultKey, result);
        return run;
    }

    private String nestedValue(Map<String, Object> payload, String parentKey, String childKey, String defaultValue) {
        Object parent = payload.get(parentKey);
        if (parent instanceof Map<?, ?> map) {
            Object child = map.get(childKey);
            if (child != null) {
                return String.valueOf(child);
            }
        }
        return defaultValue;
    }

    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> normalized = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                normalized.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return normalized;
        }
        return Map.of();
    }

    private int nestedInt(Map<String, Object> payload, String parentKey, String childKey, int defaultValue) {
        Object parent = payload.get(parentKey);
        if (parent instanceof Map<?, ?> map) {
            Object child = map.get(childKey);
            if (child instanceof Number number) {
                return number.intValue();
            }
            if (child != null) {
                try {
                    return (int) Math.round(Double.parseDouble(String.valueOf(child)));
                } catch (NumberFormatException ignored) {
                }
            }
        }
        return defaultValue;
    }

    private Integer nestedNullableInt(Map<String, Object> payload, String parentKey, String childKey) {
        Object parent = payload.get(parentKey);
        if (!(parent instanceof Map<?, ?> map)) {
            return null;
        }
        Object child = map.get(childKey);
        if (child instanceof Number number) {
            return number.intValue();
        }
        if (child != null) {
            try {
                return (int) Math.round(Double.parseDouble(String.valueOf(child)));
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    private boolean nestedBoolean(Map<String, Object> payload, String parentKey, String childKey, boolean defaultValue) {
        Object parent = payload.get(parentKey);
        if (!(parent instanceof Map<?, ?> map)) {
            return defaultValue;
        }
        Object child = map.get(childKey);
        if (child instanceof Boolean bool) {
            return bool;
        }
        if (child instanceof Number number) {
            return number.intValue() != 0;
        }
        if (child instanceof String text) {
            String normalized = text.trim().toLowerCase();
            if (List.of("1", "true", "yes", "on").contains(normalized)) {
                return true;
            }
            if (List.of("0", "false", "no", "off").contains(normalized)) {
                return false;
            }
        }
        return defaultValue;
    }

    private Map<String, Object> callLog(String stage, String event, String status, String message, Map<String, Object> details) {
        Map<String, Object> safeDetails = new LinkedHashMap<>();
        if (details != null) {
            for (Map.Entry<String, Object> entry : details.entrySet()) {
                if (entry.getValue() != null) {
                    safeDetails.put(entry.getKey(), entry.getValue());
                }
            }
        }
        if (!safeDetails.containsKey("source")) {
            safeDetails.put("source", "spring");
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("timestamp", nowIso());
        row.put("stage", stage);
        row.put("event", event);
        row.put("status", status);
        row.put("message", message);
        row.put("details", safeDetails);
        return row;
    }

    private ImageArtifact writePlaceholderImage(String runId, String fileName, int width, int height, String prompt, String stylePreset) {
        try {
            return localMediaArtifactService.writePromptCard(
                "gen/_runs/" + runId,
                fileName,
                width,
                height,
                fileName.replace(".png", "").toUpperCase() + " PLACEHOLDER",
                "style: " + stylePreset,
                prompt == null || prompt.isBlank() ? "placeholder output" : prompt
            );
        } catch (RuntimeException ex) {
            throw new GenerationNotImplementedException("generation image artifact write failed: " + ex.getMessage());
        }
    }

    private TextArtifact writeTextArtifact(String runId, Map<String, Object> request, String fileName, String content) {
        try {
            return localMediaArtifactService.writeText(storageRelativeDir(request, runId), storageFileName(request, fileName), content);
        } catch (RuntimeException ex) {
            throw new GenerationNotImplementedException("generation run artifact write failed: " + ex.getMessage());
        }
    }

    private BinaryArtifact writeBinaryArtifact(String runId, Map<String, Object> request, String fileStem, String extension, byte[] data) {
        try {
            String relativeDir = storageRelativeDir(request, runId);
            Path dir = Paths.get(localMediaArtifactService.resolveAbsolutePath("/storage/" + relativeDir + "/.dir")).getParent();
            Files.createDirectories(dir);
            String normalizedExtension = (extension == null || extension.isBlank()) ? "bin" : extension;
            String fileName = storageFileStem(request, fileStem) + "." + normalizedExtension;
            Path output = dir.resolve(fileName);
            Files.write(output, data);
            return new BinaryArtifact(
                fileName,
                output.toAbsolutePath().normalize().toString(),
                "/storage/" + relativeDir + "/" + fileName,
                Files.size(output)
            );
        } catch (IOException ex) {
            throw new GenerationProviderException("generation binary artifact write failed: " + ex.getMessage());
        }
    }

    private int[] parseDimensions(String raw, int fallbackWidth, int fallbackHeight) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase().replace("x", "*");
        String[] parts = normalized.split("\\*");
        if (parts.length == 2) {
            try {
                return new int[] {Integer.parseInt(parts[0]), Integer.parseInt(parts[1])};
            } catch (Exception ignored) {
            }
        }
        return new int[] {fallbackWidth, fallbackHeight};
    }

    private double boundedTemperature(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    private String stripMarkdownFence(String text) {
        String value = text == null ? "" : text.trim();
        if (!value.startsWith("```")) {
            return value;
        }
        int firstBreak = value.indexOf('\n');
        int lastFence = value.lastIndexOf("```");
        if (firstBreak < 0 || lastFence <= firstBreak) {
            return value.replace("```", "").trim();
        }
        return value.substring(firstBreak + 1, lastFence).trim();
    }

    private String truncateText(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() <= limit ? value : value.substring(0, limit);
    }

    private String extensionFromMimeOrUrl(String mimeType, String sourceUrl, String mediaType) {
        String normalizedMime = mimeType == null ? "" : mimeType.toLowerCase();
        if (normalizedMime.startsWith("image/png")) {
            return "png";
        }
        if (normalizedMime.startsWith("image/jpeg")) {
            return "jpg";
        }
        if (normalizedMime.startsWith("image/webp")) {
            return "webp";
        }
        if (normalizedMime.startsWith("video/mp4")) {
            return "mp4";
        }
        if (normalizedMime.startsWith("video/webm")) {
            return "webm";
        }
        if (sourceUrl != null && !sourceUrl.isBlank()) {
            String path = sourceUrl;
            int queryIndex = path.indexOf('?');
            if (queryIndex >= 0) {
                path = path.substring(0, queryIndex);
            }
            int dotIndex = path.lastIndexOf('.');
            if (dotIndex >= 0 && dotIndex < path.length() - 1) {
                return path.substring(dotIndex + 1).toLowerCase();
            }
        }
        return "image".equals(mediaType) ? "png" : "mp4";
    }

    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    private void persistRun(String runId, Map<String, Object> run) {
        try {
            Files.createDirectories(generationRunsDir.resolve(runId));
            Path output = generationRunsDir.resolve(runId).resolve("run.json");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(output.toFile(), run);
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run persistence failed: " + ex.getMessage());
        }
    }

    private Map<String, Object> loadPersistedRun(String runId) {
        try {
            Path input = generationRunsDir.resolve(runId).resolve("run.json");
            if (!Files.exists(input)) {
                return null;
            }
            return objectMapper.readValue(input.toFile(), MAP_TYPE);
        } catch (IOException ex) {
            throw new GenerationNotImplementedException("generation run load failed: " + ex.getMessage());
        }
    }

    private String storageRelativeDir(Map<String, Object> request, String runId) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("relativeDir"));
        return configured.isBlank() ? "gen/_runs/" + runId : configured;
    }

    private String storageFileStem(Map<String, Object> request, String fallback) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("fileStem"));
        return configured.isBlank() ? fallback : configured;
    }

    private String storageFileName(Map<String, Object> request, String fallback) {
        Map<String, Object> storage = mapValue(request.get("storage"));
        String configured = stringValue(storage.get("fileName"));
        return configured.isBlank() ? fallback : configured;
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private record BinaryArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes
    ) {
    }

    private record TextGenerationAttempt(
        ModelRuntimeProfile profile,
        TextModelResponse response
    ) {
    }
}
