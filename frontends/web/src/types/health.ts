/** Health-check and runtime diagnostic contracts. */
export interface HealthModelSummary {
  provider: string | null;
  primary_model?: string | null;
  primaryModel?: string | null;
  text_analysis_provider?: string | null;
  textAnalysisProvider?: string | null;
  text_analysis_model?: string | null;
  textAnalysisModel?: string | null;
  endpoint_host?: string;
  endpointHost?: string | null;
  api_key_present?: boolean;
  apiKeyPresent?: boolean;
  ready: boolean;
  temperature: number;
  max_tokens?: number;
  maxTokens?: number;
  config_errors?: string[];
  configErrors?: string[];
}

export interface HealthPlanningCapabilities {
  timed_transcript_supported?: boolean;
  timedTranscriptSupported?: boolean;
  transcript_semantic_planning?: boolean;
  transcriptSemanticPlanning?: boolean;
  visual_content_analysis?: boolean;
  visualContentAnalysis?: boolean;
  visual_event_reasoning?: boolean;
  visualEventReasoning?: boolean;
  subtitle_visual_fusion?: boolean;
  subtitleVisualFusion?: boolean;
  audio_peak_signal?: boolean;
  audioPeakSignal?: boolean;
  scene_boundary_signal?: boolean;
  sceneBoundarySignal?: boolean;
  fusion_timeline_planning?: boolean;
  fusionTimelinePlanning?: boolean;
  fallback_heuristic_enabled?: boolean;
  fallbackHeuristicEnabled?: boolean;
}

export interface HealthRuntimeSummary {
  name: string;
  env: string;
  execution_mode?: string;
  executionMode?: string;
  database_url?: string;
  databaseUrl?: string;
  model_provider?: string | null;
  modelProvider?: string | null;
  storage_root?: string;
  storageRoot?: string;
  model: HealthModelSummary;
  planning_capabilities?: HealthPlanningCapabilities;
  planningCapabilities?: HealthPlanningCapabilities;
}

export interface HealthResponse {
  ok: boolean;
  runtime: HealthRuntimeSummary;
}
