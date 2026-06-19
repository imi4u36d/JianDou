import { ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchTasks } from "@/features/home";
import { formatTaskStatus } from "@/utils/task";
import type { TaskListItem, TaskStatus } from "@/types";

const ACTIVE_TASK_STATUSES = new Set<TaskStatus>(["PENDING", "ANALYZING", "PLANNING", "RENDERING"]);

function taskTimestamp(value?: string | null) {
  const timestamp = value ? new Date(value).getTime() : Number.NaN;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function activeTaskProgress(task: TaskListItem) {
  return Math.max(0, Math.min(100, Math.round(task.progress ?? 0)));
}

function formatActiveTaskTime(value?: string | null) {
  if (!value) {
    return "暂无时间";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function activeTaskStageLabel(task: TaskListItem) {
  if (task.currentStage?.trim()) {
    return task.currentStage.trim();
  }
  if (task.status === "PENDING") {
    return typeof task.queuePosition === "number" && task.queuePosition > 0 ? `队列第 ${task.queuePosition} 位` : "等待开始";
  }
  return formatTaskStatus(task.status);
}

export function useActiveTasks() {
  const authState = useAuthSessionState();
  const activeTasks = ref<TaskListItem[]>([]);

  async function loadActiveTasks() {
    if (!authState.isAuthenticated.value) {
      activeTasks.value = [];
      return;
    }
    try {
      const tasks = await fetchTasks({ sort: "updated_desc" });
      activeTasks.value = tasks
        .filter((task) => ACTIVE_TASK_STATUSES.has(task.status))
        .sort((left, right) => taskTimestamp(right.updatedAt || right.createdAt) - taskTimestamp(left.updatedAt || left.createdAt))
        .slice(0, 12);
    } catch {
      activeTasks.value = [];
    }
  }

  const polling = usePolling(loadActiveTasks, 5000);
  void polling.start();

  return {
    activeTasks,
    taskTimestamp,
    activeTaskProgress,
    formatActiveTaskTime,
    activeTaskStageLabel,
    loadActiveTasks,
  };
}
