<template>
  <main class="task-detail-panel">
    <section v-if="!selectedTaskId" class="task-detail-empty">
      <h3>选择任务</h3>
    </section>

    <section
      v-else
      class="task-detail-content"
      :class="{ 'task-detail-content-image': imageTaskDisplay }"
      aria-labelledby="task-detail-title"
    >
      <section class="task-detail-summary" :class="{ 'task-detail-summary-image': imageTaskDisplay }">
        <header class="task-detail-header">
          <div>
            <h2 id="task-detail-title">{{ selectedTask?.title || "任务详情" }}</h2>
            <div class="task-detail-header__meta">
              <span class="surface-chip">{{ selectedTaskTypeLabel }}</span>
              <span class="surface-chip">{{ selectedTaskStageLabel }}</span>
              <span class="surface-chip">{{ selectedTaskHeaderAspectRatio }}</span>
              <span class="surface-chip">{{ selectedTaskJoinProgressPercent }}%</span>
              <span v-if="selectedTaskLoading" class="surface-chip surface-chip-loading">
                <IconRefresh size="xs" />
              </span>
            </div>
          </div>
          <button
            v-if="selectedTaskIsVideoTask"
            class="task-detail-header__workflow-btn"
            type="button"
            :title="linkedWorkflowId ? '查看阶段工作流' : '查找关联阶段工作流'"
            @click="emit('openWorkflow', linkedWorkflowId)"
          >
            <IconWorkflow size="xs" />
            <span>阶段工作流</span>
          </button>
        </header>

        <TaskStageTimeline :stages="selectedTaskStages" :image-mode="imageTaskDisplay" />

        <TaskDetailActions
          :task="selectedTaskActionTask"
          :loading="selectedTaskLoading"
          :managing-task-id="managingTaskId"
          :image-mode="imageTaskDisplay"
          @refresh="refreshSelectedTask"
          @prompt="openPromptDialog"
          @retry="handleRetry"
          @pause="handlePause"
          @continue="handleContinueTask"
          @terminate="handleTerminate"
          @delete="handleDelete"
        />
      </section>

      <section
        v-if="selectedTaskFailureReason"
        class="task-failure-card"
        :class="{ 'task-failure-card-open': failureDetailsOpen }"
      >
        <button
          type="button"
          class="task-failure-card__summary"
          :aria-expanded="failureDetailsOpen"
          @click="failureDetailsOpen = !failureDetailsOpen"
        >
          <span class="task-failure-card__icon" aria-hidden="true"><IconWarning size="xs" /></span>
          <strong>{{ selectedTaskFailureContext || "任务失败" }}</strong>
          <small class="task-failure-card__chevron" aria-hidden="true">
            <IconChevronDown size="xs" />
          </small>
        </button>
        <p v-if="failureDetailsOpen">{{ selectedTaskFailureReason }}</p>
      </section>

      <div class="task-detail-grid task-detail-grid-primary">
        <TaskResultPreview
          :progress-percent="selectedTaskJoinProgressPercent"
          :preview-loading="taskPreviewIsLoading"
          :load-state="taskPreviewLoadState"
          :media-items="taskPreviewMediaItems"
          :reference-items="selectedTaskReferenceItems"
          :awaiting-completed-preview="selectedTaskAwaitingCompletedPreview"
          :task-status="selectedTaskActionTask?.status || ''"
          :shareable="selectedTaskShareable"
          :sharing="sharingTaskResult"
          :shared="Boolean(selectedTaskShareRecord)"
          @preview="openTaskPreviewItem"
          @download="handleDownloadMedia"
          @share="openTaskShareConfirm"
          @loading="markTaskPreviewLoading"
          @ready="markTaskPreviewReady"
          @failed="markTaskPreviewFailed"
        />
      </div>

      <section
        v-if="showResultMaterials && (selectedTaskResultItems.length || selectedTaskMaterialItems.length)"
        class="detail-section detail-section-card"
      >
        <div class="detail-section__head">
          <h3>结果素材</h3>
          <RouterLink class="surface-chip detail-material-link" :to="materialLibraryLink">素材库</RouterLink>
        </div>
        <div class="detail-result-list">
          <button
            v-for="item in selectedTaskResultItems"
            :key="`result-${item.url}`"
            class="detail-result-item"
            type="button"
            @click="openTaskPreviewItem(item.title, item.url)"
          >
            <span class="detail-result-item__icon" aria-hidden="true">
              <IconImage v-if="previewKindForUrl(item.url) === 'image'" size="xs" />
              <IconVideo v-else-if="previewKindForUrl(item.url) === 'video'" size="xs" />
              <IconDownload v-else size="xs" />
            </span>
            <span class="detail-result-item__copy">
              <strong>{{ item.title }}</strong>
              <small>结果</small>
            </span>
          </button>
          <button
            v-for="item in selectedTaskMaterialItems"
            :key="`material-${item.url}`"
            class="detail-result-item"
            type="button"
            @click="openTaskPreviewItem(item.title, item.url)"
          >
            <span class="detail-result-item__icon" aria-hidden="true">
              <IconImage v-if="previewKindForUrl(item.url) === 'image'" size="xs" />
              <IconVideo v-else-if="previewKindForUrl(item.url) === 'video'" size="xs" />
              <IconDownload v-else size="xs" />
            </span>
            <span class="detail-result-item__copy">
              <strong>{{ item.title }}</strong>
              <small>素材</small>
            </span>
          </button>
        </div>
      </section>

      <TaskMonitoringSummary
        :monitoring-rows="selectedTaskCompactMonitoringRows"
        :artifact-rows="selectedTaskCompactArtifactRows"
        :artifact-directory-hint="selectedTaskArtifactDirectoryHint"
        :short-artifact-directory-hint="selectedTaskShortArtifactDirectoryHint"
      />
    </section>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
    <AppConfirmDialog v-bind="shareConfirmDialog" @confirm="acceptTaskShareConfirm" @cancel="cancelTaskShareConfirm" />
    <TaskPromptDialog
      :open="promptDialogOpen"
      :title="selectedTask?.title || '当前任务'"
      :prompt="selectedTaskPromptText"
      @close="closePromptDialog"
    />
    <AppPreviewDialog
      :open="previewDialog.open"
      :kind="previewDialog.kind"
      :title="previewDialog.title"
      :url="previewDialog.url"
      :image-load-failed="previewImageLoadFailed"
      @close="closeTaskPreviewDialog"
      @image-error="previewImageLoadFailed = true"
    />
  </main>
</template>

<script setup lang="ts">
/**
 * 任务详情面板组件。
 * 展示统一任务列表中选中任务的详情、监控和操作。
 */
import { RouterLink } from "vue-router";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import TaskPromptDialog from "./TaskPromptDialog.vue";
import TaskResultPreview from "./TaskResultPreview.vue";
import TaskStageTimeline from "./TaskStageTimeline.vue";
import TaskMonitoringSummary from "./TaskMonitoringSummary.vue";
import TaskDetailActions from "./TaskDetailActions.vue";
import {
  IconChevronDown,
  IconDownload,
  IconImage,
  IconRefresh,
  IconVideo,
  IconWarning,
  IconWorkflow,
} from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, type DownloadMediaKind } from "@/utils/download";
import { useTaskDetail } from "../composables/useTaskDetail";
import { useTaskPreviewState } from "../composables/useTaskPreviewState";
import { useTaskResultSharing } from "../composables/useTaskResultSharing";
import type { TaskDetail, TaskListItem, TaskMaterial } from "@/types";

const props = defineProps<{
  selectedTaskId: string;
  tasks: TaskListItem[];
  reloadTasks: () => Promise<void>;
  detailMode?: "default" | "image-task";
  showResultMaterials?: boolean;
}>();

const showResultMaterials = computed(() => props.showResultMaterials !== false);
const imageTaskDisplay = computed(() => props.detailMode === "image-task");

const emit = defineEmits<{
  deleted: [taskId: string];
  openWorkflow: [workflowId: string];
}>();

const detail = useTaskDetail({
  selectedTaskId: () => props.selectedTaskId,
  tasks: () => props.tasks,
  reloadTasks: props.reloadTasks,
  onDeleted: (taskId) => emit("deleted", taskId),
});

const {
  selectedTaskLoading,
  managingTaskId,
  failureDetailsOpen,
  selectedTask,
  selectedTaskActionTask,
  selectedTaskTypeLabel,
  selectedTaskStageLabel,
  selectedTaskPromptText,
  selectedTaskJoinProgressPercent,
  selectedTaskCompactMonitoringRows,
  selectedTaskFailureReason,
  selectedTaskFailureContext,
  selectedTaskPreviewMedia,
  selectedTaskAwaitingCompletedPreview,
  selectedTaskResultItems,
  selectedTaskReferenceItems,
  selectedTaskMaterialItems,
  materialLibraryLink,
  selectedTaskCompactArtifactRows,
  selectedTaskShortArtifactDirectoryHint,
  selectedTaskArtifactDirectoryHint,
  selectedTaskStages,
  selectedTaskIsActive,
  loadSelectedTaskDetails,
  startDetailPolling,
  stopDetailPolling,
  refreshSelectedTask,
  handleRetry,
  handlePause,
  handleTerminate,
  handleContinueTask,
  handleDelete,
  confirmDialog,
  acceptConfirm,
  cancelConfirm,
} = detail;

async function handleDownloadMedia(url: string, title: string, mediaType: DownloadMediaKind) {
  try {
    const result = await downloadMedia({ url, title, mediaType });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

// 选中变化时重新加载详情
import { computed, onUnmounted, ref, watch } from "vue";
const promptDialogOpen = ref(false);
const {
  closeTaskPreviewDialog,
  markTaskPreviewFailed,
  markTaskPreviewLoading,
  markTaskPreviewReady,
  openTaskPreviewItem,
  previewDialog,
  previewImageLoadFailed,
  previewKindForUrl,
  taskPreviewIsLoading,
  taskPreviewLoadState,
  taskPreviewMediaItems,
} = useTaskPreviewState(selectedTaskPreviewMedia);
const selectedTaskTypeKey = computed(() => {
  const task = selectedTask.value as TaskDetail | null;
  return String(task?.requestSnapshot?.taskType || task?.taskType || "video_generation").trim() || "video_generation";
});
const selectedTaskIsVideoTask = computed(() => selectedTaskTypeKey.value === "video_generation");
const linkedWorkflowId = computed(() => {
  const task = selectedTask.value as TaskDetail | null;
  const materials: TaskMaterial[] = task?.materials ?? [];
  const materialWorkflowId = materials.find((item) => item.workflowId)?.workflowId;
  if (materialWorkflowId) {
    return materialWorkflowId;
  }
  const context = task?.executionContext ?? {};
  const contextWorkflowId = context.workflowId;
  return typeof contextWorkflowId === "string" ? contextWorkflowId : "";
});
const selectedTaskHeaderAspectRatio = computed(() => {
  const task = selectedTask.value as TaskDetail | TaskListItem | null;
  if (!task) return "未设置";
  const requestSnapshot = "requestSnapshot" in task ? task.requestSnapshot : null;
  const aspectRatio = requestSnapshot?.aspectRatio || task.aspectRatio || "";
  return String(aspectRatio).trim() || "未设置";
});
const selectedTaskPreviewMaterialId = computed(() => selectedTaskPreviewMedia.value?.materialAssetId || "");
const {
  acceptTaskShareConfirm,
  cancelTaskShareConfirm,
  openTaskShareConfirm,
  selectedTaskShareRecord,
  selectedTaskShareable,
  shareConfirmDialog,
  sharingTaskResult,
} = useTaskResultSharing({
  selectedTaskId: () => props.selectedTaskId,
  selectedTask,
  selectedTaskActionTask,
  materialAssetId: selectedTaskPreviewMaterialId,
});

function openPromptDialog() {
  promptDialogOpen.value = true;
}

function closePromptDialog() {
  promptDialogOpen.value = false;
}

watch(
  () => props.selectedTaskId,
  () => {
    closePromptDialog();
    closeTaskPreviewDialog();
    stopDetailPolling();
    void loadSelectedTaskDetails().then(() => {
      if (selectedTaskIsActive.value) {
        startDetailPolling();
      }
    });
  },
  { immediate: true },
);

onUnmounted(() => {
  stopDetailPolling();
});
</script>

<style scoped src="./task-detail-panel.css"></style>
