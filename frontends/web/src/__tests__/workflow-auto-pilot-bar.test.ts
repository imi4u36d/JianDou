import { computed, createApp, nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useAutoPilot } from "@/composables/workflow/useAutoPilot";
import WorkflowAutoPilotBar from "@/views/unified/components/WorkflowAutoPilotBar.vue";

describe("workflow auto pilot bar", () => {
  it("renders lifecycle states and routes queued cancellation to the controller", async () => {
    const state = ref("idle");
    const terminateAutoPilot = vi.fn();
    const autoPilot = {
      autoPilotState: state,
      nextStage: ref(""),
      currentTask: ref(""),
      errorMessage: ref(""),
      busy: ref(false),
      statusLog: ref([]),
      isRunning: computed(() => state.value === "running"),
      isPaused: computed(() => state.value === "paused"),
      isFailed: computed(() => state.value === "failed"),
      isQueued: computed(() => state.value === "queued"),
      isActive: computed(() => state.value === "running" || state.value === "queued"),
      startAutoPilot: vi.fn(),
      pauseAutoPilot: vi.fn(),
      resumeAutoPilot: vi.fn(),
      terminateAutoPilot,
      startPolling: vi.fn(),
      stopPolling: vi.fn(),
      pushStatusLog: vi.fn(),
    } as unknown as ReturnType<typeof useAutoPilot>;
    const host = document.createElement("div");
    const app = createApp(WorkflowAutoPilotBar, {
      autoPilot,
      executionMode: "auto",
      queuePosition: 3,
      recentLog: [],
    });
    app.mount(host);

    expect(host.textContent).toContain("自动执行就绪");
    state.value = "queued";
    await nextTick();
    expect(host.textContent).toContain("排队中");
    expect(host.textContent).toContain("前面还有 2 个任务");
    const cancel = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "取消");
    cancel?.click();
    expect(terminateAutoPilot).toHaveBeenCalledOnce();

    app.unmount();
  });
});
