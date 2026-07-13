import { computed, reactive, ref, type Ref } from "vue";
import { createPublicShare, deletePublicShare } from "@/api/public-shares";
import { messageApi } from "@/composables/useMessage";
import type { TaskDetail, TaskListItem } from "@/types";

interface TaskResultSharingOptions {
  selectedTaskId: () => string;
  selectedTask: Ref<TaskDetail | TaskListItem | null>;
  selectedTaskActionTask: Ref<TaskListItem | null>;
  materialAssetId: Ref<string>;
}

export function useTaskResultSharing(options: TaskResultSharingOptions) {
  const sharingTaskResult = ref(false);
  const taskShareRecords = ref<Record<string, string>>({});
  const shareConfirmDialog = reactive({
    open: false,
    title: "分享生成结果",
    message: "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
    confirmText: "确认分享",
    cancelText: "取消",
    tone: "primary" as "primary" | "danger",
  });
  const selectedTaskShareRecord = computed(() => {
    const materialId = options.materialAssetId.value;
    return materialId ? taskShareRecords.value[materialId] || "" : "";
  });
  const selectedTaskShareable = computed(() => {
    const status = String(
      options.selectedTaskActionTask.value?.status || options.selectedTask.value?.status || "",
    ).toUpperCase();
    return status === "COMPLETED" && Boolean(options.materialAssetId.value);
  });

  function openTaskShareConfirm() {
    if (!selectedTaskShareable.value) return;
    const shared = Boolean(selectedTaskShareRecord.value);
    Object.assign(shareConfirmDialog, {
      title: shared ? "取消分享" : "分享生成结果",
      message: shared
        ? "取消分享后，这个生成结果将不再展示在首页分享区。"
        : "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
      confirmText: shared ? "取消分享" : "确认分享",
      tone: shared ? "danger" : "primary",
      open: true,
    });
  }

  function cancelTaskShareConfirm() {
    shareConfirmDialog.open = false;
  }

  async function acceptTaskShareConfirm() {
    const materialId = options.materialAssetId.value;
    if (!materialId || sharingTaskResult.value) return;
    sharingTaskResult.value = true;
    try {
      const currentShareId = selectedTaskShareRecord.value;
      if (currentShareId) {
        await deletePublicShare(currentShareId);
        const next = { ...taskShareRecords.value };
        delete next[materialId];
        taskShareRecords.value = next;
        messageApi.success("已取消分享");
      } else {
        const taskId =
          options.selectedTaskActionTask.value?.id
          || options.selectedTask.value?.id
          || options.selectedTaskId();
        const share = await createPublicShare({
          materialAssetId: materialId,
          sourceType: "task",
          sourceId: taskId,
        });
        taskShareRecords.value = { ...taskShareRecords.value, [materialId]: share.shareId };
        messageApi.success("已分享到首页");
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "分享失败");
    } finally {
      shareConfirmDialog.open = false;
      sharingTaskResult.value = false;
    }
  }

  return {
    acceptTaskShareConfirm,
    cancelTaskShareConfirm,
    openTaskShareConfirm,
    selectedTaskShareRecord,
    selectedTaskShareable,
    shareConfirmDialog,
    sharingTaskResult,
  };
}
