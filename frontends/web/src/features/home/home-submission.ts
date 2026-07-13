import type { CreateGenerationTaskRequest, CreateWorkflowRequest, MaterialAssetType } from "@/types";

export interface AppliedPromptTemplate {
  id: string;
  title: string;
  prompt: string;
}

export interface HomeSubmissionSnapshot {
  mode: string;
  prompt: string;
  template: AppliedPromptTemplate | null;
  aspectRatio: string;
  textAnalysisModel: string;
  imageModel: string;
  videoModel: string;
  videoSize: string;
  outputCount: number;
  supportsSeed: boolean;
  seedMode: "auto" | "manual";
  manualSeed: number | null;
  autoSeed: number;
  referenceImageUrls: string[];
}

export function buildCreativePrompt(prompt: string, template: AppliedPromptTemplate | null): string {
  const userPrompt = prompt.trim();
  if (!template) {
    return userPrompt;
  }
  const styledPrompt = template.prompt.replace("[主体]", userPrompt || "主体");
  return `${userPrompt}\n\n画风模板：${template.title}\n画风提示词：${styledPrompt}`;
}

export function resolveSubmissionSeed(snapshot: HomeSubmissionSnapshot): number | null {
  if (!snapshot.supportsSeed) {
    return null;
  }
  return snapshot.seedMode === "manual" ? snapshot.manualSeed : snapshot.autoSeed;
}

export function buildSubmitFingerprint(snapshot: HomeSubmissionSnapshot): string {
  return JSON.stringify({
    mode: snapshot.mode,
    prompt: snapshot.prompt.trim(),
    creativePrompt: buildCreativePrompt(snapshot.prompt, snapshot.template),
    aspectRatio: snapshot.aspectRatio,
    textAnalysisModel: snapshot.textAnalysisModel,
    imageModel: snapshot.imageModel,
    videoModel: snapshot.videoModel,
    videoSize: snapshot.videoSize,
    outputCount: snapshot.outputCount,
    seed: resolveSubmissionSeed(snapshot),
    references: [...snapshot.referenceImageUrls].sort(),
  });
}

export function buildImageGenerationRequest(
  snapshot: HomeSubmissionSnapshot,
  options: {
    assetType: MaterialAssetType | string;
    resolvedAspectRatio: string;
  },
): CreateGenerationTaskRequest {
  return {
    title: snapshot.prompt.trim().slice(0, 32) || "OpenAI 图片生成",
    taskType: snapshot.referenceImageUrls.length ? "image_to_image" : "image_generation",
    assetType: options.assetType,
    creativePrompt: buildCreativePrompt(snapshot.prompt, snapshot.template),
    aspectRatio: options.resolvedAspectRatio,
    imageSize: null,
    textAnalysisModel: snapshot.textAnalysisModel || null,
    imageModel: snapshot.imageModel || null,
    videoModel: null,
    videoSize: null,
    outputCount: snapshot.outputCount,
    seed: resolveSubmissionSeed(snapshot),
    referenceImageUrls: snapshot.referenceImageUrls,
    referenceAssetIds: [],
    transcriptText: "",
    stopBeforeVideoGeneration: false,
  };
}

export function buildVideoWorkflowRequest(
  snapshot: HomeSubmissionSnapshot,
  fallbackVideoSize: string | null,
): CreateWorkflowRequest {
  const creativePrompt = buildCreativePrompt(snapshot.prompt, snapshot.template);
  return {
    title: snapshot.prompt.trim().slice(0, 32) || "视频生成任务",
    transcriptText: creativePrompt || null,
    aspectRatio: snapshot.aspectRatio === "9:16" ? "9:16" : "16:9",
    textAnalysisModel: snapshot.textAnalysisModel,
    imageModel: snapshot.imageModel,
    videoModel: snapshot.videoModel,
    videoSize: snapshot.videoSize || fallbackVideoSize,
    durationMode: "auto",
    executionMode: "auto",
  };
}
