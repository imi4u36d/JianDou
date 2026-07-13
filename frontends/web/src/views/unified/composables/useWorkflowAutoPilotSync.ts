import { computed, ref, watch, type Ref } from "vue";
import type { WorkflowDetail } from "@/types";
import type { useAutoPilot } from "@/composables/workflow/useAutoPilot";

type AutoPilotState = ReturnType<typeof useAutoPilot>;

export interface WorkflowAutoPilotSyncOptions {
  workflowId: () => string;
  workflow: Ref<WorkflowDetail | null>;
  autoPilot: AutoPilotState;
  pollWorkflow: () => Promise<void>;
}

const STATE_LABELS: Record<string, string> = {
  queued: "排队中",
  running: "自动执行",
  paused: "已暂停",
  failed: "执行失败",
  completed: "已完成",
  idle: "已停止",
};

const STATE_MESSAGES: Record<string, string> = {
  queued: "已加入队列，等待执行",
  running: "",
  paused: "已暂停",
  failed: "执行失败",
  completed: "已完成",
  idle: "已停止",
};

export function useWorkflowAutoPilotSync(options: WorkflowAutoPilotSyncOptions) {
  const initialized = ref(false);
  let lastTask = "";

  const executionMode = computed(() => options.workflow.value?.executionMode ?? options.workflow.value?.durationMode ?? "manual");
  const recentLog = computed(() => options.autoPilot.statusLog.value.slice(-1));

  function syncBackendState(state?: string | null) {
    const workflow = options.workflow.value;
    options.autoPilot.autoPilotState.value = state || "idle";
    options.autoPilot.nextStage.value = workflow?.autoPilotNextStage ?? workflow?.currentStage ?? "";
    options.autoPilot.currentTask.value = workflow?.autoPilotCurrentTask ?? "";
    options.autoPilot.errorMessage.value = workflow?.autoPilotErrorMessage ?? "";
  }

  function appendStateLog(state?: string | null) {
    if (!state) return;
    const message = STATE_MESSAGES[state] ?? state;
    if (message) options.autoPilot.pushStatusLog(STATE_LABELS[state] ?? state, message, state);
  }

  watch(options.workflowId, () => {
    initialized.value = false;
    lastTask = "";
    options.autoPilot.autoPilotState.value = "idle";
    options.autoPilot.nextStage.value = "";
    options.autoPilot.currentTask.value = "";
    options.autoPilot.errorMessage.value = "";
    options.autoPilot.stopPolling();
  });

  watch(
    () => options.workflow.value?.autoPilotState,
    (state, previousState) => {
      if (!initialized.value) {
        initialized.value = true;
        syncBackendState(state);
        appendStateLog(state);
        return;
      }
      if (state !== previousState) {
        syncBackendState(state);
        appendStateLog(state);
      }
    },
  );

  watch(
    () => options.workflow.value?.autoPilotCurrentTask,
    (task) => {
      const currentTask = task ?? "";
      options.autoPilot.currentTask.value = currentTask;
      if (currentTask && currentTask !== lastTask && options.autoPilot.isRunning.value) {
        options.autoPilot.pushStatusLog("自动执行", currentTask, "running");
      }
      lastTask = currentTask;
    },
  );

  watch(
    () => options.autoPilot.isActive.value,
    (active) => {
      if (active) options.autoPilot.startPolling(options.pollWorkflow);
      else options.autoPilot.stopPolling();
    },
  );

  watch(
    () => options.autoPilot.autoPilotState.value,
    (state) => {
      if (["idle", "failed", "completed"].includes(state)) options.autoPilot.stopPolling();
    },
  );

  return { executionMode, recentLog };
}
