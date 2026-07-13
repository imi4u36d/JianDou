import type { TaskStatus } from "./task-core";

export interface TaskTraceEvent { timestamp: string; level: string; stage: string; event: string; message: string; payload: Record<string, unknown>; }
export interface SeedanceTaskQueryResult { taskId: string; status: string; videoUrl?: string | null; message?: string | null; payload: Record<string, unknown>; }

export interface TaskStageRun {
  stageRunId?: string; taskId?: string; attemptId?: string; stageName?: string | null; stageSeq?: number | null;
  clipIndex?: number | null; status?: string | null; workerInstanceId?: string | null; startedAt?: string | null;
  finishedAt?: string | null; durationMs?: number | null; inputSummary?: Record<string, unknown> | null;
  outputSummary?: Record<string, unknown> | null; errorCode?: string | null; errorMessage?: string | null;
}

export interface TaskAttempt {
  attemptId?: string; taskId?: string; attemptNo?: number | null; triggerType?: string | null; status?: string | null;
  queueName?: string | null; workerInstanceId?: string | null; queueEnteredAt?: string | null; queueLeftAt?: string | null;
  claimedAt?: string | null; startedAt?: string | null; finishedAt?: string | null; resumeFromStage?: string | null;
  resumeFromClipIndex?: number | null; failureCode?: string | null; failureMessage?: string | null;
  payload?: Record<string, unknown> | null;
}

export interface TaskArtifactDirectories {
  storageRoot?: string | null; baseRelativeDir?: string | null; baseAbsoluteDir?: string | null;
  runningRelativeDir?: string | null; runningAbsoluteDir?: string | null; joinedRelativeDir?: string | null;
  joinedAbsoluteDir?: string | null; runningPublicBaseUrl?: string | null; joinedPublicBaseUrl?: string | null;
  storyboardFileName?: string | null; firstFramePattern?: string | null; lastFramePattern?: string | null;
  clipPattern?: string | null; joinPattern?: string | null;
}

export interface TaskMonitoringSummary {
  currentStage?: string | null; activeAttemptStatus?: string | null; activeWorkerInstanceId?: string | null;
  resumeFromStage?: string | null; resumeFromClipIndex?: number | null; plannedClipCount?: number; renderedClipCount?: number;
  contiguousRenderedClipCount?: number; latestRenderedClipIndex?: number; latestVideoOutputUrl?: string | null;
  latestJoinName?: string | null; latestJoinOutputUrl?: string | null; latestImageOutputUrl?: string | null;
  latestImageOutputUrls?: string[] | null; latestJoinClipIndex?: number | null; latestJoinClipIndices?: unknown[];
  latestTrace?: Record<string, unknown>; latestStageRun?: Record<string, unknown>; latestVideoOutput?: Record<string, unknown>;
  latestJoinOutput?: Record<string, unknown>; activeAttempt?: Record<string, unknown>; storyboardFileUrl?: string | null;
  artifactDirectories?: TaskArtifactDirectories;
}

export interface TaskDurationDiagnosticClip {
  clipIndex: number; durationSource?: string | null; scriptMinDurationSeconds?: number | null;
  scriptMaxDurationSeconds?: number | null; plannedTargetDurationSeconds?: number | null;
  plannedMinDurationSeconds?: number | null; plannedMaxDurationSeconds?: number | null;
  requestedDurationSeconds?: number | null; appliedDurationSeconds?: number | null; actualDurationSeconds?: number | null;
  status?: "pending" | "rendered" | string | null;
}

export interface AdminTaskDiagnosisFinding { code: string; severity: "info" | "low" | "medium" | "high"; title: string; detail: string; }
export interface AdminTaskDiagnosis {
  taskId: string; title: string; status: TaskStatus; severity: "info" | "low" | "medium" | "high"; summary: string;
  findings: AdminTaskDiagnosisFinding[]; recovery: Record<string, unknown>; continuity: Record<string, unknown>;
  outputs: Record<string, unknown>; queue: Record<string, unknown>;
}
