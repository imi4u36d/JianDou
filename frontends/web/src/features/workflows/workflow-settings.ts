export interface WorkflowSettingsDraft {
  aspectRatio: string;
  textAnalysisModel: string;
  imageModel: string;
  videoModel: string;
  videoSize: string;
  keyframeSeed: string;
  videoSeed: string;
  durationMode: "auto" | "manual";
  minDurationSeconds: string;
  maxDurationSeconds: string;
}

export interface WorkflowParameterTag {
  label: string;
  value: string;
}

export const WORKFLOW_MANUAL_DURATION_MIN_SECONDS = 5;
export const WORKFLOW_MANUAL_DURATION_MAX_SECONDS = 12;

export function optionalWorkflowInteger(value?: string | number | null): number | null {
  if (value === undefined || value === null || value === "") {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) && Number.isInteger(numeric) ? Math.trunc(numeric) : null;
}

export function withWorkflowSetting<K extends keyof WorkflowSettingsDraft>(
  settings: WorkflowSettingsDraft,
  key: K,
  value: WorkflowSettingsDraft[K],
): WorkflowSettingsDraft {
  return { ...settings, [key]: value };
}

export function createWorkflowSettingsDraft(): WorkflowSettingsDraft {
  return {
    aspectRatio: "16:9",
    textAnalysisModel: "",
    imageModel: "",
    videoModel: "",
    videoSize: "",
    keyframeSeed: "",
    videoSeed: "",
    durationMode: "auto",
    minDurationSeconds: String(WORKFLOW_MANUAL_DURATION_MIN_SECONDS),
    maxDurationSeconds: String(WORKFLOW_MANUAL_DURATION_MAX_SECONDS),
  };
}

export function workflowSettingsDraftFromDetail(workflow: WorkflowDetail): WorkflowSettingsDraft {
  return {
    aspectRatio: workflow.aspectRatio || "16:9",
    textAnalysisModel: workflow.textAnalysisModel || "",
    imageModel: workflow.imageModel || "",
    videoModel: workflow.videoModel || "",
    videoSize: workflow.videoSize || "",
    keyframeSeed: workflow.keyframeSeed == null ? "" : String(workflow.keyframeSeed),
    videoSeed: workflow.videoSeed == null ? "" : String(workflow.videoSeed),
    durationMode: workflow.durationMode === "manual" ? "manual" : "auto",
    minDurationSeconds: String(workflow.minDurationSeconds ?? WORKFLOW_MANUAL_DURATION_MIN_SECONDS),
    maxDurationSeconds: String(workflow.maxDurationSeconds ?? WORKFLOW_MANUAL_DURATION_MAX_SECONDS),
  };
}

export function validateWorkflowSettingsDraft(draft: WorkflowSettingsDraft): string {
  if (!draft.textAnalysisModel) return "请选择文本模型";
  if (!draft.imageModel) return "请选择关键帧模型";
  if (!draft.aspectRatio) return "请选择画幅";
  if (!draft.videoModel) return "请选择视频模型";
  if (!draft.videoSize) return "请选择输出尺寸";
  if (draft.durationMode === "auto") return "";
  const minDuration = optionalWorkflowInteger(draft.minDurationSeconds);
  const maxDuration = optionalWorkflowInteger(draft.maxDurationSeconds);
  if (minDuration === null || maxDuration === null || minDuration < 1 || maxDuration < 1) {
    return "请填写合法的镜头时长";
  }
  return maxDuration < minDuration ? "最大时长不能小于最小时长" : "";
}

export function buildWorkflowSettingsPayload(draft: WorkflowSettingsDraft): UpdateWorkflowSettingsRequest {
  return {
    aspectRatio: draft.aspectRatio,
    textAnalysisModel: draft.textAnalysisModel,
    imageModel: draft.imageModel,
    videoModel: draft.videoModel,
    videoSize: draft.videoSize,
    keyframeSeed: optionalWorkflowInteger(draft.keyframeSeed),
    videoSeed: optionalWorkflowInteger(draft.videoSeed),
    durationMode: draft.durationMode,
    minDurationSeconds: draft.durationMode === "auto" ? null : optionalWorkflowInteger(draft.minDurationSeconds),
    maxDurationSeconds: draft.durationMode === "auto" ? null : optionalWorkflowInteger(draft.maxDurationSeconds),
  };
}
import type { UpdateWorkflowSettingsRequest, WorkflowDetail } from "@/types";
