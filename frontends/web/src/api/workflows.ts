/**
 * 阶段化工作流 API 请求封装。
 */
import { deleteJson, getJson, patchJson, postJson } from "./client";
import type {
  CreateWorkflowRequest,
  RateStageVersionRequest,
  RateWorkflowRequest,
  UpdateWorkflowSettingsRequest,
  WorkflowDeleteResult,
  WorkflowDetail,
  WorkflowSummary,
} from "@/types";

export function createWorkflow(payload: CreateWorkflowRequest) {
  return postJson<WorkflowDetail>("/workflows", payload);
}

export function fetchWorkflows() {
  return getJson<WorkflowSummary[]>("/workflows");
}

export function fetchWorkflow(workflowId: string) {
  return getJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}`);
}

export function deleteWorkflow(workflowId: string) {
  return deleteJson<WorkflowDeleteResult>(`/workflows/${encodeURIComponent(workflowId)}`);
}

export function updateWorkflowSettings(workflowId: string, payload: UpdateWorkflowSettingsRequest) {
  return patchJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/settings`, payload);
}

export function generateStoryboard(workflowId: string) {
  return postJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/storyboards/generate`, {});
}

export function adjustStoryboard(workflowId: string, versionId: string, prompt?: string | null) {
  const normalizedPrompt = typeof prompt === "string" ? prompt.trim() : "";
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/storyboards/${encodeURIComponent(versionId)}/adjust`,
    normalizedPrompt ? { prompt: normalizedPrompt } : {}
  );
}

export function selectStoryboard(workflowId: string, versionId: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/storyboards/${encodeURIComponent(versionId)}/select`,
    {}
  );
}

export function generateKeyframe(workflowId: string, clipIndex: number) {
  return postJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/keyframes/generate`, {});
}

export function generateKeyframeFrame(workflowId: string, clipIndex: number, frameRole: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(frameRole)}/generate`,
    {}
  );
}

export function selectKeyframe(workflowId: string, clipIndex: number, versionId: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(versionId)}/select`,
    {}
  );
}

export function selectKeyframeFrame(workflowId: string, clipIndex: number, versionId: string, frameRole: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/keyframes/${encodeURIComponent(versionId)}/frames/${encodeURIComponent(frameRole)}/select`,
    {}
  );
}

export function selectCharacterSheetAsset(workflowId: string, clipIndex: number, assetId: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/character-sheets/${clipIndex}/select-asset`,
    { assetId }
  );
}

export function generateVideo(workflowId: string, clipIndex: number) {
  return postJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/videos/generate`, {});
}

export function selectVideo(workflowId: string, clipIndex: number, versionId: string) {
  return postJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/clips/${clipIndex}/videos/${encodeURIComponent(versionId)}/select`,
    {}
  );
}

export function finalizeWorkflow(workflowId: string) {
  return postJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/finalize`, {});
}

export function rateWorkflow(workflowId: string, payload: RateWorkflowRequest) {
  return postJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/rating`, payload);
}

export function rateStageVersion(workflowId: string, versionId: string, payload: RateStageVersionRequest) {
  return patchJson<WorkflowDetail>(
    `/workflows/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(versionId)}/rating`,
    payload
  );
}

export function deleteStageVersion(workflowId: string, versionId: string) {
  return deleteJson<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(versionId)}`);
}
