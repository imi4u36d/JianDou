import { ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchTaskPage } from "@/features/home";
import { activeTaskTimestamp } from "@/features/home/active-task-presenters";
import type { TaskListItem, TaskStatus } from "@/types";

const ACTIVE_TASK_STATUSES = new Set<TaskStatus>(["PENDING", "ANALYZING", "PLANNING", "RENDERING"]);

export function useActiveTasks() {
  const authState = useAuthSessionState();
  const activeTasks = ref<TaskListItem[]>([]);

  async function loadActiveTasks() {
    if (!authState.isAuthenticated.value) {
      activeTasks.value = [];
      return;
    }
    try {
      const page = await fetchTaskPage({
        sort: "updated_desc",
        excludeTaskType: "video_generation",
        offset: 0,
        limit: 30,
      });
      activeTasks.value = page.items
        .filter((task) => ACTIVE_TASK_STATUSES.has(task.status))
        .sort(
          (left, right) =>
            activeTaskTimestamp(right.updatedAt || right.createdAt) -
            activeTaskTimestamp(left.updatedAt || left.createdAt),
        )
        .slice(0, 12);
    } catch {
      activeTasks.value = [];
    }
  }

  const polling = usePolling(loadActiveTasks, 5000);
  void polling.start();

  return {
    activeTasks,
    loadActiveTasks,
  };
}
