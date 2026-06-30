<template>
  <main class="task-detail-panel">
    <section v-if="!selectedTaskId" class="task-detail-empty">
      <h3>选择任务</h3>
    </section>

    <section v-else class="task-detail-content" aria-labelledby="task-detail-title">
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

      <section class="detail-stage-card" aria-label="任务阶段">
        <div class="detail-stage-line">
          <div v-for="stage in selectedTaskStages" :key="stage.key" class="detail-stage-line__item" :class="`detail-stage-line__item-${stage.state}`">
            <span class="detail-stage-line__dot" :class="stageStateClass(stage.state)" aria-hidden="true"></span>
            <span class="detail-stage-line__copy">
              <strong>{{ stage.label }}</strong>
              <small>{{ stage.stateLabel }}</small>
            </span>
          </div>
        </div>
      </section>

      <div class="detail-actions detail-actions-card" aria-label="任务操作">
        <button class="jd-button jd-button--sm" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
          <IconRefresh size="xs" />
          刷新
        </button>
        <button class="jd-button jd-button--sm" type="button" :disabled="selectedTaskLoading" @click="openPromptDialog">
          <IconText size="xs" />
          提示词
        </button>
        <button v-if="selectedTaskActionTask?.status === 'FAILED'" class="jd-button jd-button--sm jd-button--primary" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleRetry(selectedTaskActionTask)">
          <IconRefresh size="xs" />
          重试
        </button>
        <button v-if="selectedTaskActionTask?.status === 'COMPLETED'" class="jd-button jd-button--sm jd-button--primary" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleRetry(selectedTaskActionTask)">
          <IconRefresh size="xs" />
          重新生成
        </button>
        <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)" class="jd-button jd-button--sm" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handlePause(selectedTaskActionTask)">
          <span class="jd-button__pause" aria-hidden="true"></span>
          暂停
        </button>
        <button v-if="selectedTaskActionTask?.status === 'PAUSED'" class="jd-button jd-button--sm jd-button--primary" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleContinueTask(selectedTaskActionTask)">
          <IconRefresh size="xs" />
          继续
        </button>
        <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)" class="jd-button jd-button--sm jd-button--warning" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleTerminate(selectedTaskActionTask)">
          <IconWarning size="xs" />
          终止
        </button>
        <button v-if="selectedTaskActionTask" class="jd-button jd-button--sm jd-button--danger" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleDelete(selectedTaskActionTask)">
          <IconDelete size="xs" />
          删除
        </button>
      </div>

      <section v-if="selectedTaskFailureReason" class="task-failure-card" :class="{ 'task-failure-card-open': failureDetailsOpen }">
        <button type="button" class="task-failure-card__summary" :aria-expanded="failureDetailsOpen" @click="failureDetailsOpen = !failureDetailsOpen">
          <span class="task-failure-card__icon" aria-hidden="true"><IconWarning size="xs" /></span>
          <strong>{{ selectedTaskFailureContext || "任务失败" }}</strong>
          <small class="task-failure-card__chevron" aria-hidden="true">
            <IconChevronDown size="xs" />
          </small>
        </button>
        <p v-if="failureDetailsOpen">{{ selectedTaskFailureReason }}</p>
      </section>

      <div class="task-detail-grid task-detail-grid-primary">
        <section class="detail-section detail-section-card detail-preview-section">
          <div class="detail-section__head">
            <h3>结果预览</h3>
            <span class="surface-chip">{{ selectedTaskJoinProgressPercent }}%</span>
          </div>
          <div
            class="task-result-preview"
            :class="{
              'task-result-preview-loading': taskPreviewIsLoading,
              'task-result-preview-with-references': selectedTaskReferenceItems.length > 0,
            }"
          >
            <aside v-if="selectedTaskReferenceItems.length" class="task-reference-panel" aria-label="参考图">
              <div class="task-reference-panel__head">
                <span>参考图</span>
                <small>{{ selectedTaskReferenceItems.length }} 张</small>
              </div>
              <div class="task-reference-stack">
                <article
                  v-for="(item, index) in selectedTaskReferenceItems"
                  :key="`reference-${item.url}`"
                  class="task-reference-card"
                  :style="referenceCardStyle(index)"
                >
                  <button
                    type="button"
                    class="task-reference-card__preview"
                    :aria-label="`预览${item.title}`"
                    @click="openTaskPreviewItem(item.title, item.url)"
                  >
                    <img :src="item.thumbnailUrl || item.url" :alt="item.title" loading="lazy" />
                  </button>
                  <button
                    class="task-reference-card__download"
                    type="button"
                    :aria-label="`下载${item.title}`"
                    @click.stop="handleDownloadMedia(item.url, item.title, 'image')"
                  >
                    <IconDownload size="xs" />
                  </button>
                </article>
              </div>
            </aside>

            <div class="task-result-preview__main">
              <div v-if="selectedTaskPreviewMedia" class="task-result-preview__actions">
                <button
                  type="button"
                  class="task-result-preview__action"
                  @click="openTaskPreviewItem(selectedTaskPreviewMedia.title || '任务结果预览', selectedTaskPreviewMedia.url)"
                >
                  <IconImage v-if="selectedTaskPreviewMedia.type === 'image'" size="xs" />
                  <IconVideo v-else size="xs" />
                  预览
                </button>
                <button
                  class="task-result-preview__action"
                  type="button"
                  @click="handleDownloadMedia(selectedTaskPreviewMedia.url, selectedTaskPreviewMedia.title || '任务结果', selectedTaskPreviewMedia.type)"
                >
                  <IconDownload size="xs" />
                  下载
                </button>
                <button
                  v-if="selectedTaskShareable"
                  class="task-result-preview__action"
                  type="button"
                  :disabled="sharingTaskResult"
                  @click="openTaskShareConfirm"
                >
                  <IconShare size="xs" />
                  {{ selectedTaskShareRecord ? "已分享" : "分享" }}
                </button>
              </div>
              <video
                v-if="selectedTaskPreviewMedia?.type === 'video'"
                :src="selectedTaskPreviewMedia.url"
                :poster="selectedTaskPreviewMedia.posterUrl || undefined"
                controls
                playsinline
                preload="metadata"
                :aria-label="selectedTaskPreviewMedia.title"
                @loadstart="markTaskPreviewLoading"
                @loadedmetadata="markTaskPreviewReady"
                @loadeddata="markTaskPreviewReady"
                @canplay="markTaskPreviewReady"
                @error="markTaskPreviewFailed"
              ></video>
              <button
                v-else-if="selectedTaskPreviewMedia?.type === 'image'"
                type="button"
                class="task-result-preview__image-button"
                :aria-label="`预览${selectedTaskPreviewMedia.title || '任务结果'}`"
                @click="openTaskPreviewItem(selectedTaskPreviewMedia.title || '任务结果预览', selectedTaskPreviewMedia.url)"
              >
                <img
                  :src="selectedTaskPreviewMedia.url"
                  :alt="selectedTaskPreviewMedia.title || '任务结果预览'"
                  @load="markTaskPreviewReady"
                  @error="markTaskPreviewFailed"
                />
              </button>
              <div v-else-if="selectedTaskAwaitingCompletedPreview" class="task-result-preview__pending" role="status" aria-live="polite">
                <IconLoading size="md" />
                <span>加载预览中</span>
              </div>
              <div v-else>{{ selectedTaskActionTask?.status === "COMPLETED" ? "暂无可预览结果" : "生成中" }}</div>
              <div v-if="taskPreviewIsLoading" class="task-result-preview__loading" role="status" aria-live="polite">
                <IconLoading size="md" />
                <span>加载预览中</span>
              </div>
              <div v-else-if="taskPreviewLoadState === 'failed'" class="task-result-preview__loading task-result-preview__loading-error">
                <IconWarning size="sm" />
                <span>预览加载失败</span>
              </div>
            </div>
          </div>
        </section>

      </div>

      <section v-if="selectedTaskResultItems.length || selectedTaskMaterialItems.length" class="detail-section detail-section-card">
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

      <div v-if="selectedTaskCompactMonitoringRows.length || selectedTaskCompactArtifactRows.length" class="task-detail-grid task-detail-grid-secondary">
        <section v-if="selectedTaskCompactMonitoringRows.length" class="detail-section detail-section-card">
          <h3>监控</h3>
          <div class="detail-params">
            <div v-for="item in selectedTaskCompactMonitoringRows" :key="item.label" class="detail-params__row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <section v-if="selectedTaskCompactArtifactRows.length" class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>产物</h3>
            <span class="surface-chip" :title="selectedTaskArtifactDirectoryHint">{{ selectedTaskShortArtifactDirectoryHint }}</span>
          </div>
          <div class="detail-params">
            <div v-for="item in selectedTaskCompactArtifactRows" :key="item.label" class="detail-params__row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>
      </div>

      <section class="detail-section detail-section-card detail-trace-section" :class="{ 'detail-trace-section-open': traceListOpen }">
        <button
          type="button"
          class="detail-trace-summary"
          :aria-expanded="traceListOpen"
          aria-controls="task-detail-traces"
          @click="traceListOpen = !traceListOpen"
        >
          <span class="detail-trace-summary__copy">
            <strong>追踪</strong>
            <small>{{ selectedTaskTracePreview[0]?.message || "暂无记录" }}</small>
          </span>
          <span class="surface-chip">{{ selectedTaskTrace.length }} 条</span>
          <span class="detail-trace-summary__chevron" aria-hidden="true">
            <IconChevronDown size="xs" />
          </span>
        </button>
        <div v-if="traceListOpen" id="task-detail-traces" class="detail-traces">
          <div v-if="selectedTaskTrace.length === 0" class="detail-traces__empty">暂无记录</div>
          <div v-for="event in selectedTaskTracePreview" :key="`${event.timestamp}-${event.event}-${event.stage}`" class="detail-traces__item">
            <div class="detail-traces__body">
              <p>{{ event.message }}</p>
              <small>
                <span class="detail-traces__stage">{{ formatTraceStage(event.stage) }}</span>
                <span class="detail-traces__event">{{ formatTraceEvent(event.event) }}</span>
              </small>
            </div>
            <time class="detail-traces__time" :datetime="event.timestamp || undefined">{{ formatDateTime(event.timestamp) }}</time>
          </div>
        </div>
      </section>

    </section>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
    <AppConfirmDialog v-bind="shareConfirmDialog" @confirm="acceptTaskShareConfirm" @cancel="cancelTaskShareConfirm" />
    <Teleport to="body">
      <Transition name="task-prompt-dialog-fade">
        <div
          v-if="promptDialogOpen"
          class="task-prompt-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="task-prompt-dialog-title"
          @click.self="closePromptDialog"
          @keydown.esc.stop.prevent="closePromptDialog"
        >
          <section class="task-prompt-dialog__panel">
            <header class="task-prompt-dialog__header">
              <div>
                <h3 id="task-prompt-dialog-title">使用的提示词</h3>
                <p>{{ selectedTask?.title || "当前任务" }}</p>
              </div>
              <button ref="promptCloseButtonRef" class="task-prompt-dialog__close" type="button" aria-label="关闭提示词" title="关闭" @click="closePromptDialog">
                <IconClose size="sm" />
              </button>
            </header>
            <div class="task-prompt-dialog__content" :class="{ 'task-prompt-dialog__content-empty': !selectedTaskPromptText }">
              <pre v-if="selectedTaskPromptText">{{ selectedTaskPromptText }}</pre>
              <p v-else>暂无提示词</p>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>
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
import { IconChevronDown, IconClose, IconDelete, IconDownload, IconImage, IconLoading, IconRefresh, IconShare, IconText, IconVideo, IconWarning, IconWorkflow } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { createPublicShare, deletePublicShare } from "@/api/public-shares";
import { downloadMedia, type DownloadMediaKind } from "@/utils/download";
import { useTaskDetail } from "../composables/useTaskDetail";
import type { TaskDetail, TaskListItem, TaskMaterial } from "@/types";

const props = defineProps<{
  selectedTaskId: string;
  tasks: TaskListItem[];
  reloadTasks: () => Promise<void>;
}>();

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
  selectedTaskTrace,
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
  selectedTaskTracePreview,
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
  formatDateTime,
  formatTraceStage,
  formatTraceEvent,
  stageStateClass,
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
import { computed, nextTick, onUnmounted, reactive, ref, watch } from "vue";
const traceListOpen = ref(false);
const promptDialogOpen = ref(false);
const promptCloseButtonRef = ref<HTMLButtonElement | null>(null);
const previewImageLoadFailed = ref(false);
const taskPreviewLoadState = ref<"idle" | "loading" | "ready" | "failed">("idle");
const taskPreviewMediaUrl = computed(() => selectedTaskPreviewMedia.value?.url || "");
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
const taskPreviewIsLoading = computed(() => Boolean(taskPreviewMediaUrl.value) && taskPreviewLoadState.value === "loading");
const selectedTaskHeaderAspectRatio = computed(() => {
  const task = selectedTask.value as TaskDetail | TaskListItem | null;
  if (!task) return "未设置";
  const requestSnapshot = "requestSnapshot" in task ? task.requestSnapshot : null;
  const aspectRatio = requestSnapshot?.aspectRatio || task.aspectRatio || "";
  return String(aspectRatio).trim() || "未设置";
});
const selectedTaskPreviewMaterialId = computed(() => selectedTaskPreviewMedia.value?.materialAssetId || "");
const selectedTaskShareRecord = computed(() => {
  const materialId = selectedTaskPreviewMaterialId.value;
  return materialId ? taskShareRecords.value[materialId] || "" : "";
});
const selectedTaskShareable = computed(() => {
  const status = String(selectedTaskActionTask.value?.status || selectedTask.value?.status || "").toUpperCase();
  return status === "COMPLETED" && Boolean(selectedTaskPreviewMaterialId.value);
});
const previewDialog = reactive({
  open: false,
  kind: "image" as "storyboard" | "image" | "video",
  title: "",
  url: "",
});

async function openPromptDialog() {
  promptDialogOpen.value = true;
  await nextTick();
  promptCloseButtonRef.value?.focus({ preventScroll: true });
}

function closePromptDialog() {
  promptDialogOpen.value = false;
}

function openTaskShareConfirm() {
  if (!selectedTaskShareable.value) return;
  const shared = Boolean(selectedTaskShareRecord.value);
  shareConfirmDialog.title = shared ? "取消分享" : "分享生成结果";
  shareConfirmDialog.message = shared
    ? "取消分享后，这个生成结果将不再展示在首页分享区。"
    : "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。";
  shareConfirmDialog.confirmText = shared ? "取消分享" : "确认分享";
  shareConfirmDialog.tone = shared ? "danger" : "primary";
  shareConfirmDialog.open = true;
}

function cancelTaskShareConfirm() {
  shareConfirmDialog.open = false;
}

async function acceptTaskShareConfirm() {
  const materialId = selectedTaskPreviewMaterialId.value;
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
      const taskId = selectedTaskActionTask.value?.id || selectedTask.value?.id || props.selectedTaskId;
      const share = await createPublicShare({ materialAssetId: materialId, sourceType: "task", sourceId: taskId });
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

const IMAGE_PREVIEW_URL_PATTERN = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
const VIDEO_PREVIEW_URL_PATTERN = /\.(m4v|mov|mp4|ogg|webm)(?:[?#].*)?$/i;

function previewKindForUrl(url: string): "image" | "video" | "storyboard" {
  if (VIDEO_PREVIEW_URL_PATTERN.test(url)) return "video";
  if (IMAGE_PREVIEW_URL_PATTERN.test(url)) return "image";
  return "image";
}

function openTaskPreviewItem(title: string, url: string) {
  previewImageLoadFailed.value = false;
  previewDialog.kind = previewKindForUrl(url);
  previewDialog.title = title;
  previewDialog.url = url;
  previewDialog.open = true;
}

function referenceCardStyle(index: number) {
  const direction = index % 2 === 0 ? -1 : 1;
  return {
    zIndex: String(20 - index),
    transform: `translateX(${direction * Math.min(index, 3) * 5}px) rotate(${direction * Math.min(index + 1, 4) * 1.4}deg)`,
  };
}

function closeTaskPreviewDialog() {
  previewDialog.open = false;
  previewDialog.title = "";
  previewDialog.url = "";
  previewImageLoadFailed.value = false;
}

function markTaskPreviewLoading() {
  if (taskPreviewMediaUrl.value) {
    taskPreviewLoadState.value = "loading";
  }
}

function markTaskPreviewReady() {
  if (taskPreviewMediaUrl.value) {
    taskPreviewLoadState.value = "ready";
  }
}

function markTaskPreviewFailed() {
  if (taskPreviewMediaUrl.value) {
    taskPreviewLoadState.value = "failed";
  }
}

watch(taskPreviewMediaUrl, (url) => {
  taskPreviewLoadState.value = url ? "loading" : "idle";
}, { immediate: true });

watch(() => props.selectedTaskId, () => {
  traceListOpen.value = false;
  closePromptDialog();
  closeTaskPreviewDialog();
  stopDetailPolling();
  void loadSelectedTaskDetails({ includeTrace: true }).then(() => {
    if (selectedTaskIsActive.value) {
      startDetailPolling();
    }
  });
}, { immediate: true });

onUnmounted(() => {
  stopDetailPolling();
});
</script>

<style scoped>
.task-detail-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 14px;
  overflow: auto;
}

.task-detail-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  color: var(--text-muted);
}

.task-detail-content {
  display: grid;
  gap: 16px;
  width: 100%;
  min-width: 0;
}

.task-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  position: sticky;
  top: 8px;
  z-index: 2;
  min-width: 0;
  padding: 16px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(32px) saturate(1.8);
}

.task-detail-header h2 {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.35;
  font-weight: 600;
  color: var(--text-strong);
  word-break: break-word;
}

.task-detail-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.task-detail-header__workflow-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-shrink: 0;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-strong);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  overflow: hidden;
  isolation: isolate;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.05), 0 8px 22px rgba(20, 184, 166, 0.12);
}

.task-detail-header__workflow-btn::before {
  content: "";
  position: absolute;
  inset: -2px;
  z-index: -1;
  background: linear-gradient(
    115deg,
    rgba(99, 102, 241, 0) 0%,
    rgba(99, 102, 241, 0.18) 18%,
    rgba(20, 184, 166, 0.42) 34%,
    rgba(245, 158, 11, 0.34) 50%,
    rgba(236, 72, 153, 0.36) 66%,
    rgba(99, 102, 241, 0.2) 82%,
    rgba(99, 102, 241, 0) 100%
  );
  background-size: 260% 100%;
  animation: workflow-button-shine 2.6s linear infinite;
}

.task-detail-header__workflow-btn > svg,
.task-detail-header__workflow-btn > span {
  position: relative;
  z-index: 1;
}

.task-detail-header__workflow-btn:hover {
  background: var(--bg-soft);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.12), 0 10px 28px rgba(99, 102, 241, 0.2);
}

@keyframes workflow-button-shine {
  from {
    background-position: 160% 0;
  }
  to {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-detail-header__workflow-btn::before {
    animation: none;
    background-position: 50% 0;
  }
}

.surface-chip-loading {
  animation: chip-spin 1s linear infinite;
}

@keyframes chip-spin {
  to { transform: rotate(360deg); }
}

.detail-stage-card {
  padding: 12px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.64);
  box-shadow: var(--shadow-soft);
}

.detail-stage-line {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.detail-stage-line__item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgba(80, 90, 110, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.54);
}

.detail-stage-line__item-done {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.16);
}

.detail-stage-line__item-active,
.detail-stage-line__item-paused {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.28);
}

.detail-stage-line__item-failed {
  background: rgba(229, 72, 101, 0.08);
  border-color: rgba(229, 72, 101, 0.22);
}

.detail-stage-line__dot {
  position: relative;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--text-muted);
}

.detail-stage-line__dot.task-stage-row--done {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
}

.detail-stage-line__dot.task-stage-row--active {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  animation: task-stage-dot-breathe 1.8s ease-in-out infinite;
}

.detail-stage-line__dot.task-stage-row--active::before {
  content: "";
  position: absolute;
  inset: -7px;
  border-radius: inherit;
  background: rgba(99, 102, 241, 0.2);
  opacity: 0;
  animation: task-stage-dot-pulse 1.8s ease-out infinite;
  pointer-events: none;
}

.detail-stage-line__dot.task-stage-row--paused {
  background: var(--accent-warning);
  border-color: var(--accent-warning);
}

.detail-stage-line__dot.task-stage-row--failed {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
}

.detail-stage-line__copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.detail-stage-line__copy strong {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-stage-line__copy small {
  font-size: 0.68rem;
  color: var(--text-muted);
}

@keyframes task-stage-dot-breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.12);
  }
}

@keyframes task-stage-dot-pulse {
  0% {
    opacity: 0.55;
    transform: scale(0.45);
  }
  70%,
  100% {
    opacity: 0;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .detail-stage-line__dot.task-stage-row--active,
  .detail-stage-line__dot.task-stage-row--active::before {
    animation: none;
  }
}

.task-failure-card {
  border-radius: 12px;
  border: 1px solid rgba(229, 72, 101, 0.2);
  background: rgba(229, 72, 101, 0.04);
  padding: 10px 14px;
}

.task-failure-card__summary {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--accent-danger);
  font-size: 0.85rem;
  padding: 0;
}

.task-failure-card__chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.task-failure-card-open .task-failure-card__chevron {
  transform: rotate(180deg);
}

.task-failure-card p {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
}

.task-detail-grid {
  display: grid;
  gap: 16px;
}

.task-detail-grid-primary {
  grid-template-columns: minmax(0, 1fr);
  align-items: stretch;
}

.task-detail-grid-secondary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.detail-section {
  display: grid;
  gap: 10px;
}

.detail-section-card {
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.66);
  border: var(--glass-border);
  box-shadow: var(--shadow-soft);
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-section__head h3 {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-strong);
}

.task-result-preview {
  position: relative;
  border-radius: var(--radius-md);
  border: 1px solid rgba(99, 102, 241, 0.08);
  overflow: hidden;
  background: rgba(245, 247, 252, 0.72);
  min-height: clamp(260px, 36vw, 430px);
  display: grid;
  grid-template-columns: 1fr;
  place-items: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.task-result-preview-with-references {
  grid-template-columns: minmax(132px, 0.28fr) minmax(0, 1fr);
  align-items: stretch;
  place-items: stretch;
}

.task-reference-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  padding: 12px;
  border-right: 1px solid rgba(99, 102, 241, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.66), rgba(238, 242, 255, 0.34));
}

.task-reference-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-strong);
  font-size: 0.76rem;
  font-weight: 700;
}

.task-reference-panel__head small {
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 600;
  white-space: nowrap;
}

.task-reference-stack {
  display: grid;
  align-content: start;
  justify-items: center;
  min-height: 0;
  padding: 4px 6px 24px;
  overflow-y: auto;
}

.task-reference-card {
  position: relative;
  width: min(112px, 100%);
  aspect-ratio: 4 / 5;
  margin-top: -28px;
  border-radius: 9px;
  transform-origin: center top;
  transition: transform 160ms ease, z-index 160ms ease;
}

.task-reference-card:first-child {
  margin-top: 0;
}

.task-reference-card:hover,
.task-reference-card:focus-within {
  z-index: 40 !important;
  transform: translateY(-5px) rotate(0deg) !important;
}

.task-reference-card__preview {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: inherit;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  cursor: zoom-in;
}

.task-reference-card__preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-reference-card__download {
  position: absolute;
  right: -7px;
  bottom: -7px;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: var(--accent-indigo);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
  opacity: 0.92;
  transform: scale(1);
  transition: opacity 140ms ease, transform 140ms ease, background 140ms ease;
}

.task-reference-card:hover .task-reference-card__download,
.task-reference-card:focus-within .task-reference-card__download {
  opacity: 1;
  transform: scale(1);
}

.task-reference-card__download:hover {
  background: #eef2ff;
}

.task-result-preview__main {
  position: relative;
  display: grid;
  place-items: center;
  min-width: 0;
  min-height: inherit;
  overflow: hidden;
}

.task-result-preview__actions {
  position: absolute;
  right: 12px;
  top: 12px;
  z-index: 3;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.task-result-preview__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-strong);
  font-size: 0.74rem;
  font-weight: 700;
  text-decoration: none;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  cursor: pointer;
}

.task-result-preview__action:hover {
  background: #eef2ff;
  color: var(--accent-blue);
}

.task-result-preview__image-button {
  display: grid;
  place-items: center;
  width: 100%;
  min-height: inherit;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.task-result-preview__loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  padding: 18px;
  background: rgba(245, 247, 252, 0.82);
  color: var(--accent-indigo);
  text-align: center;
  backdrop-filter: blur(8px);
}

.task-result-preview__loading span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 600;
}

.task-result-preview__loading-error {
  color: var(--accent-danger);
}

.task-result-preview__pending {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: var(--accent-indigo);
}

.task-result-preview__pending span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 600;
}

.task-result-preview__main img,
.task-result-preview__main video {
  width: 100%;
  max-height: min(52vh, 420px);
  display: block;
  object-fit: contain;
}

.task-result-preview__main video {
  aspect-ratio: 16 / 9;
  background: #111827;
}

.detail-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.detail-overview__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  min-height: 34px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.52);
  font-size: 0.82rem;
  color: var(--text-body);
}

.detail-overview__row strong {
  color: var(--text-strong);
  font-weight: 600;
}

.detail-overview__row-progress {
  gap: 10px;
  grid-column: 1 / -1;
}

.detail-overview__progress {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-softer);
  overflow: hidden;
}

.detail-overview__progress-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent-indigo);
  transition: width 0.3s;
}

.detail-params {
  display: grid;
  gap: 8px;
}

.detail-params__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.8rem;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--text-body);
}

.detail-params__row strong {
  color: var(--text-strong);
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.detail-params-section {
  align-content: start;
}

.detail-param-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}

.detail-param-tag {
  display: grid;
  gap: 4px;
  flex: 1 1 150px;
  min-width: min(100%, 150px);
  min-height: 58px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  background: rgba(99, 102, 241, 0.055);
}

.detail-param-tag-progress {
  flex-basis: 100%;
}

.detail-param-tag__label {
  font-size: 0.7rem;
  line-height: 1.25;
  color: var(--text-muted);
}

.detail-param-tag__value {
  min-width: 0;
  font-size: 0.86rem;
  line-height: 1.35;
  font-weight: 650;
  color: var(--text-strong);
  word-break: break-word;
}

.detail-param-tag__progress {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: 10px;
  align-items: center;
}

.detail-note-block {
  margin-top: 8px;
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-softer);
}

.detail-note-block span {
  display: block;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.detail-note-block p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow: auto;
}

.detail-material-link {
  text-decoration: none;
}

.detail-result-list {
  display: flex;
  gap: 10px;
  min-width: 0;
  overflow-x: auto;
  padding: 2px 2px 8px;
  scroll-snap-type: x proximity;
}

.detail-result-item {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  flex: 0 0 min(220px, 72vw);
  gap: 8px;
  min-height: 58px;
  padding: 10px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.52);
  color: var(--text-strong);
  cursor: zoom-in;
  scroll-snap-align: start;
  text-align: left;
  transition: background 0.15s, border-color 0.15s, transform 0.12s;
}

.detail-result-item:hover {
  border-color: rgba(99, 102, 241, 0.24);
  background: rgba(99, 102, 241, 0.07);
  transform: translateY(-1px);
}

.detail-result-item__icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.detail-result-item__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.detail-result-item__copy strong {
  overflow: hidden;
  color: var(--text-strong);
  font-size: 0.82rem;
  font-weight: 650;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-result-item__copy small {
  color: var(--text-muted);
  font-size: 0.7rem;
}

.detail-trace-section {
  gap: 0;
  padding: 0;
  overflow: hidden;
}

.detail-trace-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  padding: 14px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.detail-trace-summary:hover {
  background: rgba(99, 102, 241, 0.045);
}

.detail-trace-summary__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.detail-trace-summary__copy strong {
  font-size: 0.88rem;
  font-weight: 650;
  color: var(--text-strong);
}

.detail-trace-summary__copy small {
  min-width: 0;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.76rem;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-trace-summary__chevron {
  display: grid;
  place-items: center;
  color: var(--text-muted);
  transition: transform 0.18s ease;
}

.detail-trace-section-open .detail-trace-summary__chevron {
  transform: rotate(180deg);
}

.detail-traces {
  display: grid;
  max-height: 360px;
  padding: 4px 16px 14px;
  border-top: 1px solid rgba(80, 90, 110, 0.08);
  overflow: auto;
}

.detail-traces__empty {
  text-align: center;
  padding: 16px;
  color: var(--text-muted);
  font-size: 0.82rem;
}

.detail-traces__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: 14px;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid rgba(80, 90, 110, 0.08);
}

.detail-traces__item:last-child {
  border-bottom: 0;
}

.detail-traces__body {
  min-width: 0;
}

.detail-traces__item p {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--text-body);
  word-break: break-word;
}

.detail-traces__item small {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 6px;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.detail-traces__stage {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-softer);
  font-weight: 600;
  font-size: 0.68rem;
}

.detail-traces__event {
  color: var(--text-body);
}

.detail-traces__time {
  padding-top: 1px;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.72rem;
  line-height: 1.5;
  white-space: nowrap;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-start;
}

.detail-actions-card {
  padding: 12px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.64);
  box-shadow: var(--shadow-soft);
}

.task-prompt-dialog {
  position: fixed;
  inset: 0;
  z-index: 1480;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 10, 20, 0.25);
  backdrop-filter: blur(34px) saturate(1.8);
  -webkit-backdrop-filter: blur(34px) saturate(1.8);
}

.task-prompt-dialog__panel {
  display: grid;
  gap: 14px;
  width: min(640px, 100%);
  max-height: min(78vh, 680px);
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 22px 56px rgba(0, 0, 0, 0.13), inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

.task-prompt-dialog__header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
}

.task-prompt-dialog__header h3,
.task-prompt-dialog__header p,
.task-prompt-dialog__content p {
  margin: 0;
}

.task-prompt-dialog__header h3 {
  color: var(--text-strong);
  font-size: 1rem;
  font-weight: 850;
  line-height: 1.35;
}

.task-prompt-dialog__header p {
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 720;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-prompt-dialog__close {
  display: inline-grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-muted);
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.task-prompt-dialog__close:hover,
.task-prompt-dialog__close:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.2);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.task-prompt-dialog__content {
  min-height: 160px;
  max-height: min(56vh, 480px);
  overflow: auto;
  padding: 12px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 12px;
  background: rgba(248, 250, 255, 0.86);
}

.task-prompt-dialog__content pre {
  margin: 0;
  color: var(--text-strong);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.8rem;
  line-height: 1.7;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.task-prompt-dialog__content p {
  display: grid;
  min-height: 132px;
  place-items: center;
  color: var(--text-muted);
  font-size: 0.86rem;
  font-weight: 760;
}

.task-prompt-dialog__content-empty {
  background: rgba(255, 255, 255, 0.66);
}

.task-prompt-dialog-fade-enter-active,
.task-prompt-dialog-fade-leave-active {
  transition: opacity 160ms ease;
}

.task-prompt-dialog-fade-enter-active .task-prompt-dialog__panel,
.task-prompt-dialog-fade-leave-active .task-prompt-dialog__panel {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.task-prompt-dialog-fade-enter-from,
.task-prompt-dialog-fade-leave-to {
  opacity: 0;
}

.task-prompt-dialog-fade-enter-from .task-prompt-dialog__panel,
.task-prompt-dialog-fade-leave-to .task-prompt-dialog__panel {
  transform: translateY(8px) scale(0.985);
}

.jd-button__pause {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-left: 3px solid currentColor;
  border-right: 3px solid currentColor;
}

@media (max-width: 1080px) {
  .task-detail-grid-primary,
  .task-detail-grid-secondary {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .task-result-preview-with-references {
    grid-template-columns: 1fr;
  }

  .task-reference-panel {
    border-right: 0;
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  }

  .task-reference-stack {
    display: flex;
    justify-content: flex-start;
    min-height: 112px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 4px 26px 16px 4px;
  }

  .task-reference-card {
    flex: 0 0 86px;
    width: 86px;
    margin-top: 0;
    margin-left: -18px;
  }

  .task-reference-card:first-child {
    margin-left: 0;
  }

  .task-result-preview__actions {
    left: 10px;
    right: 10px;
    justify-content: flex-end;
  }

  .detail-overview {
    grid-template-columns: 1fr;
  }

  .detail-trace-summary {
    align-items: flex-start;
  }

  .detail-traces__item {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .detail-traces__time {
    padding-top: 0;
  }

  .detail-actions {
    flex-direction: column;
  }

  .detail-actions .jd-button {
    justify-content: center;
  }

  .task-prompt-dialog {
    padding: 14px;
  }

  .task-prompt-dialog__panel {
    max-height: calc(100vh - 28px);
    padding: 14px;
  }

  .task-prompt-dialog__content {
    max-height: min(62vh, 480px);
  }
}
</style>
