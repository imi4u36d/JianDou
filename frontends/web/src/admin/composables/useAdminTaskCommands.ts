import { ref, type Ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  bulkDeleteAdminTasks,
  bulkTerminateAdminTasks,
  deleteAdminTask,
  terminateAdminTask,
} from "@/admin/features/tasks/services/taskService";
import type { AdminTaskBatchResult, AdminTaskListItem } from "@/types";

interface AdminTaskCommandApi {
  terminateOne(taskId: string): Promise<unknown>;
  terminateMany(taskIds: string[]): Promise<AdminTaskBatchResult>;
  deleteOne(taskId: string): Promise<unknown>;
  deleteMany(taskIds: string[]): Promise<AdminTaskBatchResult>;
}

interface AdminTaskMessagePort {
  success(message: string): void;
  warning(message: string): void;
  error(message: string): void;
}

type ConfirmCommand = (
  message: string,
  title: string,
  options: {
    confirmButtonText: string;
    cancelButtonText: string;
    type: "warning";
  },
) => Promise<unknown>;

interface AdminTaskCommandOptions {
  selectedTasks: Ref<AdminTaskListItem[]>;
  selectedTerminableIds: Readonly<Ref<string[]>>;
  reloadTasks: () => Promise<void>;
}

interface AdminTaskCommandDependencies {
  api?: AdminTaskCommandApi;
  confirm?: ConfirmCommand;
  message?: AdminTaskMessagePort;
}

const defaultApi: AdminTaskCommandApi = {
  terminateOne: terminateAdminTask,
  terminateMany: bulkTerminateAdminTasks,
  deleteOne: deleteAdminTask,
  deleteMany: bulkDeleteAdminTasks,
};

function isCancelled(error: unknown) {
  return error === "cancel" || error === "close";
}

export function useAdminTaskCommands(
  options: AdminTaskCommandOptions,
  dependencies: AdminTaskCommandDependencies = {},
) {
  const api = dependencies.api ?? defaultApi;
  const confirm = dependencies.confirm ?? ElMessageBox.confirm;
  const message = dependencies.message ?? ElMessage;
  const actionLoading = ref(false);
  const successMessage = ref("");

  async function terminateSingle(task: AdminTaskListItem) {
    try {
      await confirm(
        `确认终止任务"${task.title || task.id}"吗？终止后任务会进入失败状态。`,
        "终止任务",
        { confirmButtonText: "终止", cancelButtonText: "取消", type: "warning" },
      );
      actionLoading.value = true;
      successMessage.value = "";
      await api.terminateOne(task.id);
      options.selectedTasks.value = options.selectedTasks.value.filter((item) => item.id !== task.id);
      await options.reloadTasks();
      successMessage.value = "任务已终止。";
      message.success(successMessage.value);
    } catch (error) {
      if (!isCancelled(error)) message.error(error instanceof Error ? error.message : "终止任务失败");
    } finally {
      actionLoading.value = false;
    }
  }

  async function terminateSelected() {
    const taskIds = options.selectedTerminableIds.value;
    if (taskIds.length === 0) {
      message.warning("请选择排队或执行中的任务");
      return;
    }
    try {
      await confirm(
        `确认终止选中的 ${taskIds.length} 个任务吗？已完成、失败或暂停任务不会被提交。`,
        "批量终止任务",
        { confirmButtonText: "批量终止", cancelButtonText: "取消", type: "warning" },
      );
      actionLoading.value = true;
      successMessage.value = "";
      const result = await api.terminateMany(taskIds);
      const failedIds = new Set(result.failed.map((item) => item.taskId));
      options.selectedTasks.value = result.failed.length
        ? options.selectedTasks.value.filter((task) => failedIds.has(task.id))
        : [];
      await options.reloadTasks();
      successMessage.value = result.failed.length
        ? `已终止 ${result.succeededTaskIds.length} 个任务，${result.failed.length} 个未成功。`
        : `已终止 ${result.succeededTaskIds.length} 个任务。`;
      message.success(successMessage.value);
    } catch (error) {
      if (!isCancelled(error)) message.error(error instanceof Error ? error.message : "批量终止任务失败");
    } finally {
      actionLoading.value = false;
    }
  }

  async function deleteSingle(task: AdminTaskListItem) {
    try {
      await confirm(
        `确认删除任务"${task.title || task.id}"吗？删除后不可恢复。`,
        "删除任务",
        { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
      );
      actionLoading.value = true;
      successMessage.value = "";
      await api.deleteOne(task.id);
      options.selectedTasks.value = options.selectedTasks.value.filter((item) => item.id !== task.id);
      await options.reloadTasks();
      successMessage.value = "任务已删除。";
      message.success(successMessage.value);
    } catch (error) {
      if (!isCancelled(error)) message.error(error instanceof Error ? error.message : "删除任务失败");
    } finally {
      actionLoading.value = false;
    }
  }

  async function deleteSelected() {
    const taskIds = options.selectedTasks.value.map((task) => task.id);
    if (taskIds.length === 0) {
      message.warning("请选择要删除的任务");
      return;
    }
    try {
      await confirm(
        `确认删除选中的 ${taskIds.length} 个任务吗？删除后不可恢复。`,
        "批量删除任务",
        { confirmButtonText: "批量删除", cancelButtonText: "取消", type: "warning" },
      );
      actionLoading.value = true;
      successMessage.value = "";
      const result = await api.deleteMany(taskIds);
      const failedIds = new Set(result.failed.map((item) => item.taskId));
      options.selectedTasks.value = result.failed.length
        ? options.selectedTasks.value.filter((task) => failedIds.has(task.id))
        : [];
      await options.reloadTasks();
      successMessage.value = result.failed.length
        ? `已删除 ${result.succeededTaskIds.length} 个任务，${result.failed.length} 个未成功。`
        : `已删除 ${result.succeededTaskIds.length} 个任务。`;
      message.success(successMessage.value);
    } catch (error) {
      if (!isCancelled(error)) message.error(error instanceof Error ? error.message : "批量删除任务失败");
    } finally {
      actionLoading.value = false;
    }
  }

  return {
    actionLoading,
    successMessage,
    terminateSingle,
    terminateSelected,
    deleteSingle,
    deleteSelected,
  };
}
