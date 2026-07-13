import { computed, effectScope, nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import type { useAutoPilot } from "@/composables/workflow/useAutoPilot";
import { useWorkflowAutoPilotSync } from "@/views/unified/composables/useWorkflowAutoPilotSync";
import type { WorkflowDetail } from "@/types";

function autoPilotHarness() {
  const autoPilotState = ref("idle");
  const statusLog = ref<Array<{ stage: string; message: string; stateKey: string }>>([]);
  const pushStatusLog = vi.fn((stage: string, message: string, stateKey: string) => {
    statusLog.value.push({ stage, message, stateKey });
  });
  return {
    autoPilotState,
    nextStage: ref(""),
    currentTask: ref(""),
    errorMessage: ref(""),
    statusLog,
    isRunning: computed(() => autoPilotState.value === "running"),
    isActive: computed(() => ["running", "queued"].includes(autoPilotState.value)),
    pushStatusLog,
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
  } as unknown as ReturnType<typeof useAutoPilot>;
}

describe("workflow auto-pilot synchronization", () => {
  it("synchronizes backend state, logs new tasks, and controls polling", async () => {
    const workflowId = ref("workflow-1");
    const workflow = ref<WorkflowDetail | null>(null);
    const autoPilot = autoPilotHarness();
    const pollWorkflow = vi.fn(async () => undefined);
    const scope = effectScope();

    const result = scope.run(() => useWorkflowAutoPilotSync({
      workflowId: () => workflowId.value,
      workflow,
      autoPilot,
      pollWorkflow,
    }));

    workflow.value = {
      autoPilotState: "queued",
      autoPilotNextStage: "keyframe",
      autoPilotCurrentTask: "等待关键帧",
      executionMode: "auto",
    } as WorkflowDetail;
    await nextTick();

    expect(result?.executionMode.value).toBe("auto");
    expect(autoPilot.autoPilotState.value).toBe("queued");
    expect(autoPilot.nextStage.value).toBe("keyframe");
    expect(autoPilot.pushStatusLog).toHaveBeenCalledWith("排队中", "已加入队列，等待执行", "queued");
    expect(autoPilot.startPolling).toHaveBeenCalledWith(pollWorkflow);

    workflow.value.autoPilotState = "running";
    workflow.value.autoPilotCurrentTask = "生成关键帧 1";
    workflow.value = { ...workflow.value };
    await nextTick();

    expect(autoPilot.pushStatusLog).toHaveBeenCalledWith("自动执行", "生成关键帧 1", "running");

    workflow.value.autoPilotState = "completed";
    workflow.value = { ...workflow.value };
    await nextTick();
    expect(autoPilot.stopPolling).toHaveBeenCalled();

    workflowId.value = "workflow-2";
    await nextTick();
    expect(autoPilot.autoPilotState.value).toBe("idle");
    expect(autoPilot.currentTask.value).toBe("");
    scope.stop();
  });
});
