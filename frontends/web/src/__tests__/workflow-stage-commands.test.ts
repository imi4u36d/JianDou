import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useWorkflowStageCommands, type WorkflowStageCommandApi } from "@/composables/workflow/useWorkflowStageCommands";
import type { WorkflowDetail } from "@/types";

function commandApi(result: WorkflowDetail) {
  return {
    adjustStoryboard: vi.fn(async () => result),
    finalizeWorkflow: vi.fn(async () => result),
    generateCharacterSheet: vi.fn(async () => result),
    generateKeyframe: vi.fn(async () => result),
    generateKeyframeFrame: vi.fn(async () => result),
    generateStoryboard: vi.fn(async () => result),
    generateVideo: vi.fn(async () => result),
    selectKeyframe: vi.fn(async () => result),
    selectKeyframeFrame: vi.fn(async () => result),
    selectStoryboard: vi.fn(async () => result),
    selectVideo: vi.fn(async () => result),
  } as unknown as WorkflowStageCommandApi;
}

describe("workflow stage commands", () => {
  it("runs API commands through the shared refresh boundary", async () => {
    const result = { id: "wf-1" } as WorkflowDetail;
    const api = commandApi(result);
    const runAndRefresh = vi.fn(async (_actionKey: string, runner: () => Promise<WorkflowDetail>) => {
      await runner();
      return true;
    });
    const setStoryboardAdjustment = vi.fn();
    const commands = useWorkflowStageCommands(
      {
        selectedWorkflowId: ref("wf-1"),
        runAndRefresh,
        storyboardAdjustment: () => "  加强雨夜氛围  ",
        setStoryboardAdjustment,
      },
      api,
    );

    await commands.handleGenerateStoryboard();
    await commands.handleAdjustStoryboard("story-2");
    await commands.handleGenerateCharacterSheet({ characterIndex: 3, syntheticClipIndex: 1003 });

    expect(runAndRefresh.mock.calls.map(([actionKey]) => actionKey)).toEqual(["storyboard", "storyboard-adjust-story-2", "character-sheet-1003"]);
    expect(api.generateStoryboard).toHaveBeenCalledWith("wf-1");
    expect(api.adjustStoryboard).toHaveBeenCalledWith("wf-1", "story-2", "加强雨夜氛围");
    expect(api.generateCharacterSheet).toHaveBeenCalledWith("wf-1", 3);
    expect(setStoryboardAdjustment).toHaveBeenCalledWith("story-2", "");
  });

  it("does not invoke APIs without a selected workflow", async () => {
    const result = { id: "wf-1" } as WorkflowDetail;
    const api = commandApi(result);
    const runAndRefresh = vi.fn();
    const commands = useWorkflowStageCommands(
      {
        selectedWorkflowId: ref(""),
        runAndRefresh,
        storyboardAdjustment: () => "",
        setStoryboardAdjustment: vi.fn(),
      },
      api,
    );

    await commands.handleGenerateVideo(1);

    expect(runAndRefresh).not.toHaveBeenCalled();
    expect(api.generateVideo).not.toHaveBeenCalled();
  });
});
