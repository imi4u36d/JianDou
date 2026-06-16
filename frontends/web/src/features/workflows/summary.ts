import type {
  WorkflowDetail,
  WorkflowFrameFailureSummary,
  WorkflowStageOutputSummary,
  WorkflowSummary,
} from "@/types";

export type WorkflowCreateStageKey = "storyboard" | "keyframe" | "video";
export type WorkflowDetailRouteStageKey = WorkflowCreateStageKey | "character";
export type WorkflowCanvasStageKey = WorkflowDetailRouteStageKey | "final";
export type WorkflowFrameFailureRole = "first" | "last";

export interface WorkflowFrameFailure {
  role: WorkflowFrameFailureRole;
  message: string;
}

const DETAIL_STAGE_KEYS: WorkflowDetailRouteStageKey[] = ["storyboard", "character", "keyframe", "video"];

export function normalizeWorkflowDetailStage(value: unknown): WorkflowDetailRouteStageKey | null {
  const rawValue = Array.isArray(value) ? value[0] : value;
  if (typeof rawValue !== "string") {
    return null;
  }
  const normalizedValue = rawValue.trim().toLowerCase();
  if (normalizedValue === "joined") {
    return "video";
  }
  return DETAIL_STAGE_KEYS.includes(normalizedValue as WorkflowDetailRouteStageKey)
    ? normalizedValue as WorkflowDetailRouteStageKey
    : null;
}

export function normalizeWorkflowCanvasStage(value: unknown): WorkflowCanvasStageKey | null {
  const rawValue = Array.isArray(value) ? value[0] : value;
  if (typeof rawValue !== "string") {
    return null;
  }
  const normalizedValue = rawValue.trim().toLowerCase();
  if (normalizedValue === "joined" || normalizedValue === "final") {
    return "final";
  }
  return normalizeWorkflowDetailStage(normalizedValue);
}

export function workflowStageLabel(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (normalized === "storyboard") {
    return "分镜脚本";
  }
  if (normalized === "character") {
    return "角色三视图";
  }
  if (normalized === "keyframe") {
    return "关键帧";
  }
  if (normalized === "video") {
    return "视频片段";
  }
  if (normalized === "joined" || normalized === "final") {
    return "成片";
  }
  if (normalized === "material_center") {
    return "素材中心";
  }
  return value || "未开始";
}

export function workflowCanvasStageFromCurrent(
  workflow: WorkflowDetail,
  hasMissingCharacterSheets: (workflow: WorkflowDetail) => boolean
): WorkflowCanvasStageKey {
  const normalizedStage = normalizeWorkflowCanvasStage(workflow.currentStage);
  if (normalizedStage === "keyframe" && hasMissingCharacterSheets(workflow)) {
    return "character";
  }
  return normalizedStage ?? "storyboard";
}

export function workflowSummaryCanvasStage(workflow: WorkflowSummary): WorkflowCanvasStageKey {
  const normalizedStage = normalizeWorkflowCanvasStage(workflow.currentStage);
  if (normalizedStage === "keyframe") {
    const characterTotal = Number(workflow.characterSheetCount ?? 0);
    const selectedCharacterCount = Number(workflow.selectedCharacterSheetCount ?? 0);
    if (characterTotal > 0 && selectedCharacterCount < characterTotal) {
      return "character";
    }
  }
  return normalizedStage ?? "storyboard";
}

export function workflowSummaryCharacterCountLabel(workflow: WorkflowSummary) {
  const characterTotal = Number(workflow.characterSheetCount ?? 0);
  const selectedCharacterCount = Number(workflow.selectedCharacterSheetCount ?? workflow.characterSheetVersionCount ?? 0);
  if (Number.isFinite(characterTotal) && characterTotal > 0) {
    return `${selectedCharacterCount}/${characterTotal}`;
  }
  return Number.isFinite(selectedCharacterCount) ? String(selectedCharacterCount) : "0";
}

export function summaryUrlValue(summary: WorkflowStageOutputSummary | null | undefined, ...keys: (keyof WorkflowStageOutputSummary)[]) {
  for (const key of keys) {
    const value = summary?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

export function summaryUrlListValue(summary: WorkflowStageOutputSummary | null | undefined, ...keys: (keyof WorkflowStageOutputSummary)[]) {
  for (const key of keys) {
    const value = summary?.[key];
    if (Array.isArray(value)) {
      const urls = value.filter((item): item is string => typeof item === "string" && Boolean(item.trim()));
      if (urls.length) {
        return urls;
      }
    }
  }
  return [];
}

export function summaryNumberValue(summary: WorkflowStageOutputSummary | null | undefined, ...keys: (keyof WorkflowStageOutputSummary)[]) {
  for (const key of keys) {
    const value = summary?.[key];
    const numericValue = Number(value);
    if (Number.isFinite(numericValue) && numericValue > 0) {
      return numericValue;
    }
  }
  return 0;
}

export function summaryFrameFailures(summary: WorkflowStageOutputSummary | null | undefined): WorkflowFrameFailure[] {
  const value = summary?.frameFailures;
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item): item is WorkflowFrameFailureSummary => Boolean(item) && typeof item === "object" && !Array.isArray(item))
    .map((item): WorkflowFrameFailure => ({
      role: typeof item.frameRole === "string" && item.frameRole.trim() === "last" ? "last" : "first",
      message: typeof item.errorMessage === "string" ? item.errorMessage.trim() : "",
    }))
    .filter((item) => item.message);
}
