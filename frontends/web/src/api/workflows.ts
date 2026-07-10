/**
 * 阶段化工作流 API 请求封装。
 */
import type {
  CreateWorkflowRequest,
  RateStageVersionRequest,
  RateWorkflowRequest,
  UpdateWorkflowSettingsRequest,
  WorkflowDeleteResult,
  WorkflowDetail,
  WorkflowFilters,
  WorkflowPaginatedResponse,
  WorkflowSummary,
} from "@/types/workflows";

import { deleteJson, getJson, patchJson, postJson } from "./client";
import { withQuery } from "./query";

const workflowPath = (workflowId: string) => `/workflows/${encodeURIComponent(workflowId)}`;

export function createWorkflow(payload: CreateWorkflowRequest) {
  return postJson<WorkflowDetail>("/workflows", payload);
}

export function fetchAllWorkflows() {
  return getJson<WorkflowSummary[]>("/workflows");
}

export function fetchWorkflowPage(params: WorkflowFilters & { offset: number; limit: number }) {
  return getJson<WorkflowPaginatedResponse>(
    withQuery("/workflows", {
      q: params.q,
      status: params.status && params.status !== "all" ? params.status : undefined,
      sort: params.sort,
      offset: params.offset,
      limit: params.limit,
    }),
  );
}

export function fetchWorkflow(workflowId: string) {
  return getJson<WorkflowDetail>(workflowPath(workflowId));
}

export function deleteWorkflow(workflowId: string) {
  return deleteJson<WorkflowDeleteResult>(workflowPath(workflowId));
}

export function updateWorkflowSettings(workflowId: string, payload: UpdateWorkflowSettingsRequest) {
  return patchJson<WorkflowDetail>(`${workflowPath(workflowId)}/settings`, payload);
}

export function generateStoryboard(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/storyboards/generate`, {});
}

export function adjustStoryboard(workflowId: string, versionId: string, prompt?: string | null) {
  const normalizedPrompt = typeof prompt === "string" ? prompt.trim() : "";
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/storyboards/${encodeURIComponent(versionId)}/adjust`,
    normalizedPrompt ? { prompt: normalizedPrompt } : {},
  );
}

export function selectStoryboard(workflowId: string, versionId: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/storyboards/${encodeURIComponent(versionId)}/select`,
    {},
  );
}

export function generateKeyframe(workflowId: string, clipIndex: number) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/clips/${clipIndex}/keyframes/generate`, {});
}

export function generateCharacterSheet(workflowId: string, characterIndex: number) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/character-sheets/${characterIndex}/generate`,
    {},
  );
}

export function generateKeyframeFrame(workflowId: string, clipIndex: number, frameRole: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(frameRole)}/generate`,
    {},
  );
}

export function selectKeyframe(workflowId: string, clipIndex: number, versionId: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(versionId)}/select`,
    {},
  );
}

export function selectKeyframeFrame(workflowId: string, clipIndex: number, versionId: string, frameRole: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(versionId)}/frames/${encodeURIComponent(frameRole)}/select`,
    {},
  );
}

export function selectCharacterSheetAsset(workflowId: string, clipIndex: number, assetId: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/character-sheets/${clipIndex}/select-asset`,
    { assetId },
  );
}

export function generateVideo(workflowId: string, clipIndex: number) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/clips/${clipIndex}/videos/generate`, {});
}

export function selectVideo(workflowId: string, clipIndex: number, versionId: string) {
  return postJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/clips/${clipIndex}/videos/${encodeURIComponent(versionId)}/select`,
    {},
  );
}

export function finalizeWorkflow(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/finalize`, {});
}

export function rateWorkflow(workflowId: string, payload: RateWorkflowRequest) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/rating`, payload);
}

export function rateStageVersion(workflowId: string, versionId: string, payload: RateStageVersionRequest) {
  return patchJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/versions/${encodeURIComponent(versionId)}/rating`,
    payload,
  );
}

export function deleteStageVersion(workflowId: string, versionId: string) {
  return deleteJson<WorkflowDetail>(
    `${workflowPath(workflowId)}/versions/${encodeURIComponent(versionId)}`,
  );
}

export function deleteAllStageVersions(workflowId: string, stageType?: string) {
  return deleteJson<WorkflowDetail>(
    withQuery(`${workflowPath(workflowId)}/versions`, {
      stage_type: stageType,
    }),
  );
}

export interface WorkflowActionResponse {
  success: boolean;
  message?: string;
}

export function startAutoPilot(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/auto-pilot/start`, {});
}

export function pauseAutoPilot(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/auto-pilot/pause`, {});
}

export function resumeAutoPilot(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/auto-pilot/resume`, {});
}

export function terminateAutoPilot(workflowId: string) {
  return postJson<WorkflowDetail>(`${workflowPath(workflowId)}/auto-pilot/terminate`, {});
}
