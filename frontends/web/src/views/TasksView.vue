<template>
  <section class="tasks-view" :class="{ 'tasks-view-detail-active': selectedTaskId }">
    <aside class="tasks-list-panel">
      <label class="tasks-search-field" aria-label="搜索任务">
        <div class="tasks-search-field__control">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input v-model="searchText" type="search" placeholder="标题、状态、类型" />
        </div>
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
          <button v-if="isFilterActive" class="btn-warning" type="button" @click="clearFilters">清空筛选</button>
          <RouterLink to="/workspace" class="btn-secondary">返回工作台</RouterLink>
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
              <span class="task-list__title">{{ task.title || "未命名任务" }}</span>
              <span class="task-list__meta">
                <span>{{ taskTypeLabel(task) }}</span>
                <span class="task-list__status" :class="`task-list__status-${taskStatusTone(task.status)}`">{{ formatTaskStatus(task.status) }}</span>
                <time :datetime="task.updatedAt || task.createdAt || undefined">{{ formatCompactDateTime(task.updatedAt || task.createdAt) }}</time>
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
              <span class="surface-chip" :title="selectedTaskId">{{ selectedTaskShortId }}</span>
            <span class="surface-chip">{{ selectedTaskStageLabel }}</span>
              <span v-if="selectedTaskLoading" class="surface-chip surface-chip-loading">
                <IconRefresh size="xs" />
              </span>
            </div>
          </div>
          <button class="task-detail-close-button" type="button" aria-label="关闭详情" title="关闭" @click="clearSelectedTask">
            <IconClose size="sm" />
          </button>
        </header>

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

          <section class="detail-section detail-section-card">
            <div class="detail-section__head">
              <h3>请求参数</h3>
              <span class="surface-chip">{{ selectedTaskDurationModeLabel }}</span>
            </div>
            <div class="detail-params">
              <div v-for="item in selectedTaskCompactParameterRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <div v-if="selectedTaskTranscriptPreview" class="detail-note-block">
              <span>Prompt</span>
              <p>{{ selectedTaskTranscriptPreview }}</p>
            </div>
          </section>
        </div>

        <section v-if="selectedTaskResultItems.length || selectedTaskMaterialItems.length" class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>结果和素材</h3>
            <RouterLink class="surface-chip detail-material-link" :to="materialLibraryLink">素材库</RouterLink>
          </div>
          <div class="detail-result-list">
            <a v-for="item in selectedTaskResultItems" :key="`result-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">
              <IconDownload size="xs" />
              <span>{{ item.title }}</span>
            </a>
            <a v-for="item in selectedTaskMaterialItems" :key="`material-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">
              <IconDownload size="xs" />
              <span>{{ item.title }}</span>
            </a>
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

        <div class="detail-actions">
          <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)" class="detail-action-btn" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handlePause(selectedTaskActionTask)">
            <span class="detail-action-btn__pause" aria-hidden="true"></span>
            暂停
          </button>
          <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)" class="detail-action-btn detail-action-btn-warning" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleTerminate(selectedTaskActionTask)">
            <IconWarning size="xs" />
            终止
          </button>
          <button v-if="selectedTaskActionTask?.status === 'PAUSED'" class="detail-action-btn detail-action-btn-primary" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleContinueTask(selectedTaskActionTask)">
            <IconRefresh size="xs" />
            继续
          </button>
          <button class="detail-action-btn" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
            <IconRefresh size="xs" />
            刷新
          </button>
          <button v-if="selectedTaskActionTask" class="detail-action-btn detail-action-btn-danger" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleDelete(selectedTaskActionTask)">
            <IconDelete size="xs" />
            删除
          </button>
        </div>
      </section>
    </main>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
/**
 * 任务页面组件。
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import { usePolling } from "@/composables/usePolling";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, retryTask, terminateTask } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import AppSelect from "@/components/common/AppSelect.vue";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { AppIcon, IconChevronDown, IconClose, IconDelete, IconDownload, IconRefresh, IconWarning, type IconName } from "@/components/icons";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import {
  formatTaskDurationMode,
  formatTaskModelValue,
  formatTaskOutputCount,
  formatTaskRequestedDuration,
  formatTaskResolvedDuration,
  formatTaskSeed,
  formatTaskStopBeforeVideoGeneration,
  formatTaskTranscriptSummary,
  getTaskRequestSnapshot,
  previewTaskTranscript,
} from "@/utils/task-request";
import { formatTaskStatus } from "@/utils/task";
import { formatDateTime as formatCompactDateTime, getTaskStatusMeta } from "@/utils/presentation";

const route = useRoute();
const router = useRouter();

type TaskSortMode = "status_desc" | "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc";

const DEFAULT_SORT_MODE: TaskSortMode = "status_desc";
const statusFilterOptions: Array<{ label: string; value: TaskStatus | "all" }> = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "RENDERING" },
  { label: "排队", value: "PENDING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "失败", value: "FAILED" },
];
const sortModeOptions: AppSelectOption[] = [
  { label: "智能优先", value: "status_desc" },
  { label: "最近更新", value: "updated_desc" },
  { label: "最新创建", value: "created_desc" },
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

function compareByUpdatedAtDesc(left: Pick<TaskListItem, "updatedAt">, right: Pick<TaskListItem, "updatedAt">) {
  return toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt);
}

function compareByCreatedAtDesc(left: Pick<TaskListItem, "createdAt">, right: Pick<TaskListItem, "createdAt">) {
  return toTimestamp(right.createdAt) - toTimestamp(left.createdAt);
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

const selectedTaskShortId = computed(() => compactIdentifier(selectedTaskId.value, 8));

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

const selectedTaskDurationModeLabel = computed(() => formatTaskDurationMode(selectedTaskRequestSnapshot.value));

const selectedTaskTranscriptPreview = computed(() => previewTaskTranscript(selectedTaskRequestSnapshot.value));

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

const selectedTaskCompactParameterRows = computed(() => {
  return selectedTaskParameterRows.value.slice(0, 6);
});

const selectedTaskJoinProgressPercent = computed(() => {
  const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status;
  if (status === "COMPLETED") {
    return 100;
  }
  const progress = selectedTaskDetail.value?.progress ?? selectedTaskSummary.value?.progress ?? 0;
  return Math.max(0, Math.min(100, Math.round(progress)));
});

const selectedTaskParameterRows = computed(() => {
  const task = selectedTaskDetail.value;
  if (!task) {
    return [];
  }
  const snapshot = selectedTaskRequestSnapshot.value;
  return [
    { label: "文本模型", value: formatTaskModelValue(snapshot.textAnalysisModel) },
    { label: "关键帧模型", value: formatTaskModelValue(snapshot.imageModel) },
    { label: "视频模型", value: formatTaskModelValue(snapshot.videoModel) },
    { label: "清晰度 / 画幅", value: formatTaskModelValue(snapshot.videoSize) },
    { label: "输出数量", value: formatTaskOutputCount(snapshot) },
    { label: "请求时长", value: formatTaskRequestedDuration(snapshot) },
    { label: "生效时长", value: formatTaskResolvedDuration(task) },
    { label: "任务种子", value: selectedTaskSeedLabel.value },
    { label: "提前停止视频生成", value: formatTaskStopBeforeVideoGeneration(snapshot) },
    { label: "文本输入", value: formatTaskTranscriptSummary(snapshot) },
    { label: "画幅比例", value: formatTaskModelValue(snapshot.aspectRatio || task.aspectRatio) },
  ];
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
    const url = firstNonBlank(output.previewUrl, output.downloadUrl);
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
    const url = firstNonBlank(material.previewUrl, material.fileUrl);
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
  writeQuery();
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && selectedTaskId.value) {
    clearSelectedTask();
  }
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
  display: grid;
  grid-template-columns: minmax(300px,380px) minmax(0,1fr);
  gap: 0;
  min-height: 100%;
  padding: 0;
  overflow: hidden;
  background: var(--bg-base);
}
.tasks-list-panel {
  display: flex; flex-direction: column; gap: 10px;
  padding: 20px 16px; border-right: 1px solid var(--border-subtle);
  background: var(--bg-surface); overflow-y: auto;
}
.tasks-search-field { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border-subtle); background: var(--bg-muted); }
.tasks-search-field svg { width: 15px; height: 15px; color: var(--text-muted); flex-shrink: 0; }
.tasks-search-field input { flex: 1; min-height: 28px; font-size: 13px; color: var(--text-primary); }
.tasks-search-field input::placeholder { color: var(--text-muted); }
.tasks-search-field__control { display: flex; align-items: center; gap: 8px; flex: 1; }
.tasks-filter-strip { display: flex; gap: 4px; flex-wrap: wrap; }
.tasks-filter-chip { padding: 5px 10px; border-radius: 999px; border: 1px solid var(--border-subtle); background: var(--bg-surface); color: var(--text-muted); font-size: 11px; font-weight: 600; cursor: pointer; transition: all 120ms ease; }
.tasks-filter-chip:hover { background: var(--bg-muted); color: var(--text-primary); }
.tasks-filter-chip-active { background: var(--bg-accent-soft); color: var(--accent-indigo); border-color: rgba(79,70,229,0.2); }
.tasks-sort-field { min-height: 32px; }
.tasks-loading, .tasks-empty-board { display: grid; place-items: center; min-height: 120px; padding: 20px; color: var(--text-muted); text-align: center; }
.tasks-empty-board h3 { margin: 0 0 12px; font-size: 14px; font-weight: 700; color: var(--text-secondary); }
.tasks-empty-board__actions { display: flex; gap: 8px; justify-content: center; }
.task-list { display: flex; flex-direction: column; gap: 4px; }
.task-list__item { display: flex; align-items: stretch; gap: 0; border-radius: 10px; border: 1px solid transparent; background: transparent; transition: all 120ms ease; }
.task-list__item:hover { background: var(--bg-muted); }
.task-list__item-active { background: var(--bg-accent-soft) !important; border-color: rgba(79,70,229,0.15); }
.task-list__main-button { flex: 1; display: flex; align-items: center; gap: 10px; min-height: 56px; padding: 8px 10px; border: 0; background: transparent; cursor: pointer; text-align: left; min-width: 0; }
.task-list__type-badge { display: grid; place-items: center; width: 32px; height: 32px; overflow: hidden; border-radius: 8px; background: var(--bg-muted); color: var(--text-secondary); flex-shrink: 0; }
.task-list__type-badge img { width: 100%; height: 100%; object-fit: cover; }
.task-list__type-badge-video_generation { background: rgba(79,70,229,0.1); color: var(--accent-indigo); }
.task-list__type-badge-image_generation, .task-list__type-badge-image_to_image { background: rgba(16,185,129,0.1); color: var(--accent-emerald); }
.task-list__type-badge-character_sheet { background: rgba(244,63,94,0.1); color: var(--accent-rose); }
.task-list__main { display: grid; gap: 4px; min-width: 0; flex: 1; }
.task-list__title { min-width: 0; font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-list__meta { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: center; color: var(--text-muted); font-size: 11px; font-weight: 500; }
.task-list__meta time { white-space: nowrap; }
.task-list__status { display: inline-flex; align-items: center; min-height: 20px; padding: 0 6px; border-radius: 999px; background: var(--bg-muted); color: var(--text-muted); font-size: 10px; font-weight: 700; }
.task-list__status-success { background: rgba(16,185,129,0.1); color: var(--accent-emerald); }
.task-list__status-warning { background: rgba(245,158,11,0.1); color: var(--accent-amber); }
.task-list__status-info { background: rgba(59,130,246,0.1); color: var(--accent-blue); }
.task-list__status-danger { background: rgba(244,63,94,0.1); color: var(--accent-rose); }
.task-list__progress { height: 3px; overflow: hidden; border-radius: 999px; background: var(--bg-muted); }
.task-list__progress i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue)); }
.task-list__side { display: grid; justify-items: end; align-self: stretch; min-width: 48px; gap: 4px; padding: 8px 8px 8px 0; }
.task-list__side > strong { align-self: end; color: var(--text-muted); font-size: 11px; font-weight: 700; }
.task-list__side-actions { display: flex; gap: 2px; align-self: start; }
.task-list__retry, .task-list__delete { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 6px; background: transparent; color: var(--text-muted); cursor: pointer; transition: all 120ms ease; }
.task-list__retry:hover:not(:disabled), .task-list__delete:hover:not(:disabled) { background: rgba(244,63,94,0.1); color: var(--accent-rose); }
.task-list__retry:disabled, .task-list__delete:disabled { cursor: not-allowed; opacity: 0.4; }
.task-detail-panel { padding: 20px 24px; overflow-y: auto; background: var(--bg-base); }
.task-detail-empty { display: grid; min-height: 100%; place-content: center; color: var(--text-muted); text-align: center; }
.task-detail-empty h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.task-detail-content { display: grid; align-content: start; gap: 16px; }
.task-detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; position: sticky; top: -14px; z-index: 5; padding: 2px 2px 12px; border-bottom: 1px solid var(--border-subtle); background: linear-gradient(180deg, var(--bg-base), rgba(244,245,247,0.8)); backdrop-filter: blur(12px); }
.task-detail-header h2 { margin: 0; font-size: 20px; font-weight: 800; color: var(--text-primary); line-height: 1.2; }
.task-detail-header__meta { display: flex; flex-wrap: wrap; margin-top: 8px; gap: 6px; }
.task-detail-header__meta .surface-chip { max-width: min(100%,280px); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-detail-close-button { display: inline-grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--bg-surface); color: var(--text-muted); cursor: pointer; }
.task-detail-close-button:hover { background: var(--bg-muted); color: var(--text-primary); }
.task-detail-close-button :deep(svg) { width: 16px; height: 16px; }
.surface-chip-loading { width: 30px; min-width: 30px; padding: 0; justify-content: center; }
.surface-chip-loading :deep(svg) { width: 13px; height: 13px; animation: task-detail-spin 900ms linear infinite; }
@keyframes task-detail-spin { to { transform: rotate(360deg); } }
.detail-stage-line { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 6px; }
.detail-stage-line__item { position: relative; display: inline-flex; align-items: center; gap: 8px; min-height: 36px; padding: 4px 8px 4px 0; color: var(--text-secondary); }
.detail-stage-line__item::after { content: ""; position: absolute; left: 16px; right: 2px; top: 18px; height: 2px; border-radius: 999px; background: var(--border-subtle); z-index: 0; }
.detail-stage-line__item:last-child::after { display: none; }
.detail-stage-line__item-done { color: var(--accent-emerald); }
.detail-stage-line__item-active, .detail-stage-line__item-paused { color: var(--accent-indigo); }
.detail-stage-line__item-failed { color: var(--accent-rose); }
.detail-stage-line__dot { z-index: 1; width: 14px; height: 14px; border-radius: 50%; background: var(--bg-muted); box-shadow: 0 0 0 3px var(--bg-base); }
.task-stage-row--done { background: var(--accent-indigo); }
.task-stage-row--active { background: var(--accent-blue); box-shadow: 0 0 0 4px rgba(79,70,229,0.12); }
.task-stage-row--paused { background: linear-gradient(90deg, rgba(245,158,11,0.6), var(--bg-muted)); }
.task-stage-row--failed { background: linear-gradient(90deg, rgba(244,63,94,0.6), var(--bg-muted)); }
.task-stage-row--pending { background: var(--bg-muted); }
.detail-stage-line__copy { display: grid; gap: 1px; min-width: 0; }
.detail-stage-line__copy strong { font-size: 11px; font-weight: 700; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.detail-stage-line__copy small { font-size: 10px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-failure-card { display: grid; min-height: 44px; border: 1px solid rgba(244,63,94,0.1); border-radius: 10px; background: rgba(244,63,94,0.04); color: var(--accent-rose); overflow: hidden; }
.task-failure-card-open { grid-template-rows: auto auto; height: max-content; min-height: 0; }
.task-failure-card__summary { display: grid; grid-template-columns: 26px minmax(0,1fr) auto; align-items: center; gap: 8px; width: 100%; min-height: 46px; padding: 0 12px; background: transparent; cursor: pointer; text-align: left; border: 0; color: inherit; }
.task-failure-card__icon { display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 6px; background: rgba(244,63,94,0.1); color: var(--accent-rose); }
.task-failure-card__icon :deep(svg) { width: 15px; height: 15px; }
.task-failure-card__summary strong { min-width: 0; overflow: hidden; color: var(--accent-rose); font-size: 13px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.task-failure-card__chevron { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 6px; background: rgba(244,63,94,0.08); color: rgba(244,63,94,0.78); transition: transform 160ms ease; }
.task-failure-card-open .task-failure-card__chevron { transform: rotate(180deg); }
.task-failure-card p { margin: 0; max-height: min(220px,34vh); overflow: auto; padding: 0 12px 12px; color: #9a3447; font-family: ui-monospace, monospace; font-size: 11px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.detail-section { display: grid; gap: 10px; min-width: 0; }
.detail-section-card { padding: 14px 0 0; border-top: 1px solid var(--border-subtle); }
.detail-section h3 { margin: 0; font-size: 13px; font-weight: 700; color: var(--text-primary); }
.detail-section__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 30px; }
.detail-overview { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 0 20px; }
.detail-overview__row { display: grid; grid-template-columns: 1fr auto; gap: 8px; min-height: 36px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 13px; }
.detail-overview__row strong { color: var(--text-primary); font-weight: 600; }
.detail-overview__row-progress { grid-column: 1 / -1; grid-template-columns: auto 1fr auto; }
.detail-overview__progress { height: 4px; border-radius: 999px; background: var(--bg-muted); overflow: hidden; }
.detail-overview__progress-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue)); }
.detail-params { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 0 20px; }
.detail-params__row { display: grid; grid-template-columns: minmax(60px,0.4fr) minmax(0,1fr); gap: 8px; min-height: 36px; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }
.detail-params__row span { color: var(--text-muted); display: flex; align-items: center; min-width: 0; }
.detail-params__row strong { color: var(--text-primary); font-weight: 600; overflow-wrap: anywhere; display: flex; align-items: center; min-width: 0; }
.task-detail-grid { display: grid; grid-template-columns: minmax(300px,1.2fr) minmax(260px,0.8fr); gap: 20px; }
.task-detail-grid-secondary { grid-template-columns: repeat(auto-fit, minmax(min(100%,260px), 1fr)); }
.task-detail-grid-primary { align-items: start; }
.task-result-preview { display: grid; place-items: center; height: clamp(200px,30vw,360px); min-height: 190px; overflow: hidden; border-radius: 14px; border: 1px solid var(--border-subtle); background: var(--bg-muted); color: var(--text-muted); font-weight: 600; }
.task-result-preview img { width: 100%; height: 100%; min-height: 0; object-fit: contain; }
.detail-result-list { display: flex; flex-wrap: wrap; gap: 6px; }
.detail-result-list a { display: inline-flex; align-items: center; gap: 5px; max-width: 100%; min-height: 32px; padding: 0 10px; border-radius: 8px; background: var(--bg-accent-soft); color: var(--accent-indigo); font-size: 12px; font-weight: 700; border: 1px solid rgba(79,70,229,0.12); text-decoration: none; }
.detail-result-list a:hover { background: rgba(79,70,229,0.12); border-color: rgba(79,70,229,0.2); }
.detail-result-list a :deep(svg) { flex: 0 0 auto; width: 14px; height: 14px; }
.detail-result-list a span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.detail-material-link { text-decoration: none; }
.detail-note-block { display: grid; gap: 6px; padding: 10px 0 0; border-top: 1px solid var(--border-subtle); }
.detail-note-block span { color: var(--text-muted); font-size: 11px; font-weight: 700; text-transform: uppercase; }
.detail-note-block p { margin: 0; color: var(--text-secondary); line-height: 1.7; font-size: 13px; white-space: pre-wrap; }
.detail-traces { display: grid; max-height: 240px; overflow: auto; border-top: 1px solid var(--border-subtle); }
.detail-traces__item { position: relative; padding: 8px 8px 8px 24px; border-bottom: 1px solid var(--border-subtle); }
.detail-traces__item::before { content: ""; position: absolute; left: 10px; top: 14px; width: 6px; height: 6px; border-radius: 50%; background: var(--accent-indigo); }
.detail-traces__item p, .detail-traces__item small { margin: 0; font-family: ui-monospace, monospace; }
.detail-traces__item p { color: var(--text-primary); font-size: 11px; line-height: 1.5; }
.detail-traces__item small { display: block; margin-top: 2px; color: var(--text-muted); font-size: 10px; }
.detail-traces__empty { padding: 10px; color: var(--text-muted); font-size: 12px; }
.detail-actions { position: sticky; bottom: 0; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; margin: 0; padding: 10px 0 0; border-top: 1px solid var(--border-subtle); background: linear-gradient(180deg, transparent, var(--bg-base) 28%); backdrop-filter: blur(14px); }
.detail-action-btn { display: inline-flex; align-items: center; justify-content: center; gap: 5px; min-height: 34px; padding: 0 12px; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--bg-surface); color: var(--text-secondary); font-size: 12px; font-weight: 700; cursor: pointer; transition: all 120ms ease; }
.detail-action-btn:hover:not(:disabled) { background: var(--bg-muted); color: var(--text-primary); }
.detail-action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.detail-action-btn span, .detail-action-btn :deep(svg) { display: inline-grid; place-items: center; width: 15px; height: 15px; flex: 0 0 auto; }
.detail-action-btn__pause { position: relative; }
.detail-action-btn__pause::before, .detail-action-btn__pause::after { content: ""; position: absolute; top: 2px; bottom: 2px; width: 3px; border-radius: 999px; background: currentColor; }
.detail-action-btn__pause::before { left: 3px; }
.detail-action-btn__pause::after { right: 3px; }
.detail-action-btn-primary { background: var(--bg-accent-soft); color: var(--accent-indigo); border-color: rgba(79,70,229,0.15); }
.detail-action-btn-warning { background: rgba(245,158,11,0.1); color: var(--accent-amber); border-color: rgba(245,158,11,0.15); }
.detail-action-btn-danger { background: rgba(244,63,94,0.08); color: var(--accent-rose); border-color: rgba(244,63,94,0.12); }
@media (max-width: 900px) {
  .tasks-view { grid-template-columns: 1fr; }
  .tasks-list-panel { padding: 0 0 18px; border-right: 0; border-bottom: 1px solid var(--border-subtle); background: transparent; }
  .task-detail-empty, .task-detail-content { padding: 0 0 18px; }
  .task-detail-panel { padding: 14px; }
  .detail-actions { margin: 0; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); border-radius: 0; }
  .detail-action-btn { width: 100%; }
  .detail-stage-line { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
  .task-detail-grid { grid-template-columns: 1fr; }
  .tasks-view-detail-active { grid-template-rows: 1fr; }
  .tasks-view-detail-active .tasks-list-panel { display: none; }
  .tasks-view-detail-active .task-detail-panel { min-height: calc(100vh - 36px); }
  .tasks-view:not(.tasks-view-detail-active) .task-detail-panel { display: none; }
}
@media (max-width: 640px) {
  .tasks-view { padding: 14px; }
  .tasks-list-panel, .task-detail-panel, .task-detail-empty, .task-detail-content { padding: 0; border-radius: 0; }
  .task-detail-panel { border: 0; background: transparent; box-shadow: none; backdrop-filter: none; }
  .detail-overview__row-progress { grid-template-columns: 1fr; }
  .detail-overview, .detail-params { grid-template-columns: 1fr; }
  .task-detail-header { display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: start; }
  .detail-stage-line__item { min-height: 40px; }
  .detail-stage-line { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 6px; }
  .task-failure-card p { max-height: min(160px,30vh); }
}
</style>
