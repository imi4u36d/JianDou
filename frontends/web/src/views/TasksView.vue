<template>
  <section class="tasks-view" :class="{ 'tasks-view-detail-active': selectedTaskId }">
    <aside class="tasks-list-panel">
      <label class="tasks-search-field" aria-label="搜索任务">
        <svg class="tasks-search-field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input v-model="searchText" type="search" placeholder="搜索任务" />
        <button
          v-if="searchText"
          class="tasks-search-field__clear"
          type="button"
          @click="searchText = ''"
          aria-label="清除搜索"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        </button>
      </label>

      <div class="tasks-filter-strip" aria-label="任务筛选">
        <button
          v-for="item in statusFilterOptions"
          :key="item.value"
          type="button"
          class="tasks-filter-chip"
          :class="{ 'tasks-filter-chip-active': statusFilter === item.value }"
          @click="statusFilter = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <label class="tasks-sort-field" aria-label="任务排序">
        <AppSelect v-model="sortMode" :options="sortModeOptions" variant="toolbar" compact />
      </label>

      <div v-if="loading" class="tasks-loading">加载中</div>

      <div v-else-if="filteredTasks.length === 0" class="tasks-empty-board">
        <h3>{{ isFilterActive ? "没有匹配任务" : "暂无任务" }}</h3>
        <div class="tasks-empty-board__actions">
          <button v-if="isFilterActive" class="jd-button jd-button--warning" type="button" @click="clearFilters">清空筛选</button>
          <RouterLink to="/workspace" class="jd-button jd-button--secondary">返回工作台</RouterLink>
        </div>
      </div>

      <div v-else class="task-list">
        <article
          v-for="task in sortedFilteredTasks"
          :key="task.id"
          class="task-list__item"
          :class="{ 'task-list__item-active': task.id === selectedTaskId }"
        >
          <button
            type="button"
            class="task-list__main-button"
            :aria-label="`查看任务 ${task.title || '未命名任务'}`"
            @click="handleSelectTask(task)"
          >
            <span class="task-list__type-badge" :class="`task-list__type-badge-${normalizedTaskType(task)}`" aria-hidden="true">
              <img v-if="taskThumbnailUrl(task)" :src="taskThumbnailUrl(task)" alt="" />
              <AppIcon v-else :name="taskTypeIcon(task)" size="sm" />
            </span>
            <span class="task-list__main">
              <span class="task-list__title-row">
                <span
                  class="task-list__title"
                  :class="{ 'task-list__title-scrollable': isScrollableTaskTitle(task.title) }"
                  :title="task.title || '未命名任务'"
                >
                  <span class="task-list__title-text">{{ task.title || "未命名任务" }}</span>
                </span>
                <span class="task-list__meta">
                  <span class="task-list__meta-tag">{{ taskTypeLabel(task) }}</span>
                  <span class="task-list__status" :class="`task-list__status-${taskStatusTone(task.status)}`">{{ formatTaskStatus(task.status) }}</span>
                  <time class="task-list__meta-tag" :datetime="task.updatedAt || task.createdAt || undefined">{{ formatCompactDateTime(task.updatedAt || task.createdAt) }}</time>
                </span>
              </span>
              <span class="task-list__progress" aria-hidden="true"><i :style="{ width: `${taskProgress(task)}%` }"></i></span>
            </span>
          </button>
          <span class="task-list__side">
            <span class="task-list__side-actions">
              <button
                v-if="task.status === 'FAILED'"
                class="task-list__retry"
                type="button"
                :disabled="managingTaskId === task.id"
                aria-label="重试任务"
                title="重试"
                @click.stop="handleRetry(task)"
              >
                <IconRefresh size="xs" />
              </button>
              <button
                class="task-list__delete"
                type="button"
                :disabled="managingTaskId === task.id"
                aria-label="删除任务"
                title="删除"
                @click.stop="handleDelete(task)"
              >
                <IconDelete size="xs" />
              </button>
            </span>
            <strong>{{ taskProgress(task) }}%</strong>
          </span>
        </article>
      </div>
    </aside>

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
          <button class="task-detail-close-button" type="button" aria-label="关闭详情" title="关闭" @click="clearSelectedTask">
            <IconClose size="sm" />
          </button>
        </header>

        <div class="detail-actions" aria-label="任务操作">
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

        <div class="detail-stage-line" aria-label="任务阶段">
          <div v-for="stage in selectedTaskStages" :key="stage.key" class="detail-stage-line__item" :class="`detail-stage-line__item-${stage.state}`">
            <span class="detail-stage-line__dot" :class="stageStateClass(stage.state)" aria-hidden="true"></span>
            <span class="detail-stage-line__copy">
              <strong>{{ stage.label }}</strong>
              <small>{{ stage.stateLabel }}</small>
            </span>
          </div>
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
            <div class="task-result-preview">
              <img v-if="selectedTaskThumbnailUrl" :src="selectedTaskThumbnailUrl" alt="任务结果预览" />
              <div v-else>生成中</div>
            </div>
            <div class="detail-overview">
              <div class="detail-overview__row detail-overview__row-progress">
                <span>进度</span>
                <div class="detail-overview__progress">
                  <div class="detail-overview__progress-fill" :style="{ width: `${selectedTaskJoinProgressPercent}%` }"></div>
                </div>
                <strong>{{ selectedTaskJoinProgressPercent }}%</strong>
              </div>
              <div class="detail-overview__row"><span>参考图</span><strong>{{ selectedReferenceImageCount }} 张</strong></div>
              <div class="detail-overview__row"><span>实例</span><strong :title="selectedTaskWorkerLabel">{{ selectedTaskShortWorkerLabel }}</strong></div>
              <div class="detail-overview__row"><span>种子</span><strong>{{ selectedTaskSeedLabel }}</strong></div>
            </div>
          </section>

        </div>

        <section v-if="selectedTaskResultItems.length || selectedTaskMaterialItems.length" class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>结果和素材</h3>
            <RouterLink class="surface-chip detail-material-link" :to="materialLibraryLink">素材库</RouterLink>
          </div>
          <div class="detail-result-list">
            <button v-for="item in selectedTaskResultItems" :key="`result-${item.url}`" type="button" @click="handleDownloadMedia(item.url, item.title)">
              <IconDownload size="xs" />
              <span>{{ item.title }}</span>
            </button>
            <button v-for="item in selectedTaskMaterialItems" :key="`material-${item.url}`" type="button" @click="handleDownloadMedia(item.url, item.title)">
              <IconDownload size="xs" />
              <span>{{ item.title }}</span>
            </button>
          </div>
        </section>

        <div v-if="selectedTaskMonitoringRows.length || selectedTaskArtifactRows.length" class="task-detail-grid task-detail-grid-secondary">
          <section v-if="selectedTaskMonitoringRows.length" class="detail-section detail-section-card">
            <h3>监控</h3>
            <div class="detail-params">
              <div v-for="item in selectedTaskCompactMonitoringRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </section>

          <section v-if="selectedTaskArtifactRows.length" class="detail-section detail-section-card">
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

        <section class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>追踪</h3>
            <span class="surface-chip">{{ selectedTaskTrace.length }}</span>
          </div>
          <div class="detail-traces">
            <div v-if="selectedTaskTrace.length === 0" class="detail-traces__empty">暂无记录</div>
            <div v-for="event in selectedTaskTracePreview" :key="`${event.timestamp}-${event.event}-${event.stage}`" class="detail-traces__item">
              <p>{{ event.message }}</p>
              <small>[{{ event.stage }}] {{ formatDateTime(event.timestamp) }}</small>
            </div>
          </div>
        </section>

      </section>
    </main>

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

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
/**
 * 任务页面组件。
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import { usePolling } from "@/composables/usePolling";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, retryTask, terminateTask } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, inferMediaDownloadKind, type DownloadMediaKind } from "@/utils/download";
import AppSelect from "@/components/common/AppSelect.vue";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { AppIcon, IconChevronDown, IconClose, IconDelete, IconDownload, IconRefresh, IconText, IconWarning, type IconName } from "@/components/icons";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import {
  formatTaskSeed,
  getTaskRequestSnapshot,
} from "@/utils/task-request";
import { formatTaskStatus } from "@/utils/task";
import { formatDateTime as formatCompactDateTime, getTaskStatusMeta } from "@/utils/presentation";

const route = useRoute();
const router = useRouter();

type TaskSortMode = "status_desc" | "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc";

const DEFAULT_SORT_MODE: TaskSortMode = "created_desc";
const statusFilterOptions: Array<{ label: string; value: TaskStatus | "all" }> = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "RENDERING" },
  { label: "排队", value: "PENDING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "失败", value: "FAILED" },
];
const sortModeOptions: AppSelectOption[] = [
  { label: "最新创建", value: "created_desc" },
  { label: "智能优先", value: "status_desc" },
  { label: "最近更新", value: "updated_desc" },
  { label: "进度最高", value: "progress_desc" },
  { label: "有脚本优先", value: "semantic_desc" },
];
const STATUS_SORT_PRIORITY: Record<TaskStatus, number> = {
  RENDERING: 0,
  ANALYZING: 1,
  PLANNING: 2,
  PENDING: 3,
  PAUSED: 4,
  FAILED: 5,
  COMPLETED: 6,
};

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const sortMode = ref<TaskSortMode>(DEFAULT_SORT_MODE);
const managingTaskId = ref("");
const selectedTaskId = ref("");
const selectedTaskDetail = ref<TaskDetail | null>(null);
const selectedTaskTrace = ref<TaskTraceEvent[]>([]);
const selectedTaskLoading = ref(false);
const failureDetailsOpen = ref(false);
const promptDialogOpen = ref(false);
const promptCloseButtonRef = ref<HTMLButtonElement | null>(null);
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
let querySyncTimer: number | null = null;

const isFilterActive = computed(() => {
  return Boolean(searchText.value.trim() || statusFilter.value !== "all");
});

/**
 * 规范化查询值。
 * @param value 待处理的值
 */
function normalizeQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] == null ? "" : String(value[0]);
  }
  return value == null ? "" : String(value);
}

function toTimestamp(value?: string | null) {
  const timestamp = value ? new Date(value).getTime() : Number.NaN;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function compareByUpdatedAtDesc(
  left: Pick<TaskListItem, "id" | "createdAt" | "updatedAt">,
  right: Pick<TaskListItem, "id" | "createdAt" | "updatedAt">,
) {
  return toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt)
    || toTimestamp(right.createdAt) - toTimestamp(left.createdAt)
    || right.id.localeCompare(left.id);
}

function compareByCreatedAtDesc(
  left: Pick<TaskListItem, "id" | "createdAt" | "updatedAt">,
  right: Pick<TaskListItem, "id" | "createdAt" | "updatedAt">,
) {
  return toTimestamp(right.createdAt) - toTimestamp(left.createdAt)
    || toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt)
    || right.id.localeCompare(left.id);
}

function compareByStatus(left: TaskListItem, right: TaskListItem) {
  const priorityDiff = STATUS_SORT_PRIORITY[left.status] - STATUS_SORT_PRIORITY[right.status];
  if (priorityDiff !== 0) {
    return priorityDiff;
  }
  const createdDiff = compareByCreatedAtDesc(left, right);
  if (createdDiff !== 0) {
    return createdDiff;
  }
  return compareByUpdatedAtDesc(left, right);
}

function reconcileTaskList(currentTasks: TaskListItem[], nextTasks: TaskListItem[]) {
  const currentTaskMap = new Map(currentTasks.map((task) => [task.id, task]));
  return nextTasks.map((task) => {
    const currentTask = currentTaskMap.get(task.id);
    if (!currentTask) {
      return task;
    }
    Object.assign(currentTask, task);
    return currentTask;
  });
}

/**
 * 应用路由筛选条件。
 */
function applyRouteFilters() {
  searchText.value = normalizeQueryValue(route.query.q);

  const nextStatus = normalizeQueryValue(route.query.status);
  statusFilter.value = ["PENDING", "PAUSED", "ANALYZING", "PLANNING", "RENDERING", "COMPLETED", "FAILED"].includes(nextStatus)
    ? (nextStatus as TaskStatus)
    : "all";

  const nextSort = normalizeQueryValue(route.query.sort);
  sortMode.value = ["status_desc", "updated_desc", "created_desc", "progress_desc", "semantic_desc"].includes(nextSort)
    ? (nextSort as typeof sortMode.value)
    : DEFAULT_SORT_MODE;
  const selected = normalizeQueryValue(route.query.selected) || normalizeQueryValue(route.query.taskId);
  selectedTaskId.value = selected.trim();
}

const selectedTaskSummary = computed(() => {
  if (!selectedTaskId.value) {
    return null;
  }
  return tasks.value.find((task) => task.id === selectedTaskId.value) ?? null;
});

const selectedTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);

const selectedTaskActionTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);

const selectedTaskTypeLabel = computed(() => taskTypeLabel(selectedTask.value));

const selectedTaskStageLabel = computed(() => {
  if (selectedTaskDetail.value) {
    return formatTaskStatus(selectedTaskDetail.value.status);
  }
  if (selectedTaskSummary.value) {
    return formatTaskStatus(selectedTaskSummary.value.status);
  }
  return "等待更新";
});

const selectedTaskRequestSnapshot = computed(() => getTaskRequestSnapshot(selectedTaskDetail.value));

const selectedTaskPromptText = computed(() => {
  return firstNonBlank(
    selectedTaskDetail.value?.creativePrompt,
    selectedTaskRequestSnapshot.value.creativePrompt,
  );
});

const selectedTaskHeaderAspectRatio = computed(() => {
  const task = selectedTask.value;
  const snapshotAspectRatio = selectedTaskRequestSnapshot.value.aspectRatio;
  return String(snapshotAspectRatio || task?.aspectRatio || "").trim() || "未设置";
});

const selectedReferenceImageCount = computed(() => {
  const snapshotCount = listValue(selectedTaskDetail.value?.requestSnapshot?.referenceImageUrls).length;
  const contextCount = listValue(selectedTaskDetail.value?.executionContext?.referenceImageUrls).length;
  const sourceCount = selectedTaskDetail.value?.sourceAssetCount ?? selectedTaskSummary.value?.sourceAssetCount ?? 0;
  return Math.max(snapshotCount, contextCount, sourceCount);
});

const selectedTaskSeedLabel = computed(() => {
  const detailSeed = selectedTaskDetail.value?.taskSeed;
  if (typeof detailSeed === "number" && Number.isFinite(detailSeed)) {
    return String(Math.trunc(detailSeed));
  }
  const summarySeed = selectedTaskSummary.value?.taskSeed;
  if (typeof summarySeed === "number" && Number.isFinite(summarySeed)) {
    return String(Math.trunc(summarySeed));
  }
  return formatTaskSeed(selectedTaskRequestSnapshot.value);
});

const selectedTaskJoinProgressPercent = computed(() => {
  const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status;
  if (status === "COMPLETED") {
    return 100;
  }
  const progress = selectedTaskDetail.value?.progress ?? selectedTaskSummary.value?.progress ?? 0;
  return Math.max(0, Math.min(100, Math.round(progress)));
});

const selectedTaskMonitoringRows = computed(() => {
  const monitoring = selectedTaskDetail.value?.monitoring;
  if (!monitoring) {
    return [];
  }
  return [
    { label: "当前阶段", value: formatMonitoringValue(monitoring.currentStage) },
    { label: "尝试状态", value: formatMonitoringValue(monitoring.activeAttemptStatus) },
    { label: "恢复阶段", value: formatMonitoringValue(monitoring.resumeFromStage) },
    { label: "恢复镜头", value: formatMonitoringValue(monitoring.resumeFromClipIndex) },
    { label: "计划镜头数", value: formatMonitoringValue(monitoring.plannedClipCount) },
    { label: "已生成镜头数", value: formatMonitoringValue(monitoring.renderedClipCount) },
    { label: "连续完成镜头", value: formatMonitoringValue(monitoring.contiguousRenderedClipCount) },
    { label: "最新片段", value: formatMonitoringValue(monitoring.latestRenderedClipIndex) },
  ].filter((item) => item.value !== "暂无");
});

const selectedTaskWorkerLabel = computed(() => formatMonitoringValue(selectedTaskDetail.value?.monitoring?.activeWorkerInstanceId));
const selectedTaskShortWorkerLabel = computed(() => compactIdentifier(selectedTaskWorkerLabel.value, 10));
const selectedTaskCompactMonitoringRows = computed(() => selectedTaskMonitoringRows.value.slice(0, 5));
const selectedTaskJoinLabel = computed(() => {
  const monitoring = selectedTaskDetail.value?.monitoring;
  if (!monitoring) {
    return "暂无";
  }
  return formatMonitoringValue(monitoring.latestJoinName || monitoring.latestJoinClipIndex);
});
const selectedTaskFailureReason = computed(() => {
  return selectedTaskDetail.value?.failureReason || selectedTaskSummary.value?.failureReason || "";
});
const selectedTaskFailureContext = computed(() => {
  return taskFailureContext(selectedTaskDetail.value ?? selectedTaskSummary.value);
});

const selectedTaskThumbnailUrl = computed(() => taskThumbnailUrl(selectedTaskDetail.value ?? selectedTaskSummary.value));

const selectedTaskResultItems = computed(() => {
  const items: Array<{ title: string; url: string }> = [];
  const detail = selectedTaskDetail.value;
  if (!detail) {
    return items;
  }
  for (const output of detail.outputs ?? []) {
    const url = firstNonBlank(output.downloadUrl, output.previewUrl);
    if (url) {
      items.push({ title: output.title || `结果 #${output.clipIndex || items.length + 1}`, url });
    }
  }
  const latestJoinUrl = detail.monitoring?.latestJoinOutputUrl;
  if (latestJoinUrl && !items.some((item) => item.url === latestJoinUrl)) {
    items.push({ title: detail.monitoring?.latestJoinName || "最新拼接结果", url: latestJoinUrl });
  }
  const latestVideoUrl = detail.monitoring?.latestVideoOutputUrl;
  if (latestVideoUrl && !items.some((item) => item.url === latestVideoUrl)) {
    items.push({ title: "最新视频结果", url: latestVideoUrl });
  }
  return items;
});

const selectedTaskMaterialItems = computed(() => {
  const detail = selectedTaskDetail.value;
  if (!detail) {
    return [];
  }
  const rows: Array<{ title: string; url: string }> = [];
  for (const material of detail.materials ?? []) {
    const url = firstNonBlank(material.publicUrl, material.fileUrl);
    if (url) {
      rows.push({ title: material.title || material.id || "任务素材", url });
    }
  }
  if (detail.source?.fileUrl) {
    rows.push({ title: detail.source.originalFileName || "来源素材", url: detail.source.fileUrl });
  }
  for (const source of detail.sourceAssets ?? []) {
    if (source.fileUrl && !rows.some((item) => item.url === source.fileUrl)) {
      rows.push({ title: source.originalFileName || "来源素材", url: source.fileUrl });
    }
  }
  return rows;
});

const selectedTaskTracePreview = computed(() => selectedTaskTrace.value.slice(0, 16));

const materialLibraryLink = computed(() => {
  const assetType = selectedTaskDetail.value?.requestSnapshot?.assetType;
  return assetType ? `/materials?assetType=${encodeURIComponent(assetType)}` : "/materials";
});

const selectedTaskArtifactDirectories = computed(() => {
  return selectedTaskDetail.value?.artifactDirectories ?? selectedTaskDetail.value?.monitoring?.artifactDirectories ?? null;
});

const selectedTaskArtifactDirectoryHint = computed(() => {
  const artifactDirectories = selectedTaskArtifactDirectories.value;
  if (!artifactDirectories?.baseRelativeDir) {
    return "等待任务创建";
  }
  return artifactDirectories.baseRelativeDir;
});

const selectedTaskShortArtifactDirectoryHint = computed(() => compactPath(selectedTaskArtifactDirectoryHint.value));

const selectedTaskArtifactRows = computed(() => {
  const artifactDirectories = selectedTaskArtifactDirectories.value;
  if (!artifactDirectories) {
    return [];
  }
  return [
    { label: "存储根目录", value: formatMonitoringValue(artifactDirectories.storageRoot) },
    { label: "任务基目录", value: formatMonitoringValue(artifactDirectories.baseAbsoluteDir || artifactDirectories.baseRelativeDir) },
    { label: "运行目录", value: formatMonitoringValue(artifactDirectories.runningAbsoluteDir || artifactDirectories.runningRelativeDir) },
    { label: "拼接目录", value: formatMonitoringValue(artifactDirectories.joinedAbsoluteDir || artifactDirectories.joinedRelativeDir) },
    { label: "脚本文件", value: formatMonitoringValue(artifactDirectories.storyboardFileName) },
    { label: "首帧命名", value: formatMonitoringValue(artifactDirectories.firstFramePattern) },
    { label: "尾帧命名", value: formatMonitoringValue(artifactDirectories.lastFramePattern) },
    { label: "片段命名", value: formatMonitoringValue(artifactDirectories.clipPattern) },
    { label: "拼接命名", value: formatMonitoringValue(artifactDirectories.joinPattern) },
  ].filter((item) => item.value !== "暂无");
});

const selectedTaskCompactArtifactRows = computed(() => selectedTaskArtifactRows.value.slice(0, 5));

const selectedTaskStages = computed(() => {
  const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status ?? "PENDING";
  const taskType = normalizedTaskType(selectedTask.value);
  if (taskType !== "video_generation") {
    return buildImageTaskStages(status, taskType);
  }
  return buildVideoTaskStages(status);
});

const taskStageStateLabels: Record<TaskStageState, string> = {
  pending: "等待",
  active: "进行中",
  paused: "已暂停",
  done: "已完成",
  failed: "失败",
};

type TaskStageState = "pending" | "active" | "paused" | "done" | "failed";

interface TaskStageDisplayItem {
  key: string;
  label: string;
  state: TaskStageState;
  stateLabel: string;
}

function withTaskStageLabels(items: Array<Omit<TaskStageDisplayItem, "stateLabel">>): TaskStageDisplayItem[] {
  return items.map((item) => ({ ...item, stateLabel: taskStageStateLabels[item.state] }));
}

function buildVideoTaskStages(status: TaskStatus): TaskStageDisplayItem[] {
  const stageOrder: TaskStatus[] = ["ANALYZING", "PLANNING", "RENDERING", "COMPLETED"];
  const pausedAtRender = status === "PAUSED";
  const currentIndex = pausedAtRender ? 2 : stageOrder.indexOf(status);
  const items = [
    { key: "ANALYZING", label: "素材分析", state: currentIndex > 0 ? "done" : currentIndex === 0 ? "active" : "pending" },
    { key: "PLANNING", label: "任务编排", state: currentIndex > 1 ? "done" : currentIndex === 1 ? "active" : "pending" },
    { key: "RENDERING", label: "视频生成", state: pausedAtRender ? "paused" : currentIndex > 2 ? "done" : currentIndex === 2 ? "active" : "pending" },
    { key: "COMPLETED", label: "任务完成", state: status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : "pending" },
  ] as Array<Omit<TaskStageDisplayItem, "stateLabel">>;
  return withTaskStageLabels(items);
}

function buildImageTaskStages(status: TaskStatus, taskType: string): TaskStageDisplayItem[] {
  const renderLabel = taskType === "character_sheet" ? "三视图生成" : "图片生成";
  const submitState: TaskStageState = ["RENDERING", "COMPLETED", "FAILED"].includes(status) ? "done" : status === "PAUSED" ? "paused" : "active";
  const renderState: TaskStageState =
    status === "COMPLETED" ? "done" :
    status === "FAILED" ? "failed" :
    status === "PAUSED" ? "paused" :
    status === "RENDERING" ? "active" :
    "pending";
  const completeState: TaskStageState = status === "COMPLETED" ? "done" : "pending";
  return withTaskStageLabels([
    { key: "PENDING", label: "提交任务", state: submitState },
    { key: "RENDERING", label: renderLabel, state: renderState },
    { key: "COMPLETED", label: "生成完成", state: completeState },
  ]);
}

const filteredTasks = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  // 搜索和状态过滤放在前端完成，保证输入联动时不额外触发接口请求。
  return tasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [task.title, task.sourceFileName ?? "", task.aspectRatio ?? ""]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });
});

const sortedFilteredTasks = computed(() => {
  const items = [...filteredTasks.value];
  switch (sortMode.value) {
    case "status_desc":
      return items.sort(compareByStatus);
    case "created_desc":
      return items.sort(compareByCreatedAtDesc);
    case "updated_desc":
      return items.sort(compareByUpdatedAtDesc);
    case "progress_desc":
      return items.sort((left, right) => (right.progress ?? 0) - (left.progress ?? 0));
    case "semantic_desc":
      return items.sort((left, right) => Number(Boolean(right.hasTimedTranscript || right.hasTranscript)) - Number(Boolean(left.hasTimedTranscript || left.hasTranscript)));
    default:
      return items.sort(compareByUpdatedAtDesc);
  }
});

async function loadTasks() {
  const authenticated = await requireAuth({
    title: "登录后查看任务",
    message: "任务管理只展示你的个人任务，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    tasks.value = [];
    messageApi.error("登录后可查看任务管理");
    loading.value = false;
    return;
  }
  loading.value = tasks.value.length === 0;
  try {
    // 将筛选保留在前端本地，避免输入和视图切换时额外触发请求。
    const nextTasks = (await fetchTasks({
      sort: sortMode.value,
    })) ?? [];
    tasks.value = reconcileTaskList(tasks.value, nextTasks);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "加载任务列表失败");
  } finally {
    loading.value = false;
  }
}

async function loadSelectedTaskDetails(options: { silent?: boolean } = {}) {
  if (!selectedTaskId.value) {
    selectedTaskDetail.value = null;
    selectedTaskTrace.value = [];
    return;
  }
  if (!options.silent) {
    selectedTaskLoading.value = true;
  }
  try {
    const [detail, trace] = await Promise.all([
      fetchTask(selectedTaskId.value),
      fetchTaskTrace(selectedTaskId.value, 120),
    ]);
    selectedTaskDetail.value = detail;
    // 详情面板优先显示最新事件，便于定位当前卡住的阶段。
    selectedTaskTrace.value = [...trace].reverse();
  } catch (error) {
    if (!options.silent) {
      messageApi.error(error instanceof Error ? error.message : "任务详情加载失败");
    }
  } finally {
    if (!options.silent) {
      selectedTaskLoading.value = false;
    }
  }
}

async function refreshSelectedTask() {
  await loadSelectedTaskDetails();
}

/**
 * 处理写入查询。
 */
function writeQuery() {
  const query: Record<string, string> = {};
  if (searchText.value.trim()) {
    query.q = searchText.value.trim();
  }
  if (statusFilter.value !== "all") {
    query.status = statusFilter.value;
  }
  if (sortMode.value !== DEFAULT_SORT_MODE) {
    query.sort = sortMode.value;
  }
  if (selectedTaskId.value) {
    query.selected = selectedTaskId.value;
  }

  const currentQuery = route.query;
  const nextQuery = query;
  const sameQuery =
    (normalizeQueryValue(currentQuery.q) || "") === (nextQuery.q || "") &&
    (normalizeQueryValue(currentQuery.status) || "") === (nextQuery.status || "") &&
    (normalizeQueryValue(currentQuery.sort) || "") === (nextQuery.sort || "") &&
    ((normalizeQueryValue(currentQuery.selected) || normalizeQueryValue(currentQuery.taskId) || "") === (nextQuery.selected || ""));

  if (!sameQuery) {
    router.replace({ query: nextQuery });
  }
}

/**
 * 处理调度写入查询。
 */
function scheduleWriteQuery() {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
  }
  querySyncTimer = window.setTimeout(() => {
    querySyncTimer = null;
    writeQuery();
  }, 160);
}

/**
 * 处理清空筛选条件。
 */
function clearFilters() {
  searchText.value = "";
  statusFilter.value = "all";
  sortMode.value = DEFAULT_SORT_MODE;
}

function clearSelectedTask() {
  selectedTaskId.value = "";
  selectedTaskDetail.value = null;
  selectedTaskTrace.value = [];
  promptDialogOpen.value = false;
  writeQuery();
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") {
    return;
  }
  if (promptDialogOpen.value) {
    closePromptDialog();
    return;
  }
  if (selectedTaskId.value) {
    clearSelectedTask();
  }
}

async function openPromptDialog() {
  promptDialogOpen.value = true;
  await nextTick();
  promptCloseButtonRef.value?.focus({ preventScroll: true });
}

function closePromptDialog() {
  promptDialogOpen.value = false;
}

/**
 * 处理处理Select任务。
 * @param task 要处理的任务对象
 */
function handleSelectTask(task: TaskListItem) {
  selectedTaskId.value = task.id;
  writeQuery();
  void loadSelectedTaskDetails();
}

async function handleRetry(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "任务重试会重新加入队列，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  managingTaskId.value = task.id;
  try {
    await retryTask(task.id);
    await Promise.all([
      loadTasks(),
      task.id === selectedTaskId.value ? loadSelectedTaskDetails() : Promise.resolve(),
    ]);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "重试任务失败");
  } finally {
    managingTaskId.value = "";
  }
}

async function handlePause(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  managingTaskId.value = task.id;
  try {
    await pauseTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "暂停任务失败");
  } finally {
    managingTaskId.value = "";
  }
}

async function handleContinueTask(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  managingTaskId.value = task.id;
  try {
    await continueTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "继续任务失败");
  } finally {
    managingTaskId.value = "";
  }
}

async function handleTerminate(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  const ok = await requestConfirm({
    title: "终止任务",
    message: `任务会变为失败状态，可再删除或重试：${task.title || "未命名任务"}`,
    confirmText: "终止",
  });
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  try {
    await terminateTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "终止任务失败");
  } finally {
    managingTaskId.value = "";
  }
}

async function handleDelete(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "任务删除后无法恢复，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  const ok = await requestConfirm({
    title: "删除任务",
    message: `删除后无法恢复：${task.title || "未命名任务"}`,
    confirmText: "删除",
  });
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  try {
    await deleteTask(task.id);
    tasks.value = tasks.value.filter((t) => t.id !== task.id);
    if (selectedTaskId.value === task.id) {
      clearSelectedTask();
    }
    messageApi.success("任务已删除");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "删除任务失败");
  } finally {
    managingTaskId.value = "";
  }
}

async function handleDownloadMedia(url: string, title: string, mediaType?: DownloadMediaKind) {
  try {
    const resolvedMediaType = mediaType ?? inferMediaDownloadKind(url);
    const result = await downloadMedia({ url, title, mediaType: resolvedMediaType });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

/**
 * 格式化日期时间。
 * @param value 待处理的值
 */
function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) {
    return value;
  }
  return new Date(timestamp).toLocaleString();
}

function taskStatusTone(status: TaskStatus) {
  return getTaskStatusMeta(status).tone;
}

/**
 * 格式化监控值。
 * @param value 待处理的值
 */
function formatMonitoringValue(value: unknown) {
  if (value == null) {
    return "暂无";
  }
  if (typeof value === "number") {
    return value > 0 ? String(value) : "暂无";
  }
  const text = String(value).trim();
  return text ? text : "暂无";
}

function compactIdentifier(value: string, keep = 8) {
  const text = String(value ?? "").trim();
  if (!text || text === "暂无") {
    return text || "暂无";
  }
  if (text.length <= keep + 2) {
    return text;
  }
  return `#${text.slice(-keep)}`;
}

function compactPath(value: string) {
  const text = String(value ?? "").trim();
  if (!text || text === "等待任务创建" || text.length <= 28) {
    return text || "等待任务创建";
  }
  const parts = text.split(/[\\/]/).filter(Boolean);
  if (parts.length >= 2) {
    return `.../${parts.slice(-2).join("/")}`;
  }
  return `...${text.slice(-24)}`;
}

function taskFailureContext(task?: Pick<TaskListItem, "failureStage" | "failureClipIndex"> | null) {
  if (!task) {
    return "";
  }
  const parts: string[] = [];
  if (task.failureStage) {
    parts.push(`阶段 ${task.failureStage}`);
  }
  if (typeof task.failureClipIndex === "number" && task.failureClipIndex > 0) {
    parts.push(`镜头 #${task.failureClipIndex}`);
  }
  return parts.join(" · ");
}

function taskProgress(task?: Pick<TaskListItem, "progress" | "status"> | null) {
  if (!task) {
    return 0;
  }
  if (task.status === "COMPLETED") {
    return 100;
  }
  return Math.max(0, Math.min(100, Math.round(task.progress ?? 0)));
}

function normalizedTaskType(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null) {
  return String(task?.requestSnapshot?.taskType || task?.taskType || "video_generation").trim() || "video_generation";
}

function taskTypeLabel(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null) {
  switch (normalizedTaskType(task)) {
    case "image_generation":
      return "文生图";
    case "image_to_image":
      return "图生图";
    case "character_sheet":
      return "角色三视图";
    case "video_generation":
      return "视频生成";
    default:
      return "生成任务";
  }
}

function taskTypeIcon(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): IconName {
  switch (normalizedTaskType(task)) {
    case "image_generation":
    case "image_to_image":
      return "image";
    case "character_sheet":
      return "character";
    case "video_generation":
      return "video";
    default:
      return "task";
  }
}

function isScrollableTaskTitle(title?: string | null) {
  return (title || "未命名任务").trim().length > 12;
}

function firstNonBlank(...values: Array<string | null | undefined>) {
  for (const value of values) {
    const normalized = String(value ?? "").trim();
    if (normalized) {
      return normalized;
    }
  }
  return "";
}

function listValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function taskThumbnailUrl(task?: (TaskListItem | TaskDetail) | null) {
  const detail = task && "outputs" in task ? task : null;
  if (detail) {
    const material = detail.materials?.find((item) => firstNonBlank(item.thumbnailUrl, item.previewUrl, item.fileUrl));
    if (material) {
      return firstNonBlank(material.thumbnailUrl, material.previewUrl, material.fileUrl);
    }
    const output = detail.outputs?.find((item) => firstNonBlank(item.thumbnailUrl, item.previewUrl, item.downloadUrl));
    if (output) {
      return firstNonBlank(output.thumbnailUrl, output.previewUrl, output.downloadUrl);
    }
    const source = detail.sourceAssets?.find((item) => firstNonBlank(item.thumbnailUrl, item.fileUrl));
    if (source) {
      return firstNonBlank(source.thumbnailUrl, source.fileUrl);
    }
    return firstNonBlank(
      detail.source?.fileUrl,
    );
  }
  if (task?.thumbnailUrl) {
    return task.thumbnailUrl;
  }
  const selectedDetailForTask = task?.id && selectedTaskDetail.value?.id === task.id ? selectedTaskDetail.value : null;
  if (selectedDetailForTask) {
    return taskThumbnailUrl(selectedDetailForTask);
  }
  return "";
}

/**
 * 处理阶段状态样式类。
 * @param state 状态值
 */
function stageStateClass(state: "pending" | "active" | "paused" | "done" | "failed") {
  switch (state) {
    case "done":
      return "task-stage-row--done";
    case "active":
      return "task-stage-row--active";
    case "paused":
      return "task-stage-row--paused";
    case "failed":
      return "task-stage-row--failed";
    default:
      return "task-stage-row--pending";
  }
}

const { start } = usePolling(async () => {
  await loadTasks();
  await loadSelectedTaskDetails({ silent: true });
}, 5000);

watch(
  () => route.query,
  () => {
    applyRouteFilters();
    void loadSelectedTaskDetails();
  },
  { immediate: true, deep: true }
);

watch([searchText, statusFilter, sortMode], () => {
  scheduleWriteQuery();
});

watch(selectedTaskId, () => {
  failureDetailsOpen.value = false;
});

onMounted(async () => {
  window.addEventListener("keydown", handleWindowKeydown);
  await start();
});

onUnmounted(() => {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
    querySyncTimer = null;
  }
  window.removeEventListener("keydown", handleWindowKeydown);
});

</script>

<style scoped>
.tasks-view {
  height: 100%;
  min-height: 0;
  background: var(--bg-base);
  color: var(--text-strong);
  padding: 18px 22px 18px 18px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(var(--tasks-list-column-width, 320px), var(--tasks-list-column-width, 360px)) minmax(0, 1fr);
  align-content: stretch;
  gap: 22px;
}

.tasks-list-panel,
.task-detail-panel {
  min-height: 0;
  overflow: auto;
}

.tasks-list-panel {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 0 4px 0 0;
}

.task-detail-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 14px;
  overflow: auto;
}

.tasks-search-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.55);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.tasks-search-field:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(255, 255, 255, 0.8);
}

.tasks-search-field__icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-muted);
  transition: color 180ms ease;
}

.tasks-search-field:focus-within .tasks-search-field__icon {
  color: var(--accent-indigo);
}

.tasks-search-field input {
  width: 100%;
  min-height: 36px;
  border: 0;
  outline: 0;
  box-shadow: none;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.86rem;
}

.tasks-search-field input:focus-visible {
  box-shadow: none;
}

.tasks-search-field input::placeholder {
  color: var(--text-muted);
}

.tasks-search-field__clear {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.tasks-search-field__clear:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.tasks-search-field__clear svg {
  width: 12px;
  height: 12px;
}

.tasks-filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 2px 0;
}

.tasks-filter-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-body);
  font-size: 0.78rem;
  font-weight: 780;
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.tasks-filter-chip:hover,
.tasks-filter-chip:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(79, 70, 229, 0.26);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.tasks-filter-chip-active {
  border-color: rgba(99, 102, 241, 0.2);
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.96), rgba(224, 231, 255, 0.92));
  color: var(--accent-blue);
  box-shadow: 0 10px 22px rgba(99, 102, 241, 0.08);
}

.tasks-sort-field {
  display: grid;
  gap: 0;
}

.tasks-sort-field :deep(.app-select),
.tasks-sort-field :deep(.app-select__trigger) {
  width: 100%;
}

.tasks-alert,
.tasks-loading,
.tasks-empty-board {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: transparent;
}

.tasks-empty-board {
  flex-direction: column;
  align-items: flex-start;
}

.tasks-empty-board__eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.72rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.tasks-empty-board h3 {
  margin: 0;
  font-size: 1.35rem;
  color: var(--text-strong);
}

.tasks-empty-board p {
  margin: 0;
  color: var(--text-body);
  max-width: 44rem;
  line-height: 1.7;
}

.tasks-empty-board__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.task-list {
  display: grid;
  gap: 4px;
}

.task-list__item {
  --task-title-max-width: clamp(7.5rem, 42%, 12.5rem);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 66px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--text-strong);
  transition:
    background 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.task-list__item-active {
  border-color: rgba(99, 102, 241, 0.18);
  background: linear-gradient(90deg, rgba(224, 231, 255, 0.9), rgba(238, 242, 255, 0.7));
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.06);
}

.task-list__item:hover {
  transform: translateY(-1px);
  border-color: rgba(79, 70, 229, 0.16);
  background: rgba(255, 255, 255, 0.72);
}

.task-list__main-button {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 48px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.task-list__main-button:focus-visible {
  outline: 2px solid rgba(79, 70, 229, 0.34);
  outline-offset: 5px;
  border-radius: 0;
}

.task-list__type-badge {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  overflow: hidden;
  border-radius: 9px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  color: var(--accent-indigo);
  font-size: 0.72rem;
  font-weight: 900;
}

.task-list__type-badge img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-list__type-badge-video_generation {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(79, 70, 229, 0.12));
  color: var(--accent-blue);
}

.task-list__type-badge-image_generation,
.task-list__type-badge-image_to_image {
  background: linear-gradient(135deg, rgba(139, 212, 80, 0.18), rgba(79, 70, 229, 0.12));
  color: #18916a;
}

.task-list__type-badge-character_sheet {
  background: linear-gradient(135deg, rgba(255, 107, 95, 0.14), rgba(99, 102, 241, 0.1));
  color: var(--accent-coral);
}

.task-list__main {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.task-list__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.task-list__title {
  display: block;
  width: var(--task-title-max-width);
  max-width: var(--task-title-max-width);
  min-width: 0;
  flex: 0 1 auto;
  font-size: 0.94rem;
  font-weight: 760;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-list__title-text {
  display: inline-block;
  min-width: 100%;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  will-change: transform;
}

.task-list__title-scrollable:hover .task-list__title-text {
  max-width: none;
  overflow: visible;
  animation: task-title-marquee 4.8s ease-in-out infinite alternate;
}

@keyframes task-title-marquee {
  0%,
  18% {
    transform: translateX(0);
  }

  82%,
  100% {
    transform: translateX(min(0px, calc(-100% + var(--task-title-max-width))));
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-list__title-scrollable:hover .task-list__title-text {
    animation: none;
    transform: none;
  }
}

.task-list__meta {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: nowrap;
  gap: 6px;
  align-items: center;
  min-width: 0;
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 720;
  overflow: hidden;
}

.task-list__meta-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  max-width: 8rem;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  line-height: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-list__meta time {
  max-width: 7.6rem;
  white-space: nowrap;
}

.task-list__status {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-muted);
  line-height: 1;
}

.task-list__status-success {
  background: rgba(35, 199, 120, 0.1);
  color: #16885a;
}

.task-list__status-warning {
  background: rgba(255, 190, 100, 0.16);
  color: #966128;
}

.task-list__status-info {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-blue);
}

.task-list__status-danger {
  background: rgba(229, 72, 101, 0.1);
  color: var(--accent-danger);
}

.task-list__progress {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
}

.task-list__progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue));
}

.task-list__side {
  display: grid;
  justify-items: end;
  align-self: stretch;
  min-width: 58px;
  gap: 6px;
}

.task-list__side > strong {
  align-self: end;
  color: var(--text-body);
  font-size: 0.78rem;
}

.task-list__side-actions {
  display: flex;
  gap: 4px;
  align-self: start;
}

.task-list__retry,
.task-list__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  font-size: 0.68rem;
  font-weight: 800;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
}

.task-list__retry :deep(svg),
.task-list__delete :deep(svg) {
  width: 15px;
  height: 15px;
}

.task-list__retry {
  background: rgba(229, 72, 101, 0.1);
  color: var(--accent-danger);
}

.task-list__retry:hover:not(:disabled),
.task-list__retry:focus-visible {
  border-color: rgba(255, 118, 150, 0.62);
  background: rgba(255, 118, 150, 0.1);
}

.task-list__delete {
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-muted);
}

.task-list__delete:hover:not(:disabled),
.task-list__delete:focus-visible {
  background: rgba(229, 72, 101, 0.1);
  color: var(--accent-danger);
}

.task-list__retry:disabled,
.task-list__delete:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.task-detail-content {
  display: grid;
  align-content: start;
  gap: 16px;
  min-height: 100%;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.task-detail-empty {
  display: grid;
  min-height: 100%;
  padding: 28px;
  place-content: center;
  justify-items: center;
  color: var(--text-muted);
  text-align: center;
}

.task-detail-empty h3,
.task-detail-empty p {
  margin: 0;
}

.task-detail-empty h3 {
  color: var(--text-muted);
  font-size: 1rem;
  font-weight: 760;
}

.task-detail-empty p {
  max-width: 30rem;
  color: var(--text-body);
  line-height: 1.7;
}

.task-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  position: sticky;
  top: 8px;
  z-index: 5;
  padding: 16px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(32px) saturate(1.8);
  box-shadow: var(--shadow-soft);
}

.task-detail-header h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-strong);
  letter-spacing: 0;
  line-height: 1.35;
}

.task-detail-header__meta {
  display: flex;
  flex-wrap: wrap;
  margin-top: 9px;
  gap: 7px;
  min-width: 0;
}

.task-detail-header__meta .surface-chip {
  max-width: min(100%, 280px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.surface-chip-loading {
  width: 30px;
  min-width: 30px;
  padding: 0;
  justify-content: center;
}

.surface-chip-loading :deep(svg) {
  width: 13px;
  height: 13px;
  animation: task-detail-spin 900ms linear infinite;
}

@keyframes task-detail-spin {
  to {
    transform: rotate(360deg);
  }
}

.task-detail-close-button {
  flex: 0 0 auto;
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

.task-detail-close-button:hover,
.task-detail-close-button:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.2);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.task-detail-close-button :deep(svg) {
  width: 16px;
  height: 16px;
}

.detail-stage-line {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
  gap: 6px;
  padding: 0 0 2px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.detail-stage-line__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  min-width: 0;
  padding: 6px 10px 6px 0;
  border: 1px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--text-body);
}

.detail-stage-line__item::after {
  content: "";
  position: absolute;
  left: 18px;
  right: 2px;
  top: 21px;
  height: 2px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  transform: translateX(10px);
  z-index: 0;
}

.detail-stage-line__item:last-child::after {
  display: none;
}

.detail-stage-line__item-done {
  color: var(--accent-indigo);
}

.detail-stage-line__item-active,
.detail-stage-line__item-paused {
  color: var(--accent-blue);
}

.detail-stage-line__item-failed {
  color: var(--accent-danger);
}

.detail-stage-line__dot {
  z-index: 1;
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  border-radius: 999px;
  position: relative;
  background: rgba(0, 0, 0, 0.06);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.92);
}

.detail-stage-line__dot::after {
  content: "";
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
}

.detail-stage-line__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.detail-stage-line__copy strong,
.detail-stage-line__copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-stage-line__copy strong {
  color: var(--text-strong);
  font-size: 0.78rem;
  font-weight: 780;
}

.detail-stage-line__copy small {
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 700;
}

.task-stage-row--done {
  background: var(--accent-indigo);
}

.task-stage-row--done::after,
.task-stage-row--active::after {
  background: #fff;
}

.task-stage-row--active {
  background: var(--accent-blue);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
  animation: task-stage-dot-breathe 1.8s ease-in-out infinite;
}

.task-stage-row--active::before {
  content: "";
  position: absolute;
  inset: -8px;
  border-radius: inherit;
  background: rgba(99, 102, 241, 0.18);
  opacity: 0;
  animation: task-stage-dot-pulse 1.8s ease-out infinite;
  pointer-events: none;
}

.task-stage-row--paused {
  background: linear-gradient(90deg, rgba(255, 190, 100, 0.6), rgba(0, 0, 0, 0.06));
}

.task-stage-row--failed {
  background: linear-gradient(90deg, rgba(255, 118, 150, 0.68), rgba(0, 0, 0, 0.06));
}

.task-stage-row--pending {
  background: rgba(0, 0, 0, 0.06);
}

@keyframes task-stage-dot-breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@keyframes task-stage-dot-pulse {
  0% {
    opacity: 0.55;
    transform: scale(0.55);
  }
  70%,
  100% {
    opacity: 0;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-stage-row--active,
  .task-stage-row--active::before {
    animation: none;
  }
}

.task-failure-card {
  display: grid;
  overflow: hidden;
  min-height: 46px;
  border: 1px solid rgba(229, 72, 101, 0.1);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 247, 248, 0.78), rgba(255, 255, 255, 0.72));
  color: var(--accent-danger);
}

.task-failure-card-open {
  grid-template-rows: auto auto;
  height: max-content;
  min-height: 0;
  overflow: hidden;
}

.task-failure-card__summary {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 46px;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.task-failure-card__icon {
  display: inline-grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 9px;
  background: rgba(229, 72, 101, 0.1);
  color: #bf2f48;
}

.task-failure-card__icon :deep(svg) {
  width: 15px;
  height: 15px;
}

.task-failure-card__summary strong {
  min-width: 0;
  overflow: hidden;
  color: #bf2f48;
  font-size: 0.84rem;
  font-weight: 780;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-failure-card__chevron {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: rgba(229, 72, 101, 0.08);
  color: rgba(191, 47, 72, 0.78);
  transition:
    transform 160ms ease,
    background 160ms ease;
}

.task-failure-card-open .task-failure-card__chevron {
  transform: rotate(180deg);
  background: rgba(229, 72, 101, 0.12);
}

.task-failure-card p {
  margin: 0;
  max-height: min(220px, 34vh);
  overflow: auto;
  padding: 0 12px 12px;
  color: #9a3447;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.76rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.task-failure-card-open p {
  max-height: min(220px, 34vh);
  min-height: 0;
}

.detail-section {
  display: grid;
  gap: 11px;
  min-width: 0;
}

.detail-section-card {
  padding: 14px 0 0;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.detail-section h3 {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 820;
  color: var(--text-strong);
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 30px;
}

.detail-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
  border-top: 0;
  padding-top: 0;
}

.detail-overview__row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 9px;
  min-height: 38px;
  align-items: center;
  padding: 7px 0;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
  color: var(--text-body);
}

.detail-overview__row strong {
  color: var(--text-strong);
}

.detail-overview__row-progress {
  grid-column: 1 / -1;
  grid-template-columns: auto 1fr auto;
  align-items: center;
}

.detail-overview__progress {
  height: 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.detail-overview__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-indigo) 0%, var(--accent-blue) 100%);
}

.detail-params {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 22px;
  border-top: 0;
}

.detail-params__row {
  display: grid;
  grid-template-columns: minmax(70px, 0.4fr) minmax(0, 1fr);
  gap: 10px;
  min-height: 38px;
  padding: 8px 0;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
}

.detail-params__row span,
.detail-params__row strong {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0;
  font-size: 0.82rem;
}

.detail-params__row span {
  color: var(--text-muted);
}

.detail-params__row strong {
  color: var(--text-strong);
  font-weight: 680;
  overflow-wrap: anywhere;
}

.task-detail-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1.18fr) minmax(300px, 0.82fr);
  gap: 22px;
}

.task-detail-grid-secondary {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
}

.task-detail-grid-primary {
  align-items: start;
  grid-template-columns: minmax(0, 1fr);
}

.task-detail-grid-primary > .detail-section-card,
.task-detail-grid-secondary > .detail-section-card:first-child {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.task-result-preview {
  display: grid;
  place-items: center;
  height: clamp(240px, 34vw, 410px);
  min-height: 190px;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background:
    linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(99, 102, 241, 0.08)),
    #eef2ff;
  color: var(--text-muted);
  font-weight: 760;
}

.task-result-preview img {
  width: 100%;
  height: 100%;
  min-height: 0;
  object-fit: contain;
}

.detail-result-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-result-list a,
.detail-result-list button,
.detail-material-link {
  text-decoration: none;
}

.detail-result-list a,
.detail-result-list button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  min-height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  background: rgba(243, 248, 255, 0.82);
  color: var(--accent-blue);
  font-size: 0.82rem;
  font-weight: 800;
  border: 1px solid rgba(99, 102, 241, 0.12);
  cursor: pointer;
}

.detail-result-list a:hover,
.detail-result-list button:hover {
  background: #eef2ff;
  border-color: rgba(79, 70, 229, 0.24);
}

.detail-result-list a :deep(svg),
.detail-result-list button :deep(svg) {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
}

.detail-result-list a span,
.detail-result-list button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-note-block {
  display: grid;
  gap: 8px;
  padding: 12px 0 0;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
}

.detail-note-block span {
  color: var(--text-muted);
  font-size: 0.74rem;
  letter-spacing: 0;
  text-transform: none;
}

.detail-note-block p {
  margin: 0;
  color: var(--text-body);
  line-height: 1.7;
  white-space: pre-wrap;
}

.detail-traces {
  display: grid;
  gap: 0;
  max-height: 260px;
  overflow: auto;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
}

.detail-traces__item,
.detail-traces__empty {
  position: relative;
  padding: 10px 10px 10px 30px;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
}

.detail-traces__item::before {
  content: "";
  position: absolute;
  left: 14px;
  top: 16px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-blue));
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.08);
}

.detail-traces__item p,
.detail-traces__item small {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.detail-traces__item p {
  color: var(--text-strong);
  font-size: 0.76rem;
  line-height: 1.55;
}

.detail-traces__item small {
  display: block;
  margin-top: 0.3rem;
  color: var(--text-muted);
  font-size: 0.68rem;
}

.detail-traces__empty {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 7px;
  margin: -6px 0 0;
  padding: 0 0 2px;
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
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 720;
  overflow: hidden;
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
  white-space: pre-wrap;
  overflow-wrap: anywhere;
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
  position: relative;
  display: inline-grid;
  place-items: center;
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
}

.jd-button__pause::before,
.jd-button__pause::after {
  content: "";
  position: absolute;
  top: 2px;
  bottom: 2px;
  width: 3px;
  border-radius: 999px;
  background: currentColor;
}

.jd-button__pause::before {
  left: 3px;
}

.jd-button__pause::after {
  right: 3px;
}

@media (max-width: 900px) {
  .tasks-view {
    grid-template-columns: 1fr;
    padding: 18px;
    overflow: auto;
  }

  .tasks-list-panel {
    padding: 0 0 18px;
    border-right: 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  .task-detail-empty,
  .task-detail-content {
    padding: 0 0 18px;
  }

  .task-detail-panel {
    padding: 14px;
  }
  .detail-actions {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-radius: 0;
  }

  .detail-actions .jd-button {
    width: 100%;
  }

  .detail-stage-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .detail-stage-line__item {
    min-width: 0;
  }

  .task-detail-grid {
    grid-template-columns: 1fr;
  }

  .tasks-view-detail-active {
    grid-template-rows: 1fr;
  }

  .tasks-view-detail-active .tasks-list-panel {
    display: none;
  }

  .tasks-view-detail-active .task-detail-panel {
    min-height: calc(100vh - 36px);
  }

  .tasks-view:not(.tasks-view-detail-active) .task-detail-panel {
    display: none;
  }
}

@media (max-width: 640px) {
  .tasks-view {
    padding: 14px;
  }

  .tasks-list-panel,
  .task-detail-panel,
  .task-detail-empty,
  .task-detail-content {
    padding: 0;
    border-radius: 0;
  }

  .detail-overview__row-progress {
    grid-template-columns: 1fr;
  }

  .detail-overview,
  .detail-params {
    grid-template-columns: 1fr;
  }

  .task-detail-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .detail-stage-line__item {
    min-height: 40px;
  }

  .detail-stage-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .task-failure-card p,
  .task-failure-card-open p {
    max-height: min(160px, 30vh);
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
