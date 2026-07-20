import type { Ref } from "vue";
import {
  adjustStoryboard,
  finalizeWorkflow,
  generateCharacterSheet,
  generateVisualAsset,
  generateKeyframe,
  generateKeyframeFrame,
  generateStoryboard,
  generateVideo,
  selectKeyframe,
  selectKeyframeFrame,
  selectStoryboard,
  selectVideo,
} from "@/features/workflows";
import { characterSheetClipIndex, characterSheetIndex } from "@/composables/workflow/useCharacterSheetUtils";
import type { WorkflowCharacterSheet, WorkflowDetail } from "@/types";

export interface WorkflowStageCommandApi {
  adjustStoryboard: typeof adjustStoryboard;
  finalizeWorkflow: typeof finalizeWorkflow;
  generateCharacterSheet: typeof generateCharacterSheet;
  generateVisualAsset?: typeof generateVisualAsset;
  generateKeyframe: typeof generateKeyframe;
  generateKeyframeFrame: typeof generateKeyframeFrame;
  generateStoryboard: typeof generateStoryboard;
  generateVideo: typeof generateVideo;
  selectKeyframe: typeof selectKeyframe;
  selectKeyframeFrame: typeof selectKeyframeFrame;
  selectStoryboard: typeof selectStoryboard;
  selectVideo: typeof selectVideo;
}

interface WorkflowStageCommandOptions {
  selectedWorkflowId: Readonly<Ref<string>>;
  runAndRefresh: (actionKey: string, runner: () => Promise<WorkflowDetail>) => Promise<boolean>;
  storyboardAdjustment: (versionId: string) => string;
  setStoryboardAdjustment: (versionId: string, value: string) => void;
}

const defaultApi: WorkflowStageCommandApi = {
  adjustStoryboard,
  finalizeWorkflow,
  generateCharacterSheet,
  generateVisualAsset,
  generateKeyframe,
  generateKeyframeFrame,
  generateStoryboard,
  generateVideo,
  selectKeyframe,
  selectKeyframeFrame,
  selectStoryboard,
  selectVideo,
};

export function useWorkflowStageCommands(options: WorkflowStageCommandOptions, api: WorkflowStageCommandApi = defaultApi) {
  function run(actionKey: string, command: (workflowId: string) => Promise<WorkflowDetail>) {
    const workflowId = options.selectedWorkflowId.value;
    if (!workflowId) return Promise.resolve(false);
    return options.runAndRefresh(actionKey, () => command(workflowId));
  }

  async function handleGenerateStoryboard() {
    await run("storyboard", api.generateStoryboard);
  }

  async function handleAdjustStoryboard(versionId: string) {
    const prompt = options.storyboardAdjustment(versionId).trim();
    const succeeded = await run(`storyboard-adjust-${versionId}`, (workflowId) => api.adjustStoryboard(workflowId, versionId, prompt));
    if (succeeded) options.setStoryboardAdjustment(versionId, "");
  }

  async function handleSelectStoryboard(versionId: string) {
    await run(versionId, (workflowId) => api.selectStoryboard(workflowId, versionId));
  }

  async function handleGenerateKeyframe(clipIndex: number) {
    await run(`keyframe-${clipIndex}`, (workflowId) => api.generateKeyframe(workflowId, clipIndex));
  }

  async function handleGenerateCharacterSheet(sheet: WorkflowCharacterSheet) {
    const index = characterSheetIndex(sheet);
    if (index === null) return;
    const clipIndex = characterSheetClipIndex(sheet) ?? index;
    const generator = api.generateVisualAsset ?? api.generateCharacterSheet;
    await run(`character-sheet-${clipIndex}`, (workflowId) => generator(workflowId, index));
  }

  async function handleGenerateKeyframeFrame(clipIndex: number, frameRole: string) {
    await run(`keyframe-${clipIndex}-${frameRole}`, (workflowId) => api.generateKeyframeFrame(workflowId, clipIndex, frameRole));
  }

  async function handleSelectKeyframe(clipIndex: number, versionId: string) {
    await run(versionId, (workflowId) => api.selectKeyframe(workflowId, clipIndex, versionId));
  }

  async function handleSelectKeyframeFrame(clipIndex: number, versionId: string, frameRole: string) {
    await run(`${versionId}-${frameRole}`, (workflowId) => api.selectKeyframeFrame(workflowId, clipIndex, versionId, frameRole));
  }

  async function handleGenerateVideo(clipIndex: number) {
    await run(`video-${clipIndex}`, (workflowId) => api.generateVideo(workflowId, clipIndex));
  }

  async function handleSelectVideo(clipIndex: number, versionId: string) {
    await run(versionId, (workflowId) => api.selectVideo(workflowId, clipIndex, versionId));
  }

  async function handleFinalize() {
    await run("finalize", api.finalizeWorkflow);
  }

  return {
    handleGenerateStoryboard,
    handleAdjustStoryboard,
    handleSelectStoryboard,
    handleGenerateKeyframe,
    handleGenerateCharacterSheet,
    handleGenerateKeyframeFrame,
    handleSelectKeyframe,
    handleSelectKeyframeFrame,
    handleGenerateVideo,
    handleSelectVideo,
    handleFinalize,
  };
}
