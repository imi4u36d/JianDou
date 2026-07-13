import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useWorkflowVersionCommands } from "@/views/unified/composables/useWorkflowVersionCommands";
import type { StageVersion, WorkflowDetail } from "@/types";

function harness() {
  const workflow = { id: "workflow-1", characterSheets: [] } as unknown as WorkflowDetail;
  const selectedWorkflow = ref<WorkflowDetail | null>(workflow);
  const busyActionKey = ref("");
  const reloadWorkflows = vi.fn(async () => undefined);
  const applyWorkflowDrafts = vi.fn();
  const requestConfirm = vi.fn(async () => true);
  const dependencies = {
    requireAuthentication: vi.fn(async () => true),
    deleteAllVersions: vi.fn(async () => workflow),
    deleteVersion: vi.fn(async () => workflow),
    fetchWorkflowDetail: vi.fn(async () => workflow),
    reuseAsset: vi.fn(async () => ({ success: true } as never)),
    message: { error: vi.fn(), warning: vi.fn() },
  };
  const commands = useWorkflowVersionCommands({
    selectedWorkflowId: computed(() => "workflow-1"),
    selectedWorkflow,
    busyActionKey,
    workflowCharacterSheets: computed(() => []),
    applyWorkflowDrafts,
    reloadWorkflows,
    requestConfirm,
  }, dependencies);
  return { workflow, busyActionKey, reloadWorkflows, applyWorkflowDrafts, requestConfirm, dependencies, commands };
}

describe("workflow version commands", () => {
  it("authenticates, confirms and refreshes after deleting a version", async () => {
    const context = harness();
    const version = { id: "version-1" } as StageVersion;

    await context.commands.handleDeleteStageVersion(version);

    expect(context.dependencies.requireAuthentication).toHaveBeenCalledOnce();
    expect(context.requestConfirm).toHaveBeenCalledOnce();
    expect(context.dependencies.deleteVersion).toHaveBeenCalledWith("workflow-1", "version-1");
    expect(context.applyWorkflowDrafts).toHaveBeenCalledWith(context.workflow);
    expect(context.reloadWorkflows).toHaveBeenCalledOnce();
    expect(context.busyActionKey.value).toBe("");
  });

  it("does not mutate data when authentication is rejected", async () => {
    const context = harness();
    context.dependencies.requireAuthentication.mockResolvedValue(false);

    await context.commands.handleReuseAsset("asset-1", "version-1");

    expect(context.dependencies.reuseAsset).not.toHaveBeenCalled();
    expect(context.dependencies.message.warning).toHaveBeenCalledOnce();
  });

  it("supports page-specific confirmation copy and reuse navigation", async () => {
    const workflow = { id: "workflow-reused", currentStage: "keyframe", characterSheets: [] } as unknown as WorkflowDetail;
    const selectedWorkflow = ref<WorkflowDetail | null>(null);
    const requestConfirm = vi.fn(async () => true);
    const onReused = vi.fn();
    const dependencies = {
      requireAuthentication: vi.fn(async () => true),
      deleteAllVersions: vi.fn(async () => workflow),
      deleteVersion: vi.fn(async () => workflow),
      fetchWorkflowDetail: vi.fn(async () => workflow),
      reuseAsset: vi.fn(async () => workflow),
      message: { error: vi.fn(), warning: vi.fn() },
    };
    const commands = useWorkflowVersionCommands({
      selectedWorkflowId: computed(() => "workflow-1"),
      selectedWorkflow,
      busyActionKey: ref(""),
      workflowCharacterSheets: computed(() => []),
      applyWorkflowDrafts: vi.fn(),
      reloadWorkflows: vi.fn(async () => undefined),
      requestConfirm,
      deleteVersionConfirmMessage: () => "级联删除提示",
      onReused,
    }, dependencies);

    await commands.handleDeleteStageVersion({ id: "version-1", stageType: "storyboard" } as StageVersion);
    await commands.handleReuseAsset("asset-1", "version-1");

    expect(requestConfirm).toHaveBeenCalledWith(expect.objectContaining({ message: "级联删除提示" }));
    expect(onReused).toHaveBeenCalledWith(workflow);
  });
});
