import type { TaskMaterial, TaskOutput } from "./task-assets";
import type { EditingMode, TaskListItem, TaskPlanClip, TaskSourceAssetSummary } from "./task-core";
import type { TaskArtifactDirectories, TaskAttempt, TaskDurationDiagnosticClip, TaskMonitoringSummary, TaskStageRun } from "./task-execution";

export interface TaskRequestSnapshot {
  taskType?: string | null; assetType?: string | null; title?: string | null; creativePrompt?: string | null;
  aspectRatio?: string | null; imageSize?: string | null; textAnalysisModel?: string | null; imageModel?: string | null;
  videoModel?: string | null; videoSize?: string | null; seed?: number | null; videoDurationSeconds?: number | "auto" | null;
  outputCount?: number | "auto" | { auto?: boolean; count?: number | string | null } | null;
  minDurationSeconds?: number | null; maxDurationSeconds?: number | null; transcriptText?: string | null;
  stopBeforeVideoGeneration?: boolean | null; referenceImageUrls?: string[] | null; referenceAssetIds?: string[] | null;
}

export interface TaskDetail extends TaskListItem {
  sourceFileName: string; sourceFileNames?: string[]; sourceAssetIds?: string[]; editingMode?: EditingMode;
  aspectRatio: string; minDurationSeconds: number; maxDurationSeconds: number; introTemplate: string; outroTemplate: string;
  creativePrompt?: string; errorMessage?: string | null; failureReason?: string | null; failureStage?: string | null;
  failureClipIndex?: number | null; startedAt?: string | null; finishedAt?: string | null; retryCount?: number;
  completedOutputCount?: number; transcriptPreview?: string | null; hasTranscript?: boolean; hasTimedTranscript?: boolean;
  transcriptCueCount?: number; source?: TaskSourceAssetSummary | null; sourceAssets?: TaskSourceAssetSummary[];
  storyboardScript?: string | null; materials?: TaskMaterial[]; artifactDirectories?: TaskArtifactDirectories;
  executionContext?: Record<string, unknown>; requestSnapshot?: TaskRequestSnapshot;
  durationDiagnostics?: TaskDurationDiagnosticClip[]; plan?: TaskPlanClip[]; attempts?: TaskAttempt[];
  stageRuns?: TaskStageRun[]; monitoring?: TaskMonitoringSummary; outputs: TaskOutput[];
}
