<template>
  <section class="tasks-view">
    <aside
      class="tasks-list-panel"
      :class="{ 'tasks-list-panel-collapsed': listCollapsed }"
      :style="listCollapsed ? { '--tasks-list-column-width': '214px' } : undefined"
    >
      <div class="tasks-panel-header">
        <div>
          <p class="tasks-eyebrow">任务管理</p>
          <h2 class="tasks-title">工作台任务</h2>
        </div>
        <button
          class="tasks-collapse-toggle"
          type="button"
          :aria-expanded="!listCollapsed"
          :aria-label="listCollapsed ? '展开任务列表' : '收起任务列表'"
          @click="listCollapsed = !listCollapsed"
        >
          <span></span>
          <span></span>
        </button>
      </div>

      <template v-if="!listCollapsed">
        <label class="tasks-search-field">
          <span>搜索</span>
          <div class="tasks-search-field__control">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input v-model="searchText" type="search" placeholder="标题、状态、类型" />
          </div>
        </label>

        <div v-if="loading" class="tasks-loading">正在加载任务...</div>

        <div v-else-if="filteredTasks.length === 0" class="tasks-empty-board">
          <p class="tasks-empty-board__eyebrow">{{ isFilterActive ? "当前筛选无结果" : "暂无工作台任务" }}</p>
          <h3>{{ isFilterActive ? "没有匹配任务" : "提交生成后会在这里追踪" }}</h3>
          <p>{{ isFilterActive ? "可以清空搜索词或切换状态筛选后再试。" : "在工作台发起图片、三视图或视频生成后，会出现实时进度和结果记录。" }}</p>
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
            role="button"
            tabindex="0"
            :aria-label="`查看任务 ${task.title || '未命名任务'}`"
            @click="handleSelectTask(task)"
            @keydown="handleTaskItemKeydown(task, $event)"
          >
            <span class="task-list__thumb">
              <img v-if="taskThumbnailUrl(task)" :src="taskThumbnailUrl(task)" alt="" />
              <span v-else>{{ taskTypeShortLabel(task) }}</span>
            </span>
            <span class="task-list__main">
              <span class="task-list__title">{{ task.title || "未命名任务" }}</span>
              <span class="task-list__meta">
                <span>{{ taskTypeLabel(task) }}</span>
                <span>{{ formatTaskStatus(task.status) }}</span>
                <span>{{ formatDateTime(task.updatedAt || task.createdAt) }}</span>
              </span>
              <span class="task-list__progress" aria-hidden="true"><i :style="{ width: `${taskProgress(task)}%` }"></i></span>
            </span>
            <span class="task-list__side">
              <span class="task-list__side-actions">
                <button
                  v-if="task.status === 'FAILED'"
                  class="task-list__retry"
                  type="button"
                  :disabled="managingTaskId === task.id"
                  @click.stop="handleRetry(task)"
                >
                  重试
                </button>
                <button
                  class="task-list__delete"
                  type="button"
                  :disabled="managingTaskId === task.id"
                  @click.stop="handleDelete(task)"
                >
                  删除
                </button>
              </span>
              <strong>{{ taskProgress(task) }}%</strong>
            </span>
          </article>
        </div>
      </template>

      <div v-else class="tasks-collapsed-hint">
        <span>{{ filteredTasks.length }}</span>
        <small>任务</small>
      </div>
    </aside>

    <main class="task-detail-panel">
      <section v-if="!selectedTaskId" class="task-detail-empty">
        <p class="tasks-empty-board__eyebrow">任务追踪</p>
        <h3>选择一个任务查看进度和结果</h3>
        <p>这里会展示工作台生成请求的阶段、参数、素材入口、结果预览和最近追踪。</p>
      </section>

      <section v-else class="task-detail-content" aria-labelledby="task-detail-title">
        <header class="task-detail-header">
          <div>
            <p class="tasks-eyebrow">{{ selectedTaskTypeLabel }}</p>
            <h2 id="task-detail-title">{{ selectedTask?.title || "任务详情" }}</h2>
            <div class="task-detail-header__meta">
              <span class="surface-chip">{{ selectedTaskId }}</span>
              <span class="surface-chip">{{ selectedTaskStageLabel }}</span>
              <span v-if="selectedTaskLoading" class="surface-chip">加载中</span>
            </div>
          </div>
          <button class="btn-secondary btn-sm" type="button" @click="clearSelectedTask">取消选中</button>
        </header>

        <div class="detail-stage-line">
          <div v-for="stage in selectedTaskStages" :key="stage.key" class="detail-stage-line__item">
            <div class="detail-stage-line__bar" :class="stageStateClass(stage.state)"></div>
            <p>{{ stage.label }}</p>
          </div>
        </div>

        <div v-if="selectedTaskFailureReason" class="task-details-panel__error task-details-panel__error-block">
          <strong>{{ selectedTaskFailureContext || "失败原因" }}</strong>
          <p>{{ selectedTaskFailureReason }}</p>
        </div>

        <div class="task-detail-grid task-detail-grid-primary">
          <section class="detail-section detail-section-card detail-preview-section">
            <div class="detail-section__head">
              <h3>结果预览</h3>
              <span class="surface-chip">{{ selectedTaskJoinProgressPercent }}%</span>
            </div>
            <div class="task-result-preview">
              <img v-if="selectedTaskThumbnailUrl" :src="selectedTaskThumbnailUrl" alt="任务结果预览" />
              <div v-else>等待结果</div>
            </div>
            <div class="detail-overview">
              <div class="detail-overview__row detail-overview__row-progress">
                <span>任务进度</span>
                <div class="detail-overview__progress">
                  <div class="detail-overview__progress-fill" :style="{ width: `${selectedTaskJoinProgressPercent}%` }"></div>
                </div>
                <strong>{{ selectedTaskJoinProgressPercent }}%</strong>
              </div>
              <div class="detail-overview__row"><span>参考图</span><strong>{{ selectedReferenceImageCount }} 张</strong></div>
              <div class="detail-overview__row"><span>执行实例</span><strong>{{ selectedTaskWorkerLabel }}</strong></div>
              <div class="detail-overview__row"><span>种子</span><strong>{{ selectedTaskSeedLabel }}</strong></div>
            </div>
          </section>

          <section class="detail-section detail-section-card">
            <div class="detail-section__head">
              <h3>请求参数</h3>
              <span class="surface-chip">{{ selectedTaskDurationModeLabel }}</span>
            </div>
            <div class="detail-params">
              <div v-for="item in selectedTaskParameterRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <div v-if="selectedTaskTranscriptPreview" class="detail-note-block">
              <span>输入预览</span>
              <p>{{ selectedTaskTranscriptPreview }}</p>
            </div>
          </section>
        </div>

        <section v-if="selectedTaskResultItems.length || selectedTaskMaterialItems.length" class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>结果和素材</h3>
            <RouterLink class="surface-chip detail-material-link" :to="materialLibraryLink">素材库入口</RouterLink>
          </div>
          <div class="detail-result-list">
            <a v-for="item in selectedTaskResultItems" :key="`result-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            <a v-for="item in selectedTaskMaterialItems" :key="`material-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
          </div>
        </section>

        <div v-if="selectedTaskMonitoringRows.length || selectedTaskArtifactRows.length" class="task-detail-grid task-detail-grid-secondary">
          <section v-if="selectedTaskMonitoringRows.length" class="detail-section detail-section-card">
            <h3>运行监控</h3>
            <div class="detail-params">
              <div v-for="item in selectedTaskMonitoringRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </section>

          <section v-if="selectedTaskArtifactRows.length" class="detail-section detail-section-card">
            <div class="detail-section__head">
              <h3>产物目录</h3>
              <span class="surface-chip">{{ selectedTaskArtifactDirectoryHint }}</span>
            </div>
            <div class="detail-params">
              <div v-for="item in selectedTaskArtifactRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </section>
        </div>

        <section class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>最近追踪</h3>
            <span class="surface-chip">{{ selectedTaskTrace.length }}</span>
          </div>
          <div class="detail-traces">
            <div v-if="selectedTaskTrace.length === 0" class="detail-traces__empty">暂时还没有追踪记录。</div>
            <div v-for="event in selectedTaskTracePreview" :key="`${event.timestamp}-${event.event}-${event.stage}`" class="detail-traces__item">
              <p>{{ event.message }}</p>
              <small>[{{ event.stage }}] {{ formatDateTime(event.timestamp) }}</small>
            </div>
          </div>
        </section>

        <div class="detail-actions">
          <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)" class="btn-secondary btn-sm" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handlePause(selectedTaskActionTask)">暂停</button>
          <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)" class="btn-warning btn-sm" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleTerminate(selectedTaskActionTask)">终止</button>
          <button v-if="selectedTaskActionTask?.status === 'PAUSED'" class="btn-primary btn-sm" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleContinueTask(selectedTaskActionTask)">继续</button>
          <button class="btn-secondary btn-sm" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">刷新</button>
          <button v-if="selectedTaskActionTask" class="btn-danger btn-sm" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleDelete(selectedTaskActionTask)">删除任务</button>
        </div>
      </section>
    </main>
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
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, retryTask, terminateTask } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
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

const route = useRoute();
const router = useRouter();

type TaskSortMode = "status_desc" | "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc";

const DEFAULT_SORT_MODE: TaskSortMode = "status_desc";
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
const listCollapsed = ref(false);
const managingTaskId = ref("");
const selectedTaskId = ref("");
const selectedTaskDetail = ref<TaskDetail | null>(null);
const selectedTaskTrace = ref<TaskTraceEvent[]>([]);
const selectedTaskLoading = ref(false);
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
  listCollapsed.value = normalizeQueryValue(route.query.collapsed) === "1";

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
    const nextTasks = await fetchTasks({
      sort: sortMode.value,
    });
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
  if (listCollapsed.value) {
    query.collapsed = "1";
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
    (normalizeQueryValue(currentQuery.collapsed) || "") === (nextQuery.collapsed || "") &&
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

function handleTaskItemKeydown(task: TaskListItem, event: KeyboardEvent) {
  if (event.target !== event.currentTarget) {
    return;
  }
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }
  event.preventDefault();
  handleSelectTask(task);
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
  const ok = window.confirm(`确认终止任务"${task.title}"吗？终止后任务会变为失败状态，可再删除或重试。`);
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
  const ok = window.confirm(`确认删除任务"${task.title || '未命名任务'}"吗？删除后无法恢复。`);
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

function taskTypeShortLabel(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null) {
  switch (normalizedTaskType(task)) {
    case "image_generation":
      return "文";
    case "image_to_image":
      return "图";
    case "character_sheet":
      return "角";
    case "video_generation":
      return "视";
    default:
      return "任";
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

watch([searchText, statusFilter, sortMode, listCollapsed], () => {
  scheduleWriteQuery();
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
  background: #fff;
  color: var(--text-strong);
  padding: 18px 22px 18px 0;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(var(--tasks-list-column-width, 320px), var(--tasks-list-column-width, 410px)) minmax(0, 1fr);
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
  gap: 16px;
  padding: 26px 20px 18px 26px;
  border-right: 1px solid rgba(15, 20, 25, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.tasks-list-panel-collapsed {
  grid-template-rows: auto auto;
  align-content: start;
  min-width: 214px;
  padding: 20px 16px 18px 20px;
}

.task-detail-panel {
  display: grid;
}

.tasks-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.tasks-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.tasks-collapse-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 42px;
  height: 36px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 10px;
  background: #fff;
  color: var(--text-strong);
}

.tasks-collapse-toggle span {
  width: 10px;
  height: 16px;
  border: 2px solid currentColor;
  border-radius: 3px;
}

.tasks-collapse-toggle span:first-child {
  border-right-width: 1px;
}

.tasks-collapse-toggle span:last-child {
  border-left-width: 1px;
}

.tasks-search-field {
  display: grid;
  gap: 12px;
}

.tasks-search-field > span {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--text-strong);
}

.tasks-search-field__control {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  padding: 0 14px;
  border-radius: 14px;
  border: 0;
  background: #eef2f4;
}

.tasks-search-field__control svg {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
}

.tasks-search-field__control input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.95rem;
}

.tasks-search-field__control input::placeholder {
  color: #9aa5ad;
}

.tasks-alert,
.tasks-loading,
.tasks-empty-board {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
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

.tasks-collapsed-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: min(100%, 520px);
  padding: 12px 0;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
  color: var(--text-muted);
  font-size: 0.82rem;
}

.task-list {
  display: grid;
  gap: 0;
}

.task-list__item {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 82px;
  padding: 12px 0;
  border: 0;
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 0;
  background: transparent;
  text-align: left;
  color: var(--text-strong);
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease;
}

.task-list__item:focus-visible {
  outline: 2px solid rgba(124, 58, 237, 0.34);
  outline-offset: 3px;
}

.task-list__item-active {
  background: linear-gradient(90deg, rgba(124, 58, 237, 0.1), rgba(124, 58, 237, 0));
}

.task-list__item:hover {
  background: rgba(255, 255, 255, 0.58);
}

.task-list__thumb {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  overflow: hidden;
  border-radius: 14px;
  background: #eef8fb;
  color: var(--accent-cyan);
  font-size: 0.92rem;
  font-weight: 900;
}

.task-list__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-list__main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.task-list__title {
  min-width: 0;
  font-size: 0.94rem;
  font-weight: 760;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-list__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 720;
}

.task-list__progress {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(15, 20, 25, 0.08);
}

.task-list__progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--bg-accent);
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
  min-width: 42px;
  height: 26px;
  padding: 0 8px;
  border: 0;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 800;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
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
  background: rgba(15, 20, 25, 0.06);
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

.task-detail-empty,
.task-detail-content {
  display: grid;
  align-content: start;
  gap: 20px;
  min-height: 100%;
  padding: 30px 28px 24px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.task-detail-empty {
  place-content: center;
  justify-items: center;
  text-align: center;
}

.task-detail-empty h3,
.task-detail-empty p {
  margin: 0;
}

.task-detail-empty h3 {
  font-size: 1.4rem;
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
}

.tasks-eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.task-detail-header h2 {
  margin: 0;
  font-size: clamp(1.25rem, 2vw, 1.7rem);
  font-weight: 700;
  color: var(--text-strong);
}

.task-detail-header__meta {
  display: flex;
  flex-wrap: wrap;
  margin-top: 10px;
  gap: 8px;
}

.task-details-panel__empty,
.task-details-panel__error {
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(229, 72, 101, 0.07);
  color: var(--text-muted);
}

.task-details-panel__error {
  color: var(--accent-danger);
}

.task-details-panel__error-block {
  display: grid;
  gap: 6px;
  border-left: 3px solid rgba(229, 72, 101, 0.62);
}

.task-details-panel__error-block strong,
.task-details-panel__error-block p {
  margin: 0;
}

.detail-stage-line {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.detail-stage-line__item {
  display: grid;
  gap: 8px;
  justify-items: center;
  text-align: center;
}

.detail-stage-line__bar {
  width: 100%;
  height: 18px;
  border-radius: 999px;
  position: relative;
  background: rgba(15, 20, 25, 0.08);
}

.detail-stage-line__bar::after {
  content: "";
  position: absolute;
  inset: 3px auto 3px calc(50% - 6px);
  width: 12px;
  border-radius: 50%;
  background: rgba(15, 20, 25, 0.18);
}

.task-stage-row--done {
  background: var(--bg-accent);
}

.task-stage-row--done::after,
.task-stage-row--active::after {
  background: #fff;
}

.task-stage-row--active {
  background: var(--bg-accent);
}

.task-stage-row--paused {
  background: linear-gradient(90deg, rgba(255, 190, 100, 0.6), rgba(15, 20, 25, 0.06));
}

.task-stage-row--failed {
  background: linear-gradient(90deg, rgba(255, 118, 150, 0.68), rgba(15, 20, 25, 0.06));
}

.task-stage-row--pending {
  background: rgba(15, 20, 25, 0.08);
}

.detail-stage-line__item p {
  margin: 0;
  color: var(--text-body);
  font-size: 0.72rem;
  line-height: 1.35;
}

.detail-section {
  display: grid;
  gap: 12px;
}

.detail-section-card {
  padding: 20px 0;
  border: 0;
  border-radius: 0;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
  background: transparent;
}

.detail-section h3 {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-strong);
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 28px;
}

.detail-overview {
  display: grid;
  gap: 0;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
}

.detail-overview__row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  min-height: 40px;
  align-items: center;
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
  color: var(--text-body);
}

.detail-overview__row strong {
  color: var(--text-strong);
}

.detail-overview__row-progress {
  grid-template-columns: auto 1fr auto;
  align-items: center;
}

.detail-overview__progress {
  height: 6px;
  border-radius: 999px;
  background: rgba(15, 20, 25, 0.08);
  overflow: hidden;
}

.detail-overview__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #8f71ff 0%, #59d7ff 100%);
}

.detail-params {
  display: grid;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
  overflow: hidden;
}

.detail-params__row {
  display: grid;
  grid-template-columns: minmax(90px, 0.8fr) minmax(0, 1fr);
  min-height: 42px;
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
}

.detail-params__row span,
.detail-params__row strong {
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 0.82rem;
}

.detail-params__row span {
  color: var(--text-muted);
}

.detail-params__row strong {
  color: var(--text-strong);
  font-weight: 500;
}

.task-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.task-detail-grid-primary {
  align-items: start;
}

.task-detail-grid-primary > .detail-section-card,
.task-detail-grid-secondary > .detail-section-card:first-child {
  border-top: 0;
}

.task-result-preview {
  display: grid;
  place-items: center;
  min-height: 260px;
  overflow: hidden;
  border-radius: 12px;
  background: #eef2f4;
  color: var(--text-muted);
  font-weight: 760;
}

.task-result-preview img {
  width: 100%;
  height: 100%;
  min-height: 260px;
  object-fit: contain;
}

.detail-result-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.detail-result-list a,
.detail-material-link {
  text-decoration: none;
}

.detail-result-list a {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  color: var(--accent-cyan);
  font-size: 0.82rem;
  font-weight: 800;
  border-bottom: 1px solid rgba(124, 58, 237, 0.28);
}

.detail-note-block {
  display: grid;
  gap: 8px;
  padding: 12px 0 0;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
  background: transparent;
}

.detail-note-block span {
  color: var(--text-muted);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
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
  max-height: 360px;
  overflow: auto;
  border-top: 1px solid rgba(15, 20, 25, 0.08);
}

.detail-traces__item,
.detail-traces__empty {
  padding: 12px 0;
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 0;
  background: transparent;
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
  margin-top: 0.32rem;
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
  gap: 10px;
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
    border-bottom: 1px solid rgba(15, 20, 25, 0.08);
    background: transparent;
  }

  .task-detail-empty,
  .task-detail-content {
    padding: 0 0 18px;
  }

  .detail-stage-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .tasks-view {
    padding: 14px;
  }

  .tasks-list-panel,
  .task-detail-empty,
  .task-detail-content {
    padding: 0;
    border-radius: 0;
  }

  .detail-overview__row-progress {
    grid-template-columns: 1fr;
  }

  .task-detail-header {
    display: grid;
  }
}
</style>
