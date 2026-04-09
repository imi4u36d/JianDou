import { onUnmounted, ref } from "vue";
import { fetchTask, fetchTaskTrace } from "@/api/tasks";
import type { TaskDetail, TaskTraceEvent, TaskStatus } from "@/types";
import type { TaskProgressState } from "./types";

function nowLabel() {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function buildInitialState(): TaskProgressState {
  return {
    status: "idle",
    progress: 0,
    stage: "等待任务",
    message: "提交参数后将开始生成视频。",
    updatedAt: nowLabel(),
  };
}

function normalizeProgress(value: number | null | undefined, fallback: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function mapTaskStatus(status: TaskStatus, rawProgress: number | null | undefined) {
  const progress = normalizeProgress(rawProgress, 0);
  switch (status) {
    case "PENDING":
      return { status: "running" as const, stage: "任务排队中", progress: Math.max(progress, 12) };
    case "PAUSED":
      return { status: "paused" as const, stage: "任务已暂停", progress: Math.max(progress, 1) };
    case "ANALYZING":
      return { status: "running" as const, stage: "分析输入内容", progress: Math.max(progress, 34) };
    case "PLANNING":
      return { status: "running" as const, stage: "规划生成方案", progress: Math.max(progress, 58) };
    case "RENDERING":
      return { status: "running" as const, stage: "渲染视频中", progress: Math.max(progress, 82) };
    case "COMPLETED":
      return { status: "completed" as const, stage: "任务完成", progress: 100 };
    case "FAILED":
      return { status: "failed" as const, stage: "任务失败", progress: Math.max(progress, 1) };
    default:
      return { status: "running" as const, stage: "执行中", progress: Math.max(progress, 18) };
  }
}

export function useTaskProgress() {
  const state = ref<TaskProgressState>(buildInitialState());
  const traceEvents = ref<TaskTraceEvent[]>([]);
  const taskId = ref("");
  const taskDetail = ref<TaskDetail | null>(null);

  let optimisticTimer: number | null = null;
  let pollTimer: number | null = null;

  function clearOptimisticTimer() {
    if (optimisticTimer !== null) {
      window.clearInterval(optimisticTimer);
      optimisticTimer = null;
    }
  }

  function clearPollTimer() {
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function patchState(next: Partial<TaskProgressState>) {
    state.value = {
      ...state.value,
      ...next,
      updatedAt: nowLabel(),
    };
  }

  function reset() {
    clearOptimisticTimer();
    clearPollTimer();
    taskId.value = "";
    taskDetail.value = null;
    traceEvents.value = [];
    state.value = buildInitialState();
  }

  function startOptimisticProgress() {
    clearOptimisticTimer();
    optimisticTimer = window.setInterval(() => {
      if (taskId.value || state.value.status !== "running") {
        return;
      }
      const next = Math.min(state.value.progress + 3, 72);
      let nextStage = "排队等待";
      if (next >= 25 && next < 50) {
        nextStage = "任务已创建";
      } else if (next >= 50) {
        nextStage = "远端生成处理中";
      }
      patchState({ progress: next, stage: nextStage });
    }, 600);
  }

  async function syncTaskTrace(runTaskId: string) {
    try {
      const [task, trace] = await Promise.all([
        fetchTask(runTaskId),
        fetchTaskTrace(runTaskId, 30).catch(() => []),
      ]);
      const mapped = mapTaskStatus(task.status, task.progress);
      const latestTrace = trace.length ? trace[trace.length - 1] : null;
      taskDetail.value = task;
      traceEvents.value = trace;
      patchState({
        status: mapped.status,
        progress: mapped.progress,
        stage: mapped.stage,
        message: latestTrace?.message || mapped.stage,
      });
      if (mapped.status !== "running") {
        clearPollTimer();
      }
    } catch (error) {
      patchState({
        message: error instanceof Error ? error.message : "任务状态同步失败",
      });
    }
  }

  function start(initial?: Partial<TaskProgressState>) {
    reset();
    patchState({
      status: "running",
      progress: 8,
      stage: "提交生成请求",
      message: "正在创建视频生成任务...",
      ...(initial || {}),
    });
    startOptimisticProgress();
  }

  function attachTask(runTaskId: string) {
    taskId.value = runTaskId;
    clearOptimisticTimer();
    patchState({
      status: "running",
      progress: Math.max(state.value.progress, 12),
      stage: "任务执行中",
      message: `任务 ID: ${runTaskId}`,
    });
    void syncTaskTrace(runTaskId);
    clearPollTimer();
    pollTimer = window.setInterval(() => {
      void syncTaskTrace(runTaskId);
    }, 2000);
  }

  function complete(message = "视频已生成完成。") {
    clearOptimisticTimer();
    clearPollTimer();
    patchState({
      status: "completed",
      progress: 100,
      stage: "任务完成",
      message,
    });
  }

  function fail(message: string) {
    clearOptimisticTimer();
    clearPollTimer();
    patchState({
      status: "failed",
      progress: Math.max(1, state.value.progress),
      stage: "任务失败",
      message,
    });
  }

  onUnmounted(() => {
    clearOptimisticTimer();
    clearPollTimer();
  });

  return {
    state,
    taskId,
    taskDetail,
    traceEvents,
    reset,
    start,
    attachTask,
    complete,
    fail,
  };
}
