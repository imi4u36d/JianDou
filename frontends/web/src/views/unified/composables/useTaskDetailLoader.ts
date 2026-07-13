import { computed, ref, watch } from "vue";
import { fetchTask } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import { usePolling } from "@/composables/usePolling";
import { resolveTaskPreviewMedia } from "@/utils/task-preview";
import type { TaskDetail, TaskListItem } from "@/types";
import { isActiveTaskStatus } from "../features/task-detail-presenters";

interface TaskDetailLoaderDependencies {
  fetch?: typeof fetchTask;
  message?: Pick<typeof messageApi, "error">;
  pollIntervalMs?: number;
  completedPreviewPollLimit?: number;
}

interface TaskDetailLoaderOptions {
  selectedTaskId: () => string;
  selectedTaskSummary: () => TaskListItem | null;
  dependencies?: TaskDetailLoaderDependencies;
}

export function useTaskDetailLoader(options: TaskDetailLoaderOptions) {
  const dependencies = options.dependencies ?? {};
  const fetch = dependencies.fetch ?? fetchTask;
  const message = dependencies.message ?? messageApi;
  const previewPollLimit = dependencies.completedPreviewPollLimit ?? 8;
  const selectedTaskDetail = ref<TaskDetail | null>(null);
  const selectedTaskLoading = ref(false);
  const completedPreviewPollCount = ref(0);
  let detailRequestSerial = 0;

  const selectedTaskPreviewMedia = computed(() =>
    resolveTaskPreviewMedia(selectedTaskDetail.value ?? options.selectedTaskSummary()),
  );
  const selectedTaskAwaitingCompletedPreview = computed(() => {
    const status = selectedTaskDetail.value?.status ?? options.selectedTaskSummary()?.status;
    return status === "COMPLETED" && !selectedTaskPreviewMedia.value && completedPreviewPollCount.value < previewPollLimit;
  });

  async function loadSelectedTaskDetails(loadOptions: { silent?: boolean } = {}) {
    const taskId = options.selectedTaskId();
    const requestId = ++detailRequestSerial;
    if (!taskId) {
      selectedTaskDetail.value = null;
      selectedTaskLoading.value = false;
      return;
    }
    if (!loadOptions.silent) {
      if (selectedTaskDetail.value?.id !== taskId) selectedTaskDetail.value = null;
      selectedTaskLoading.value = true;
    }
    try {
      const detail = await fetch(taskId);
      if (requestId !== detailRequestSerial || options.selectedTaskId() !== taskId) return;
      selectedTaskDetail.value = detail;
      if (selectedTaskPreviewMedia.value) completedPreviewPollCount.value = 0;
      if (selectedTaskAwaitingCompletedPreview.value) {
        completedPreviewPollCount.value += 1;
        if (!detailPolling.active.value) void detailPolling.start(false);
      } else if (!isActiveTaskStatus(detail.status)) {
        detailPolling.stop();
      }
    } catch (error) {
      if (!loadOptions.silent && requestId === detailRequestSerial && options.selectedTaskId() === taskId) {
        message.error(error instanceof Error ? error.message : "任务详情加载失败");
      }
    } finally {
      if (!loadOptions.silent && requestId === detailRequestSerial && options.selectedTaskId() === taskId) {
        selectedTaskLoading.value = false;
      }
    }
  }

  const detailPolling = usePolling(async () => {
    const status = selectedTaskDetail.value?.status ?? options.selectedTaskSummary()?.status;
    if (!isActiveTaskStatus(status) && !selectedTaskAwaitingCompletedPreview.value) {
      detailPolling.stop();
      return;
    }
    await loadSelectedTaskDetails({ silent: true });
  }, dependencies.pollIntervalMs ?? 5000);

  watch(
    () => options.selectedTaskId(),
    () => {
      completedPreviewPollCount.value = 0;
    },
  );

  return {
    selectedTaskDetail,
    selectedTaskLoading,
    selectedTaskPreviewMedia,
    selectedTaskAwaitingCompletedPreview,
    loadSelectedTaskDetails,
    refreshSelectedTask: () => loadSelectedTaskDetails(),
    startDetailPolling: () => detailPolling.start(false),
    stopDetailPolling: () => detailPolling.stop(),
  };
}
