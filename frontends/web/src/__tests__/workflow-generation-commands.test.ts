import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import {
  useWorkflowGenerationCommands,
  type WorkflowGenerationCommandDependencies,
} from "@/views/unified/composables/useWorkflowGenerationCommands";
import type { UpdateWorkflowSettingsRequest, WorkflowDetail } from "@/types";

function harness(validationMessage = "") {
  const workflow = { id: "workflow-1" } as unknown as WorkflowDetail;
  const selectedWorkflow = ref<WorkflowDetail | null>(workflow);
  const busyActionKey = ref("");
  const reloadWorkflows = vi.fn(async () => undefined);
  const applyWorkflowDrafts = vi.fn();
  const requireAuthentication = vi.fn(async () => true);
  const generateStoryboard = vi.fn(async () => workflow);
  const dependencies: Partial<WorkflowGenerationCommandDependencies> = {
    requireAuthentication,
    generateStoryboard,
    message: { error: vi.fn(), warning: vi.fn() },
  };
  const commands = useWorkflowGenerationCommands({
    selectedWorkflowId: computed(() => "workflow-1"),
    selectedWorkflow,
    busyActionKey,
    workflowSettingsValidationMessage: computed(() => validationMessage),
    workflowSettingsOpen: ref(true),
    storyboardAdjustmentDrafts: {},
    missingCharacterSheets: computed(() => []),
    applyWorkflowDrafts,
    reloadWorkflows,
    buildWorkflowSettingsPayload: () => ({}) as UpdateWorkflowSettingsRequest,
    closeCharacterAssetPicker: vi.fn(),
    reloadCurrentWorkflow: vi.fn(async () => undefined),
  }, dependencies);
  return { workflow, selectedWorkflow, busyActionKey, reloadWorkflows, applyWorkflowDrafts, requireAuthentication, generateStoryboard, commands };
}

describe("workflow generation commands", () => {
  it("runs storyboard generation through authentication and refreshes state", async () => {
    const context = harness();

    await context.commands.handleGenerateStoryboard();

    expect(context.requireAuthentication).toHaveBeenCalledOnce();
    expect(context.generateStoryboard).toHaveBeenCalledWith("workflow-1");
    expect(context.selectedWorkflow.value).toEqual(context.workflow);
    expect(context.applyWorkflowDrafts).toHaveBeenCalledWith(context.workflow);
    expect(context.reloadWorkflows).toHaveBeenCalledOnce();
    expect(context.busyActionKey.value).toBe("");
  });

  it("does not authenticate or update settings when validation fails", async () => {
    const context = harness("请选择视频模型");

    await context.commands.handleUpdateWorkflowSettings();

    expect(context.requireAuthentication).not.toHaveBeenCalled();
    expect(context.reloadWorkflows).not.toHaveBeenCalled();
  });
});
