import type { ComputedRef, Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { deleteAllStageVersions, deleteStageVersion, fetchWorkflow, reuseMaterialAsset } from "@/features/workflows";
import { messageApi } from "@/composables/useMessage";
import { characterSheetVersions } from "@/composables/workflow/useCharacterSheetUtils";
import type { StageVersion, WorkflowCharacterSheet, WorkflowDetail } from "@/types";

interface WorkflowVersionCommandOptions {
  selectedWorkflowId: ComputedRef<string>;
  selectedWorkflow: Ref<WorkflowDetail | null>;
  busyActionKey: Ref<string>;
  workflowCharacterSheets: ComputedRef<WorkflowCharacterSheet[]>;
  applyWorkflowDrafts: (workflow: WorkflowDetail | null) => void;
  reloadWorkflows: () => Promise<void>;
  requestConfirm: (options: { title: string; message: string; confirmText: string }) => Promise<boolean>;
  deleteVersionConfirmMessage?: (version: StageVersion) => string;
  onReused?: (workflow: WorkflowDetail) => void | Promise<void>;
}

export interface WorkflowVersionCommandDependencies {
  requireAuthentication: typeof requireAuth;
  deleteAllVersions: typeof deleteAllStageVersions;
  deleteVersion: typeof deleteStageVersion;
  fetchWorkflowDetail: typeof fetchWorkflow;
  reuseAsset: typeof reuseMaterialAsset;
  message: Pick<typeof messageApi, "error" | "warning">;
}

const defaultDependencies: WorkflowVersionCommandDependencies = {
  requireAuthentication: requireAuth,
  deleteAllVersions: deleteAllStageVersions,
  deleteVersion: deleteStageVersion,
  fetchWorkflowDetail: fetchWorkflow,
  reuseAsset: reuseMaterialAsset,
  message: messageApi,
};

export function useWorkflowVersionCommands(
  options: WorkflowVersionCommandOptions,
  overrides: Partial<WorkflowVersionCommandDependencies> = {},
) {
  const dependencies = { ...defaultDependencies, ...overrides };
  async function handleDeleteStageVersion(version: StageVersion) {
    const authenticated = await dependencies.requireAuthentication({
      title: "登录后删除版本",
      message: "删除版本会修改你的工作流数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      dependencies.message.warning("登录后可继续删除版本。");
      return;
    }
    if (!options.selectedWorkflowId.value) return;
    const confirmed = await options.requestConfirm({
      title: "删除版本",
      message: options.deleteVersionConfirmMessage?.(version) ?? "删除后不可恢复，确认删除这个版本吗？",
      confirmText: "删除",
    });
    if (!confirmed) return;
    options.busyActionKey.value = `delete-${version.id}`;
    try {
      options.selectedWorkflow.value = await dependencies.deleteVersion(options.selectedWorkflowId.value, version.id);
      options.applyWorkflowDrafts(options.selectedWorkflow.value);
      await options.reloadWorkflows();
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "版本删除失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleClearStageVersions(stageType: string) {
    const stageLabel = stageType === "storyboard" ? "分镜" : stageType === "character" ? "角色三视图" : stageType === "keyframe" ? "关键帧" : "视频";
    const authenticated = await dependencies.requireAuthentication({
      title: `登录后清空${stageLabel}版本`,
      message: `清空${stageLabel}版本会修改你的工作流数据，请先登录或使用邀请码注册。`,
    });
    if (!authenticated) {
      dependencies.message.warning("登录后可继续操作。");
      return;
    }
    if (!options.selectedWorkflowId.value) return;
    const confirmed = await options.requestConfirm({
      title: `清空${stageLabel}版本`,
      message: `删除后不可恢复，该工作流下的全部${stageLabel}版本都会被清空。确认继续吗？`,
      confirmText: "清空",
    });
    if (!confirmed) return;
    options.busyActionKey.value = `clear-${stageType}-versions`;
    try {
      if (stageType === "character") {
        const versions = options.workflowCharacterSheets.value.flatMap(characterSheetVersions);
        for (const version of versions) {
          options.selectedWorkflow.value = await dependencies.deleteVersion(options.selectedWorkflowId.value, version.id);
          options.applyWorkflowDrafts(options.selectedWorkflow.value);
        }
        if (!versions.length) {
          options.selectedWorkflow.value = await dependencies.fetchWorkflowDetail(options.selectedWorkflowId.value);
        }
      } else {
        options.selectedWorkflow.value = await dependencies.deleteAllVersions(options.selectedWorkflowId.value, stageType);
      }
      options.applyWorkflowDrafts(options.selectedWorkflow.value);
      await options.reloadWorkflows();
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "版本清空失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleReuseAsset(assetId: string, versionId: string) {
    if (!assetId) return;
    const authenticated = await dependencies.requireAuthentication({
      title: "登录后复用素材",
      message: "复用素材会创建你的阶段工作流，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      dependencies.message.warning("登录后可继续复用素材。");
      return;
    }
    options.busyActionKey.value = `reuse-${versionId}`;
    try {
      const workflow = await dependencies.reuseAsset(assetId, { mode: "clone" });
      await options.reloadWorkflows();
      await options.onReused?.(workflow);
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "素材复用失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  return { handleDeleteStageVersion, handleClearStageVersions, handleReuseAsset };
}
