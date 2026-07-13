import { ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import { continueTask, deleteTask, pauseTask, retryTask, terminateTask } from "@/features/tasks";
import type { TaskListItem } from "@/types";

interface TaskDetailCommandApi {
  retry: typeof retryTask;
  pause: typeof pauseTask;
  continue: typeof continueTask;
  terminate: typeof terminateTask;
  delete: typeof deleteTask;
}

interface TaskDetailCommandDependencies {
  api?: TaskDetailCommandApi;
  authenticate?: typeof requireAuth;
  message?: Pick<typeof messageApi, "success" | "error">;
}

interface TaskDetailCommandOptions {
  selectedTaskId: () => string;
  reloadTasks: () => Promise<void>;
  reloadDetail: () => Promise<void>;
  requestConfirm: (options: { title: string; message: string; confirmText: string }) => Promise<boolean>;
  onDeleted?: (taskId: string) => void;
  dependencies?: TaskDetailCommandDependencies;
}

const defaultApi: TaskDetailCommandApi = {
  retry: retryTask,
  pause: pauseTask,
  continue: continueTask,
  terminate: terminateTask,
  delete: deleteTask,
};

export function useTaskDetailCommands(options: TaskDetailCommandOptions) {
  const dependencies = options.dependencies ?? {};
  const api = dependencies.api ?? defaultApi;
  const authenticate = dependencies.authenticate ?? requireAuth;
  const message = dependencies.message ?? messageApi;
  const managingTaskId = ref("");

  async function authenticateTask(messageText: string) {
    const authenticated = await authenticate({ title: "登录后操作任务", message: messageText });
    if (!authenticated) message.error("登录后可继续操作任务");
    return authenticated;
  }

  async function runCommand(task: TaskListItem, command: () => Promise<unknown>, failureMessage: string) {
    managingTaskId.value = task.id;
    try {
      await command();
      await Promise.all([options.reloadTasks(), options.reloadDetail()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : failureMessage);
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handleRetry(task: TaskListItem) {
    if (managingTaskId.value) return;
    if (!(await authenticateTask("任务重试会重新加入队列，请先登录或使用邀请码注册。"))) return;
    managingTaskId.value = task.id;
    try {
      await api.retry(task.id);
      await Promise.all([
        options.reloadTasks(),
        task.id === options.selectedTaskId() ? options.reloadDetail() : Promise.resolve(),
      ]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "重试任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handlePause(task: TaskListItem) {
    if (managingTaskId.value) return;
    if (!(await authenticateTask("任务操作会修改你的任务状态，请先登录或使用邀请码注册。"))) return;
    await runCommand(task, () => api.pause(task.id), "暂停任务失败");
  }

  async function handleContinueTask(task: TaskListItem) {
    if (managingTaskId.value) return;
    if (!(await authenticateTask("任务操作会修改你的任务状态，请先登录或使用邀请码注册。"))) return;
    await runCommand(task, () => api.continue(task.id), "继续任务失败");
  }

  async function handleTerminate(task: TaskListItem) {
    if (managingTaskId.value) return;
    if (!(await authenticateTask("任务操作会修改你的任务状态，请先登录或使用邀请码注册。"))) return;
    const confirmed = await options.requestConfirm({
      title: "终止任务",
      message: `任务会变为失败状态，可再删除或重试：${task.title || "未命名任务"}`,
      confirmText: "终止",
    });
    if (!confirmed) return;
    await runCommand(task, () => api.terminate(task.id), "终止任务失败");
  }

  async function handleDelete(task: TaskListItem) {
    if (managingTaskId.value) return;
    if (!(await authenticateTask("任务删除后无法恢复，请先登录或使用邀请码注册。"))) return;
    const confirmed = await options.requestConfirm({
      title: "删除任务",
      message: `删除后无法恢复：${task.title || "未命名任务"}`,
      confirmText: "删除",
    });
    if (!confirmed) return;
    managingTaskId.value = task.id;
    try {
      await api.delete(task.id);
      await options.reloadTasks();
      message.success("任务已删除");
      options.onDeleted?.(task.id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  return {
    managingTaskId,
    handleRetry,
    handlePause,
    handleContinueTask,
    handleTerminate,
    handleDelete,
  };
}
