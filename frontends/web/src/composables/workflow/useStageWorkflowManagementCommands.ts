import type { ComputedRef, Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { deleteWorkflow, generateVisualAsset, selectVisualAsset, updateWorkflowSettings } from "@/features/workflows";
import { buildWorkflowSettingsPayload, type WorkflowSettingsDraft } from "@/features/workflows/workflow-settings";
import { formatApiErrorMessage } from "@/utils/api-error";
import { messageApi } from "@/composables/useMessage";
import { characterSheetClipIndex, characterSheetIndex } from "@/composables/workflow/useCharacterSheetUtils";
import type { WorkflowCharacterSheet, WorkflowDetail, WorkflowSummary } from "@/types";

interface StageWorkflowManagementOptions {
  selectedWorkflowId: ComputedRef<string>;
  selectedWorkflow: Ref<WorkflowDetail | null>;
  busyActionKey: Ref<string>;
  workflowSettingsOpen: Ref<boolean>;
  workflowSettingsValidationMessage: ComputedRef<string>;
  workflowSettingsDraft: WorkflowSettingsDraft;
  missingCharacterSheets: ComputedRef<WorkflowCharacterSheet[]>;
  applyWorkflowDrafts: (workflow: WorkflowDetail | null) => void;
  loadWorkflows: () => Promise<void>;
  reloadCurrentWorkflow: () => Promise<void>;
  runAndRefresh: (actionKey: string, runner: () => Promise<WorkflowDetail>) => Promise<boolean>;
  requestConfirm: (options: { title: string; message: string; confirmText: string }) => Promise<boolean>;
  navigateAfterSelectedDelete: () => Promise<void>;
}

export interface StageWorkflowManagementDependencies {
  requireAuthentication: typeof requireAuth;
  updateSettings: typeof updateWorkflowSettings;
  generateCharacter: typeof generateVisualAsset;
  selectCharacterAsset: typeof selectVisualAsset;
  removeWorkflow: typeof deleteWorkflow;
  message: Pick<typeof messageApi, "error" | "warning">;
}

const defaultDependencies: StageWorkflowManagementDependencies = {
  requireAuthentication: requireAuth,
  updateSettings: updateWorkflowSettings,
  generateCharacter: generateVisualAsset,
  selectCharacterAsset: selectVisualAsset,
  removeWorkflow: deleteWorkflow,
  message: messageApi,
};

export function useStageWorkflowManagementCommands(
  options: StageWorkflowManagementOptions,
  overrides: Partial<StageWorkflowManagementDependencies> = {},
) {
  const dependencies = { ...defaultDependencies, ...overrides };

  async function handleUpdateWorkflowSettings() {
    if (!options.selectedWorkflowId.value || options.workflowSettingsValidationMessage.value) return;
    const succeeded = await options.runAndRefresh("workflow-settings", () =>
      dependencies.updateSettings(options.selectedWorkflowId.value, buildWorkflowSettingsPayload(options.workflowSettingsDraft))
    );
    if (succeeded) options.workflowSettingsOpen.value = false;
  }

  async function handleGenerateMissingCharacterSheets() {
    const workflowId = options.selectedWorkflowId.value;
    if (!workflowId) return;
    const pendingIndexes = options.missingCharacterSheets.value
      .map(characterSheetIndex)
      .filter((index): index is number => index !== null);
    if (!pendingIndexes.length) return;
    options.busyActionKey.value = "character-missing";
    try {
      for (const index of pendingIndexes) {
        options.selectedWorkflow.value = await dependencies.generateCharacter(workflowId, index);
        options.applyWorkflowDrafts(options.selectedWorkflow.value);
      }
      await options.loadWorkflows();
    } catch (error) {
      dependencies.message.error(formatApiErrorMessage(error, "公共素材生成失败"));
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleSelectCharacterSheetAsset(sheet: WorkflowCharacterSheet, assetId: string) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (!options.selectedWorkflowId.value || clipIndex === null) return;
    options.busyActionKey.value = `character-sheet-asset-${clipIndex}`;
    try {
      await dependencies.selectCharacterAsset(options.selectedWorkflowId.value, clipIndex, assetId);
      await options.reloadCurrentWorkflow();
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "公共素材选择失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleDeleteWorkflow(workflow: WorkflowSummary) {
    const authenticated = await dependencies.requireAuthentication({
      title: "登录后删除工作流",
      message: "删除工作流会修改你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      dependencies.message.warning("登录后可继续删除工作流。");
      return;
    }
    const confirmed = await options.requestConfirm({
      title: "删除工作流",
      message: `删除后不可恢复，工作流《${workflow.title}》及其所有生成版本都会一并删除。确认继续吗？`,
      confirmText: "删除",
    });
    if (!confirmed) return;
    options.busyActionKey.value = `delete-workflow-${workflow.id}`;
    try {
      const result = await dependencies.removeWorkflow(workflow.id);
      if (result.deleted && options.selectedWorkflowId.value === workflow.id) {
        options.selectedWorkflow.value = null;
        await options.navigateAfterSelectedDelete();
      }
      await options.loadWorkflows();
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "工作流删除失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  return {
    handleUpdateWorkflowSettings,
    handleGenerateMissingCharacterSheets,
    handleSelectCharacterSheetAsset,
    handleDeleteWorkflow,
  };
}
