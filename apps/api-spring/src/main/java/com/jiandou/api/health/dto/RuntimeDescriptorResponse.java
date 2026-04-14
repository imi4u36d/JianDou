package com.jiandou.api.health.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record RuntimeDescriptorResponse(
    boolean ok,
    RuntimeInfo runtime
) {

    public record RuntimeInfo(
        String name,
        String env,
        @JsonProperty("execution_mode") String executionMode,
        @JsonProperty("database_url") String databaseUrl,
        @JsonProperty("model_provider") String modelProvider,
        @JsonProperty("storage_root") String storageRoot,
        ModelInfo model,
        @JsonProperty("planning_capabilities") PlanningCapabilities planningCapabilities
    ) {
    }

    public record ModelInfo(
        String provider,
        @JsonProperty("primary_model") String primaryModel,
        @JsonProperty("fallback_model") String fallbackModel,
        @JsonProperty("text_analysis_provider") String textAnalysisProvider,
        @JsonProperty("text_analysis_model") String textAnalysisModel,
        @JsonProperty("vision_model") String visionModel,
        @JsonProperty("vision_fallback_model") String visionFallbackModel,
        @JsonProperty("endpoint_host") String endpointHost,
        @JsonProperty("api_key_present") boolean apiKeyPresent,
        boolean ready,
        double temperature,
        @JsonProperty("max_tokens") int maxTokens,
        @JsonProperty("config_source") String configSource,
        @JsonProperty("config_errors") List<String> configErrors
    ) {
    }

    public record PlanningCapabilities(
        @JsonProperty("timed_transcript_supported") boolean timedTranscriptSupported,
        @JsonProperty("transcript_semantic_planning") boolean transcriptSemanticPlanning,
        @JsonProperty("visual_content_analysis") boolean visualContentAnalysis,
        @JsonProperty("visual_event_reasoning") boolean visualEventReasoning,
        @JsonProperty("subtitle_visual_fusion") boolean subtitleVisualFusion,
        @JsonProperty("audio_peak_signal") boolean audioPeakSignal,
        @JsonProperty("scene_boundary_signal") boolean sceneBoundarySignal,
        @JsonProperty("fusion_timeline_planning") boolean fusionTimelinePlanning,
        @JsonProperty("fallback_heuristic_enabled") boolean fallbackHeuristicEnabled
    ) {
    }
}
