import { ref } from "vue";

export type SubmissionStartResult = "started" | "busy" | "duplicate";

export interface HomeSubmissionGuardOptions {
  duplicateWindowMs?: number;
  toastDurationMs?: number;
  now?: () => number;
}

export function useHomeSubmissionGuard(options: HomeSubmissionGuardOptions = {}) {
  const duplicateWindowMs = options.duplicateWindowMs ?? 3000;
  const toastDurationMs = options.toastDurationMs ?? 5000;
  const now = options.now ?? Date.now;
  const submitting = ref(false);
  const createdTaskId = ref("");
  const taskToastTaskId = ref("");
  let activeFingerprint = "";
  let lastSuccessfulFingerprint = "";
  let lastSuccessfulAt = 0;
  let taskToastTimer: ReturnType<typeof setTimeout> | null = null;

  function begin(fingerprint: string): SubmissionStartResult {
    if (submitting.value) {
      return "busy";
    }
    const timestamp = now();
    if (
      activeFingerprint === fingerprint ||
      (lastSuccessfulFingerprint === fingerprint && timestamp - lastSuccessfulAt < duplicateWindowMs)
    ) {
      return "duplicate";
    }
    activeFingerprint = fingerprint;
    submitting.value = true;
    return "started";
  }

  function finish(fingerprint: string, successful: boolean) {
    if (successful) {
      lastSuccessfulFingerprint = fingerprint;
      lastSuccessfulAt = now();
    }
    activeFingerprint = "";
    submitting.value = false;
  }

  function showTaskToast(taskId: string) {
    taskToastTaskId.value = taskId;
    if (taskToastTimer !== null) {
      clearTimeout(taskToastTimer);
    }
    taskToastTimer = setTimeout(() => {
      taskToastTaskId.value = "";
      taskToastTimer = null;
    }, toastDurationMs);
  }

  function dismissTaskToast() {
    taskToastTaskId.value = "";
    if (taskToastTimer !== null) {
      clearTimeout(taskToastTimer);
      taskToastTimer = null;
    }
  }

  return {
    submitting,
    createdTaskId,
    taskToastTaskId,
    begin,
    finish,
    showTaskToast,
    dismissTaskToast,
  };
}
