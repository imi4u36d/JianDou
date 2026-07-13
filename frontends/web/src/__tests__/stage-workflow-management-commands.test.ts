import { computed, reactive, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useStageWorkflowManagementCommands } from "@/composables/workflow/useStageWorkflowManagementCommands";
import type { WorkflowDetail, WorkflowSummary } from "@/types";

function harness() {
  const workflow = { id: "workflow-1", currentStage: "storyboard" } as WorkflowDetail;
  const selectedWorkflow = ref<WorkflowDetail | null>(workflow);
  const busyActionKey = ref("");
  const workflowSettingsOpen = ref(true);
  const applyWorkflowDrafts = vi.fn();
  const loadWorkflows = vi.fn(async () => undefined);
  const runAndRefresh = vi.fn(async (_key: string, runner: () => Promise<WorkflowDetail>) => {
    selectedWorkflow.value = await runner();
    return true;
  });
  const dependencies = {
    requireAuthentication: vi.fn(async () => true),
    updateSettings: vi.fn(async () => workflow),
    generateCharacter: vi.fn(async (_workflowId: string, _characterIndex: number) => workflow),
    selectCharacterAsset: vi.fn(async () => workflow),
    removeWorkflow: vi.fn(async () => ({ workflowId: "workflow-1", deleted: true })),
    message: { error: vi.fn(), warning: vi.fn() },
  };
  const navigateAfterSelectedDelete = vi.fn(async () => undefined);
  const commands = useStageWorkflowManagementCommands({
    selectedWorkflowId: computed(() => "workflow-1"),
    selectedWorkflow,
    busyActionKey,
    workflowSettingsOpen,
    workflowSettingsValidationMessage: computed(() => ""),
    workflowSettingsDraft: reactive({
      aspectRatio: "16:9",
      textAnalysisModel: "text-model",
      imageModel: "image-model",
      videoModel: "video-model",
      videoSize: "1920*1080",
      keyframeSeed: "11",
      videoSeed: "22",
      durationMode: "manual" as const,
      minDurationSeconds: "5",
      maxDurationSeconds: "8",
    }),
    missingCharacterSheets: computed(() => [
      { characterIndex: 1 },
      { syntheticClipIndex: 1002 },
    ]),
    applyWorkflowDrafts,
    loadWorkflows,
    reloadCurrentWorkflow: vi.fn(async () => undefined),
    runAndRefresh,
    requestConfirm: vi.fn(async () => true),
    navigateAfterSelectedDelete,
  }, dependencies);
  return {
    workflow,
    selectedWorkflow,
    busyActionKey,
    workflowSettingsOpen,
    applyWorkflowDrafts,
    loadWorkflows,
    runAndRefresh,
    dependencies,
    navigateAfterSelectedDelete,
    commands,
  };
}

describe("stage workflow management commands", () => {
  it("builds settings payload and closes the settings panel after success", async () => {
    const context = harness();

    await context.commands.handleUpdateWorkflowSettings();

    expect(context.dependencies.updateSettings).toHaveBeenCalledWith("workflow-1", expect.objectContaining({
      keyframeSeed: 11,
      videoSeed: 22,
      minDurationSeconds: 5,
      maxDurationSeconds: 8,
    }));
    expect(context.workflowSettingsOpen.value).toBe(false);
  });

  it("generates every missing character sheet sequentially", async () => {
    const context = harness();

    await context.commands.handleGenerateMissingCharacterSheets();

    expect(context.dependencies.generateCharacter.mock.calls.map((call) => call[1])).toEqual([1, 2]);
    expect(context.applyWorkflowDrafts).toHaveBeenCalledTimes(2);
    expect(context.loadWorkflows).toHaveBeenCalledOnce();
    expect(context.busyActionKey.value).toBe("");
  });

  it("clears selection and navigates after deleting the open workflow", async () => {
    const context = harness();

    await context.commands.handleDeleteWorkflow({ id: "workflow-1", title: "Rain" } as WorkflowSummary);

    expect(context.dependencies.requireAuthentication).toHaveBeenCalledOnce();
    expect(context.dependencies.removeWorkflow).toHaveBeenCalledWith("workflow-1");
    expect(context.selectedWorkflow.value).toBeNull();
    expect(context.navigateAfterSelectedDelete).toHaveBeenCalledOnce();
  });
});
