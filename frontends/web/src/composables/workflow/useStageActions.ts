import { ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { formatApiErrorMessage } from "@/utils/api-error";
import { messageApi } from "@/composables/useMessage";
import {
  adjustStoryboard,
  deleteStageVersion,
  deleteWorkflow,
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
import type { WorkflowCharacterSheet, WorkflowDetail, WorkflowSummary, WorkflowDeleteResult, UpdateWorkflowSettingsRequest } from "@/types";
import { characterSheetClipIndex, characterSheetIndex } from "./useCharacterSheetUtils";

export function useStageActions(deps: {
  selectedWorkflowId: () => string;
  selectedWorkflow: { value: WorkflowDetail | null };
  applyWorkflowDrafts: (workflow: WorkflowDetail | null) => void;
  loadWorkflows: () => Promise<void>;
  reloadCurrentWorkflow: () => Promise<void>;
  closeCharacterAssetPicker: () => void;
  confirmDeleteWorkflow?: (message: string) => Promise<boolean>;
}) {
  const busyActionKey = ref("");
  const workflowSettingsOpen = ref(false);

  async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>): Promise<boolean> {
    const authenticated = await requireAuth({
      title: "登录后操作工作流",
      message: "工作流操作会修改你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      messageApi.warning("登录后可继续操作工作流。");
      return false;
    }
    busyActionKey.value = actionKey;
    try {
      deps.selectedWorkflow.value = await runner();
      deps.applyWorkflowDrafts(deps.selectedWorkflow.value);
      await deps.loadWorkflows();
      return true;
    } catch (error) {
      messageApi.error(formatApiErrorMessage(error, "操作失败"));
      return false;
    } finally {
      busyActionKey.value = "";
    }
  }

  async function handleUpdateWorkflowSettings(payload: UpdateWorkflowSettingsRequest) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    const succeeded = await runAndRefresh("workflow-settings", () => updateWorkflowSettings(workflowId, payload));
    if (succeeded) {
      workflowSettingsOpen.value = false;
    }
  }

  async function handleGenerateStoryboard() {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh("storyboard", () => generateStoryboard(workflowId));
  }

  async function handleAdjustStoryboard(versionId: string, prompt: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`storyboard-adjust-${versionId}`, () => adjustStoryboard(workflowId, versionId, prompt));
  }

  async function handleSelectStoryboard(versionId: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(versionId, () => selectStoryboard(workflowId, versionId));
  }

  async function handleGenerateKeyframe(clipIndex: number) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`keyframe-${clipIndex}`, () => generateKeyframe(workflowId, clipIndex));
  }

  async function handleGenerateMissingCharacterSheets(missingSheets: WorkflowCharacterSheet[]) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    const pendingCharacterIndexes = missingSheets
      .map((sheet) => characterSheetIndex(sheet))
      .filter((index): index is number => index !== null);
    if (!pendingCharacterIndexes.length) return;
    busyActionKey.value = "character-missing";
    try {
      for (const index of pendingCharacterIndexes) {
        deps.selectedWorkflow.value = await generateCharacterSheet(workflowId, index);
        deps.applyWorkflowDrafts(deps.selectedWorkflow.value);
      }
      await deps.loadWorkflows();
    } catch (error) {
      messageApi.error(formatApiErrorMessage(error, "角色三视图生成失败"));
    } finally {
      busyActionKey.value = "";
    }
  }

  async function handleGenerateKeyframeFrame(clipIndex: number, frameRole: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`keyframe-${clipIndex}-${frameRole}`, () => generateKeyframeFrame(workflowId, clipIndex, frameRole));
  }

  async function handleSelectKeyframe(clipIndex: number, versionId: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(versionId, () => selectKeyframe(workflowId, clipIndex, versionId));
  }

  async function handleSelectKeyframeFrame(clipIndex: number, versionId: string, frameRole: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`${versionId}-${frameRole}`, () => selectKeyframeFrame(workflowId, clipIndex, versionId, frameRole));
  }

  async function handleSelectCharacterSheetAsset(sheet: WorkflowCharacterSheet, assetId: string) {
    const workflowId = deps.selectedWorkflowId();
    const clipIndex = characterSheetClipIndex(sheet);
    if (!workflowId || clipIndex === null) return;
    busyActionKey.value = `character-sheet-asset-${clipIndex}`;
    try {
      await selectCharacterSheetAsset(workflowId, clipIndex, assetId);
      deps.closeCharacterAssetPicker();
      await deps.reloadCurrentWorkflow();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "角色三视图素材选择失败");
    } finally {
      busyActionKey.value = "";
    }
  }

  async function handleGenerateVideo(clipIndex: number) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`video-${clipIndex}`, () => generateVideo(workflowId, clipIndex));
  }

  async function handleSelectVideo(clipIndex: number, versionId: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(versionId, () => selectVideo(workflowId, clipIndex, versionId));
  }

  async function handleFinalize() {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh("finalize", () => finalizeWorkflow(workflowId));
  }

  function stageTypeLabel(stageType: string): string {
    switch (stageType) {
      case "storyboard": return "分镜";
      case "keyframe": return "关键帧";
      case "video": return "视频";
      default: return "版本";
    }
  }

  function deleteWorkflowConfirmMessage(workflow: WorkflowSummary): string {
    return `删除后不可恢复，工作流《${workflow.title}》及其所有生成版本都会一并删除。确认继续吗？`;
  }

  function deleteVersionConfirmMessage(version: { stageType: string }): string {
    const label = stageTypeLabel(version.stageType);
    if (version.stageType === "storyboard") {
      return `删除后不可恢复。删除该${label}版本时，与它关联的关键帧和视频版本也会一并删除。确认继续吗？`;
    }
    if (version.stageType === "keyframe") {
      return `删除后不可恢复。删除该${label}版本时，依赖它生成的视频版本也会一并删除。确认继续吗？`;
    }
    return `删除后不可恢复，确认删除这个${label}版本吗？`;
  }

  async function handleDeleteWorkflow(workflow: WorkflowSummary, pushRoute: () => Promise<void>) {
    const authenticated = await requireAuth({
      title: "登录后删除工作流",
      message: "删除工作流会修改你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      messageApi.warning("登录后可继续删除工作流。");
      return;
    }
    if (!deps.confirmDeleteWorkflow) {
      messageApi.warning("缺少删除确认控件。");
      return;
    }
    if (!(await deps.confirmDeleteWorkflow(deleteWorkflowConfirmMessage(workflow)))) return;
    const actionKey = `delete-workflow-${workflow.id}`;
    busyActionKey.value = actionKey;
    try {
      const result: WorkflowDeleteResult = await deleteWorkflow(workflow.id);
      if (result.deleted && deps.selectedWorkflowId() === workflow.id) {
        deps.selectedWorkflow.value = null;
        await pushRoute();
      }
      await deps.loadWorkflows();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "工作流删除失败");
    } finally {
      busyActionKey.value = "";
    }
  }

  async function handleDeleteStageVersion(versionId: string) {
    const workflowId = deps.selectedWorkflowId();
    if (!workflowId) return;
    await runAndRefresh(`delete-${versionId}`, () => deleteStageVersion(workflowId, versionId));
  }

  return {
    busyActionKey,
    workflowSettingsOpen,
    runAndRefresh,
    handleUpdateWorkflowSettings,
    handleGenerateStoryboard,
    handleAdjustStoryboard,
    handleSelectStoryboard,
    handleGenerateKeyframe,
    handleGenerateMissingCharacterSheets,
    handleGenerateKeyframeFrame,
    handleSelectKeyframe,
    handleSelectKeyframeFrame,
    handleSelectCharacterSheetAsset,
    handleGenerateVideo,
    handleSelectVideo,
    handleFinalize,
    handleDeleteWorkflow,
    handleDeleteStageVersion,
    stageTypeLabel,
    deleteWorkflowConfirmMessage,
    deleteVersionConfirmMessage,
  };
}
