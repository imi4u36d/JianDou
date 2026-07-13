import type { ComputedRef, Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import {
  adjustStoryboard,
  finalizeWorkflow,
  generateCharacterSheet,
  generateKeyframe,
  generateKeyframeFrame,
  generateStoryboard,
  generateVideo,
  selectCharacterSheetAsset,
  selectKeyframe,
  selectKeyframeFrame,
  selectStoryboard,
  selectVideo,
  updateWorkflowSettings,
} from "@/features/workflows";
import { characterSheetClipIndex, characterSheetIndex } from "@/composables/workflow/useCharacterSheetUtils";
import { messageApi } from "@/composables/useMessage";
import { formatApiErrorMessage } from "@/utils/api-error";
import type { UpdateWorkflowSettingsRequest, WorkflowCharacterSheet, WorkflowDetail } from "@/types";

interface WorkflowGenerationCommandOptions {
  selectedWorkflowId: ComputedRef<string>;
  selectedWorkflow: Ref<WorkflowDetail | null>;
  busyActionKey: Ref<string>;
  workflowSettingsValidationMessage: ComputedRef<string>;
  workflowSettingsOpen: Ref<boolean>;
  storyboardAdjustmentDrafts: Record<string, string>;
  missingCharacterSheets: ComputedRef<WorkflowCharacterSheet[]>;
  applyWorkflowDrafts: (workflow: WorkflowDetail | null) => void;
  reloadWorkflows: () => Promise<void>;
  buildWorkflowSettingsPayload: () => UpdateWorkflowSettingsRequest;
  closeCharacterAssetPicker: () => void;
  reloadCurrentWorkflow: () => Promise<void>;
}

export interface WorkflowGenerationCommandDependencies {
  requireAuthentication: typeof requireAuth;
  updateSettings: typeof updateWorkflowSettings;
  generateStoryboard: typeof generateStoryboard;
  adjustStoryboard: typeof adjustStoryboard;
  selectStoryboard: typeof selectStoryboard;
  generateKeyframe: typeof generateKeyframe;
  generateCharacterSheet: typeof generateCharacterSheet;
  generateKeyframeFrame: typeof generateKeyframeFrame;
  selectKeyframe: typeof selectKeyframe;
  selectKeyframeFrame: typeof selectKeyframeFrame;
  selectCharacterSheetAsset: typeof selectCharacterSheetAsset;
  generateVideo: typeof generateVideo;
  selectVideo: typeof selectVideo;
  finalizeWorkflow: typeof finalizeWorkflow;
  message: Pick<typeof messageApi, "error" | "warning">;
}

const defaults: WorkflowGenerationCommandDependencies = {
  requireAuthentication: requireAuth,
  updateSettings: updateWorkflowSettings,
  generateStoryboard,
  adjustStoryboard,
  selectStoryboard,
  generateKeyframe,
  generateCharacterSheet,
  generateKeyframeFrame,
  selectKeyframe,
  selectKeyframeFrame,
  selectCharacterSheetAsset,
  generateVideo,
  selectVideo,
  finalizeWorkflow,
  message: messageApi,
};

export function useWorkflowGenerationCommands(
  options: WorkflowGenerationCommandOptions,
  overrides: Partial<WorkflowGenerationCommandDependencies> = {},
) {
  const dependencies = { ...defaults, ...overrides };

  async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>) {
    const authenticated = await dependencies.requireAuthentication({
      title: "登录后操作工作流",
      message: "工作流操作会修改你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      dependencies.message.warning("登录后可继续操作工作流。");
      return false;
    }
    options.busyActionKey.value = actionKey;
    try {
      options.selectedWorkflow.value = await runner();
      options.applyWorkflowDrafts(options.selectedWorkflow.value);
      await options.reloadWorkflows();
      return true;
    } catch (error) {
      dependencies.message.error(formatApiErrorMessage(error, "操作失败"));
      return false;
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleUpdateWorkflowSettings() {
    if (!options.selectedWorkflowId.value || options.workflowSettingsValidationMessage.value) return;
    const succeeded = await runAndRefresh("workflow-settings", () =>
      dependencies.updateSettings(options.selectedWorkflowId.value, options.buildWorkflowSettingsPayload())
    );
    if (succeeded) options.workflowSettingsOpen.value = false;
  }

  async function handleGenerateStoryboard() {
    if (options.selectedWorkflowId.value) {
      await runAndRefresh("storyboard", () => dependencies.generateStoryboard(options.selectedWorkflowId.value));
    }
  }

  async function handleAdjustStoryboard(versionId: string) {
    if (!options.selectedWorkflowId.value) return;
    const prompt = (options.storyboardAdjustmentDrafts[versionId] || "").trim();
    const succeeded = await runAndRefresh(`storyboard-adjust-${versionId}`, () =>
      dependencies.adjustStoryboard(options.selectedWorkflowId.value, versionId, prompt)
    );
    if (succeeded) options.storyboardAdjustmentDrafts[versionId] = "";
  }

  async function handleSelectStoryboard(versionId: string) {
    if (options.selectedWorkflowId.value) {
      await runAndRefresh(versionId, () => dependencies.selectStoryboard(options.selectedWorkflowId.value, versionId));
    }
  }

  async function handleGenerateKeyframe(clipIndex: number) {
    if (options.selectedWorkflowId.value) {
      await runAndRefresh(`keyframe-${clipIndex}`, () => dependencies.generateKeyframe(options.selectedWorkflowId.value, clipIndex));
    }
  }

  async function handleGenerateMissingCharacterSheets() {
    if (!options.selectedWorkflowId.value) return;
    const indexes = options.missingCharacterSheets.value.map(characterSheetIndex).filter((index): index is number => index !== null);
    if (!indexes.length) return;
    options.busyActionKey.value = "character-missing";
    try {
      for (const index of indexes) {
        options.selectedWorkflow.value = await dependencies.generateCharacterSheet(options.selectedWorkflowId.value, index);
        options.applyWorkflowDrafts(options.selectedWorkflow.value);
      }
      await options.reloadWorkflows();
    } catch (error) {
      dependencies.message.error(formatApiErrorMessage(error, "角色三视图生成失败"));
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleGenerateCharacterSheet(sheet: WorkflowCharacterSheet) {
    const index = characterSheetIndex(sheet);
    if (!options.selectedWorkflowId.value || index === null) return;
    const clipIndex = characterSheetClipIndex(sheet) ?? index;
    await runAndRefresh(`character-sheet-${clipIndex}`, () => dependencies.generateCharacterSheet(options.selectedWorkflowId.value, index));
  }

  async function handleGenerateKeyframeFrame(clipIndex: number, frameRole: string) {
    if (options.selectedWorkflowId.value) await runAndRefresh(`keyframe-${clipIndex}-${frameRole}`, () => dependencies.generateKeyframeFrame(options.selectedWorkflowId.value, clipIndex, frameRole));
  }

  async function handleSelectKeyframe(clipIndex: number, versionId: string) {
    if (options.selectedWorkflowId.value) await runAndRefresh(versionId, () => dependencies.selectKeyframe(options.selectedWorkflowId.value, clipIndex, versionId));
  }

  async function handleSelectCharacterSheetVersion(sheet: WorkflowCharacterSheet, versionId: string) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (options.selectedWorkflowId.value && clipIndex !== null) await runAndRefresh(versionId, () => dependencies.selectKeyframe(options.selectedWorkflowId.value, clipIndex, versionId));
  }

  async function handleSelectKeyframeFrame(clipIndex: number, versionId: string, frameRole: string) {
    if (options.selectedWorkflowId.value) await runAndRefresh(`${versionId}-${frameRole}`, () => dependencies.selectKeyframeFrame(options.selectedWorkflowId.value, clipIndex, versionId, frameRole));
  }

  async function handleSelectCharacterSheetAsset(sheet: WorkflowCharacterSheet, assetId: string) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (!options.selectedWorkflowId.value || clipIndex === null) return;
    options.busyActionKey.value = `character-sheet-asset-${clipIndex}`;
    try {
      await dependencies.selectCharacterSheetAsset(options.selectedWorkflowId.value, clipIndex, assetId);
      options.closeCharacterAssetPicker();
      await options.reloadCurrentWorkflow();
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "角色三视图素材选择失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleGenerateVideo(clipIndex: number) {
    if (options.selectedWorkflowId.value) await runAndRefresh(`video-${clipIndex}`, () => dependencies.generateVideo(options.selectedWorkflowId.value, clipIndex));
  }

  async function handleSelectVideo(clipIndex: number, versionId: string) {
    if (options.selectedWorkflowId.value) await runAndRefresh(versionId, () => dependencies.selectVideo(options.selectedWorkflowId.value, clipIndex, versionId));
  }

  async function handleFinalize() {
    if (options.selectedWorkflowId.value) await runAndRefresh("finalize", () => dependencies.finalizeWorkflow(options.selectedWorkflowId.value));
  }

  return {
    handleUpdateWorkflowSettings, handleGenerateStoryboard, handleAdjustStoryboard, handleSelectStoryboard,
    handleGenerateKeyframe, handleGenerateMissingCharacterSheets, handleGenerateCharacterSheet,
    handleGenerateKeyframeFrame, handleSelectKeyframe, handleSelectCharacterSheetVersion,
    handleSelectKeyframeFrame, handleSelectCharacterSheetAsset, handleGenerateVideo, handleSelectVideo,
    handleFinalize,
  };
}
