<template>
  <section class="tasks-view">
    <div class="tasks-layout">
      <div class="tasks-board">
        <div class="tasks-title-row">
          <h2 class="tasks-title">任务管理</h2>
          <span class="tasks-last-updated">最近刷新：{{ lastLoadedAt }}</span>
        </div>

        <div class="tasks-toolbar surface-panel">
          <label class="toolbar-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input v-model="searchText" type="search" placeholder="搜索任务、文件名或画幅" />
          </label>

          <div class="toolbar-pills">
            <button
              class="toolbar-pill"
              :class="{ 'toolbar-pill-active': statusFilter === 'PENDING' }"
              type="button"
              @click="statusFilter = statusFilter === 'PENDING' ? 'all' : 'PENDING'"
            >
              <span class="toolbar-pill__dot toolbar-pill__dot-pending"></span>
              待处理
            </button>
            <button
              class="toolbar-pill"
              :class="{ 'toolbar-pill-active': statusFilter === 'RENDERING' }"
              type="button"
              @click="statusFilter = statusFilter === 'RENDERING' ? 'all' : 'RENDERING'"
            >
              <span class="toolbar-pill__dot toolbar-pill__dot-rendering"></span>
              生成中
            </button>
            <label class="toolbar-select">
              <span class="toolbar-select__icon">↻</span>
              <select v-model="sortMode">
                <option value="updated_desc">按状态</option>
                <option value="created_desc">按创建时间</option>
                <option value="progress_desc">按进度</option>
                <option value="semantic_desc">按文本输入</option>
                <option value="effect_rating_desc">按评分</option>
              </select>
            </label>
            <button
              class="toolbar-pill"
              :class="{ 'toolbar-pill-active': statusFilter === 'COMPLETED' }"
              type="button"
              @click="statusFilter = statusFilter === 'COMPLETED' ? 'all' : 'COMPLETED'"
            >
              <span class="toolbar-pill__dot toolbar-pill__dot-completed"></span>
              已完成
            </button>
          </div>

          <div class="toolbar-actions">
            <button class="toolbar-icon" :class="{ 'toolbar-icon-active': viewMode === 'cards' }" type="button" @click="viewMode = 'cards'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="4" y="4" width="6" height="6" rx="1.4" />
                <rect x="14" y="4" width="6" height="6" rx="1.4" />
                <rect x="4" y="14" width="6" height="6" rx="1.4" />
                <rect x="14" y="14" width="6" height="6" rx="1.4" />
              </svg>
            </button>
            <button class="toolbar-icon" :class="{ 'toolbar-icon-active': viewMode === 'rows' }" type="button" @click="viewMode = 'rows'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 7h14" />
                <path d="M5 12h14" />
                <path d="M5 17h14" />
              </svg>
            </button>
            <button class="toolbar-icon" type="button" @click="clearFilters">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M4 7h16" />
                <path d="M7 12h10" />
                <path d="M10 17h4" />
              </svg>
            </button>
          </div>
        </div>

        <div v-if="errorMessage" class="surface-tile tasks-alert">
          <p>{{ errorMessage }}</p>
          <button class="btn-secondary btn-sm" type="button" @click="loadTasks">重新加载</button>
        </div>

        <div v-if="loading" class="surface-panel tasks-loading">
          正在加载任务面板...
        </div>

        <div v-else-if="filteredTasks.length === 0" class="surface-panel tasks-empty-board">
          <p class="tasks-empty-board__eyebrow">{{ isFilterActive ? "当前筛选无结果" : "任务工作台" }}</p>
          <h3>{{ isFilterActive ? "没有匹配的任务" : "创建你的第一个生成任务" }}</h3>
          <p>
            {{
              isFilterActive
                ? "可以清空搜索词，或切换状态筛选后再试。"
                : "任务创建后会出现在这里，你可以在同一个面板里查看进度、详情和追踪信息。"
            }}
          </p>
          <div class="tasks-empty-board__actions">
            <button v-if="isFilterActive" class="btn-warning" type="button" @click="clearFilters">清空筛选</button>
            <RouterLink v-else to="/tasks/new" class="btn-primary">新建任务</RouterLink>
            <RouterLink to="/generate" class="btn-secondary">打开生成器</RouterLink>
          </div>
        </div>

        <div v-else class="board-columns">
          <section v-for="column in boardColumns" :key="column.key" class="surface-panel board-column">
            <div class="board-column__head">
              <div>
                <h3>{{ column.title }}</h3>
              </div>
              <button class="board-column__more" type="button" @click="toggleGroup(column.key)">•••</button>
            </div>

            <div v-if="isGroupCollapsed(column.key)" class="board-column__collapsed">当前列已收起</div>
            <div v-else class="board-column__list">
              <button
                v-for="task in column.items"
                :key="task.id"
                type="button"
                class="board-task"
                :class="[
                  task.id === selectedTaskId ? 'board-task-active' : '',
                  boardTaskToneClass(task.status),
                ]"
                @click="handleSelectTask(task)"
              >
                <div class="board-task__media"></div>
                <div class="board-task__content">
                  <div class="board-task__head">
                    <h4>{{ task.title }}</h4>
                    <span class="board-task__menu">⋮</span>
                  </div>
                  <div class="board-task__progress">
                    <div class="board-task__progress-fill" :style="{ width: `${task.progress}%` }"></div>
                  </div>
                  <div class="board-task__meta">
                    <span>{{ task.aspectRatio || "9:16" }}</span>
                    <span>种子：{{ typeof task.taskSeed === "number" ? task.taskSeed : "--" }}</span>
                  </div>
                  <div class="board-task__footer">
                    <span>可用操作 {{ quickActionCount(task) }}</span>
                    <span class="board-task__rating">★ {{ typeof task.effectRating === "number" ? task.effectRating.toFixed(1) : "0.0" }}</span>
                  </div>
                </div>
              </button>
            </div>
          </section>
        </div>
      </div>

      <aside class="surface-panel task-details-panel">
        <div class="task-details-panel__head">
          <h2>任务详情</h2>
          <button class="task-details-panel__close" type="button" @click="clearSelectedTask">×</button>
        </div>

        <div v-if="!selectedTaskId" class="task-details-panel__empty">
          从左侧任务看板选择一个任务，即可查看详情、追踪记录和创建参数。
        </div>

        <template v-else>
          <div class="task-details-panel__title">
            <p>{{ selectedTaskDetail?.title || selectedTaskSummary?.title || "任务" }}</p>
            <strong>任务编号 · {{ selectedTaskDetail?.id || selectedTaskId }}</strong>
          </div>

          <div class="detail-stage-line">
            <div v-for="stage in selectedTaskStages" :key="stage.key" class="detail-stage-line__item">
              <div class="detail-stage-line__bar" :class="stageStateClass(stage.state)"></div>
              <p>{{ stage.label }}</p>
            </div>
          </div>

          <section class="detail-section">
            <h3>结果概览</h3>
            <div class="detail-overview">
              <div class="detail-overview__row">
                <span>执行实例</span>
                <strong>{{ selectedTaskWorkerLabel }}</strong>
              </div>
              <div class="detail-overview__row detail-overview__row-progress">
                <span>拼接进度</span>
                <div class="detail-overview__progress">
                  <div class="detail-overview__progress-fill" :style="{ width: `${selectedTaskJoinProgressPercent}%` }"></div>
                </div>
                <strong>{{ selectedTaskJoinProgressPercent }}%</strong>
              </div>
              <div class="detail-overview__row">
                <span>评分</span>
                <strong>★ {{ selectedTaskEffectRatingLabel }}</strong>
              </div>
              <div class="detail-overview__row">
                <span>种子</span>
                <strong>{{ selectedTaskSeedLabel }}</strong>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section__head">
              <h3>创建参数</h3>
              <span class="surface-chip">{{ selectedTaskDurationModeLabel }}</span>
            </div>
            <div class="detail-params">
              <div v-for="item in selectedTaskCompactParameterRows" :key="item.label" class="detail-params__row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section__head">
              <h3>最近追踪</h3>
              <span class="surface-chip">{{ selectedTaskTrace.length }}</span>
            </div>
            <div v-if="selectedTaskError" class="task-details-panel__error">{{ selectedTaskError }}</div>
            <div v-else class="detail-traces">
              <div v-if="selectedTaskTrace.length === 0" class="detail-traces__empty">暂时还没有追踪记录。</div>
              <div
                v-for="event in selectedTaskTrace.slice(0, 12)"
                :key="`${event.timestamp}-${event.event}-${event.stage}`"
                class="detail-traces__item"
              >
                <p>{{ event.message }}</p>
                <small>[{{ event.stage }}] {{ formatDateTime(event.timestamp) }}</small>
              </div>
            </div>
          </section>

          <div class="detail-actions">
            <button
              v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)"
              class="btn-secondary btn-sm"
              type="button"
              :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
              @click="handlePause(selectedTaskActionTask)"
            >
              暂停
            </button>
            <button
              v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)"
              class="btn-warning btn-sm"
              type="button"
              :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
              @click="handleTerminate(selectedTaskActionTask)"
            >
              终止
            </button>
            <button
              v-if="selectedTaskActionTask?.status === 'PAUSED'"
              class="btn-primary btn-sm"
              type="button"
              :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
              @click="handleContinueTask(selectedTaskActionTask)"
            >
              继续
            </button>
            <button class="btn-secondary btn-sm" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
              刷新
            </button>
          </div>
        </template>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 任务页面组件。
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, rateTaskEffect, retryTask, terminateTask } from "@/api/tasks";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import { usePolling } from "@/composables/usePolling";
import {
  formatTaskDurationMode,
  formatTaskEffectRating,
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
import { formatTaskStatus, getTaskLifecycleGroup, TASK_LIFECYCLE_GROUP_LABELS } from "@/utils/task";

const route = useRoute();
const router = useRouter();

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const lastLoadedAt = ref("尚未刷新");
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const sortMode = ref<"updated_desc" | "created_desc" | "progress_desc" | "semantic_desc" | "effect_rating_desc">("updated_desc");
const viewMode = ref<"rows" | "cards">("rows");
const managingTaskId = ref("");
const collapsedGroups = ref<Record<string, boolean>>({});
const selectedTaskId = ref("");
const selectedTaskDetail = ref<TaskDetail | null>(null);
const selectedTaskTrace = ref<TaskTraceEvent[]>([]);
const selectedTaskLoading = ref(false);
const selectedTaskError = ref("");
const selectedTaskRatingDraft = ref<number | null>(null);
const selectedTaskRatingNote = ref("");
const selectedTaskRatingSaving = ref(false);
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
  sortMode.value = ["updated_desc", "created_desc", "progress_desc", "semantic_desc", "effect_rating_desc"].includes(nextSort)
    ? (nextSort as typeof sortMode.value)
    : "updated_desc";

  const nextView = normalizeQueryValue(route.query.view);
  viewMode.value = nextView === "cards" ? "cards" : "rows";

  const selected = normalizeQueryValue(route.query.selected) || normalizeQueryValue(route.query.taskId);
  selectedTaskId.value = selected.trim();
}

const selectedTaskSummary = computed(() => {
  if (!selectedTaskId.value) {
    return null;
  }
  return tasks.value.find((task) => task.id === selectedTaskId.value) ?? null;
});

const selectedTaskActionTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);

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
const selectedTaskEffectRatingLabel = computed(() => {
  return formatTaskEffectRating(selectedTaskDetail.value?.effectRating ?? selectedTaskSummary.value?.effectRating);
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
    { label: "视觉模型", value: formatTaskModelValue(snapshot.visionModel) },
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
  const stageOrder: TaskStatus[] = ["ANALYZING", "PLANNING", "RENDERING", "COMPLETED"];
  const pausedAtRender = status === "PAUSED";
  const currentIndex = pausedAtRender ? 2 : stageOrder.indexOf(status);
  /**
   * 处理转为标签。
   * @param state 状态值
   */
  const toLabel = (state: "pending" | "active" | "paused" | "done" | "failed") => {
    switch (state) {
      case "done":
        return "已完成";
      case "active":
        return "进行中";
      case "paused":
        return "已暂停";
      case "failed":
        return "失败";
      default:
        return "等待";
    }
  };
  const items = [
    { key: "ANALYZING", label: "素材分析", state: currentIndex > 0 ? "done" : currentIndex === 0 ? "active" : "pending" },
    { key: "PLANNING", label: "任务编排", state: currentIndex > 1 ? "done" : currentIndex === 1 ? "active" : "pending" },
    { key: "RENDERING", label: "视频生成", state: pausedAtRender ? "paused" : currentIndex > 2 ? "done" : currentIndex === 2 ? "active" : "pending" },
    { key: "COMPLETED", label: "任务完成", state: status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : "pending" },
  ] as Array<{ key: string; label: string; state: "pending" | "active" | "paused" | "done" | "failed" }>;
  return items.map((item) => ({ ...item, stateLabel: toLabel(item.state) }));
});

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
    case "created_desc":
      return items.sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
    case "progress_desc":
      return items.sort((left, right) => (right.progress ?? 0) - (left.progress ?? 0));
    case "semantic_desc":
      return items.sort((left, right) => Number(Boolean(right.hasTimedTranscript || right.hasTranscript)) - Number(Boolean(left.hasTimedTranscript || left.hasTranscript)));
    case "effect_rating_desc":
      return items.sort((left, right) => {
        const ratingDiff = (right.effectRating ?? 0) - (left.effectRating ?? 0);
        if (ratingDiff !== 0) {
          return ratingDiff;
        }
        const ratedAtDiff = new Date(right.ratedAt || 0).getTime() - new Date(left.ratedAt || 0).getTime();
        if (ratedAtDiff !== 0) {
          return ratedAtDiff;
        }
        return new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime();
      });
    default:
      return items.sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime());
  }
});

const metrics = computed(() => {
  const total = tasks.value.length;
  const running = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "running").length;
  const completed = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "completed").length;
  const failed = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "failed").length;
  const semantic = tasks.value.filter((task) => task.hasTranscript).length;
  const timedSemantic = tasks.value.filter((task) => task.hasTimedTranscript).length;
  return { total, running, completed, failed, semantic, timedSemantic };
});

const groupedTasks = computed(() => {
  // 先排序再分组，保证同一生命周期分组内也维持统一的优先级顺序。
  const groups = [
    {
      key: "running",
      title: TASK_LIFECYCLE_GROUP_LABELS.running,
      description: "分析、编排和渲染中的任务会优先显示在这里。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "running")
    },
    {
      key: "paused",
      title: TASK_LIFECYCLE_GROUP_LABELS.paused,
      description: "已暂停的任务可继续生成，也可以直接删除。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "paused")
    },
    {
      key: "queued",
      title: TASK_LIFECYCLE_GROUP_LABELS.queued,
      description: "等待处理的任务，适合查看队列压力。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "queued")
    },
    {
      key: "completed",
      title: TASK_LIFECYCLE_GROUP_LABELS.completed,
      description: "已经完成渲染的素材，可以直接预览和下载。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "completed")
    },
    {
      key: "failed",
      title: TASK_LIFECYCLE_GROUP_LABELS.failed,
      description: "失败任务可直接重试或删除后重新创建。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "failed")
    }
  ];
  return groups.filter((group) => group.items.length > 0);
});

const boardColumns = computed(() => {
  const pendingStatuses: TaskStatus[] = ["PENDING", "PAUSED", "ANALYZING", "PLANNING"];
  return [
    {
      key: "pending",
      title: "待处理",
      items: sortedFilteredTasks.value.filter((task) => pendingStatuses.includes(task.status)),
    },
    {
      key: "rendering",
      title: "生成中",
      items: sortedFilteredTasks.value.filter((task) => task.status === "RENDERING"),
    },
    {
      key: "completed",
      title: "已结束",
      items: sortedFilteredTasks.value.filter((task) => ["COMPLETED", "FAILED"].includes(task.status)),
    },
  ];
});

async function loadTasks() {
  errorMessage.value = "";
  loading.value = tasks.value.length === 0;
  try {
    // 将筛选保留在前端本地，避免输入和视图切换时额外触发请求。
    tasks.value = await fetchTasks({
      sort: sortMode.value,
    });
    lastLoadedAt.value = new Date().toLocaleString();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载任务列表失败";
  } finally {
    loading.value = false;
  }
}

async function loadSelectedTaskDetails() {
  if (!selectedTaskId.value) {
    selectedTaskDetail.value = null;
    selectedTaskTrace.value = [];
    selectedTaskError.value = "";
    selectedTaskRatingDraft.value = null;
    selectedTaskRatingNote.value = "";
    return;
  }
  selectedTaskLoading.value = true;
  selectedTaskError.value = "";
  try {
    const [detail, trace] = await Promise.all([
      fetchTask(selectedTaskId.value),
      fetchTaskTrace(selectedTaskId.value, 120),
    ]);
    selectedTaskDetail.value = detail;
    // 详情面板优先显示最新事件，便于定位当前卡住的阶段。
    selectedTaskTrace.value = [...trace].reverse();
    selectedTaskRatingDraft.value = typeof detail.effectRating === "number" && detail.effectRating > 0 ? Math.trunc(detail.effectRating) : null;
    selectedTaskRatingNote.value = detail.effectRatingNote?.trim() || "";
  } catch (error) {
    selectedTaskError.value = error instanceof Error ? error.message : "任务详情加载失败";
  } finally {
    selectedTaskLoading.value = false;
  }
}

async function refreshSelectedTask() {
  await loadSelectedTaskDetails();
}

async function saveSelectedTaskRating() {
  if (!selectedTaskId.value || !selectedTaskRatingDraft.value) {
    return;
  }
  selectedTaskRatingSaving.value = true;
  selectedTaskError.value = "";
  try {
    await rateTaskEffect(selectedTaskId.value, {
      effectRating: selectedTaskRatingDraft.value,
      effectRatingNote: selectedTaskRatingNote.value.trim() || undefined,
    });
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    selectedTaskError.value = error instanceof Error ? error.message : "保存评分失败";
  } finally {
    selectedTaskRatingSaving.value = false;
  }
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
  if (sortMode.value !== "updated_desc") {
    query.sort = sortMode.value;
  }
  if (viewMode.value !== "rows") {
    query.view = viewMode.value;
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
    (normalizeQueryValue(currentQuery.view) || "") === (nextQuery.view || "") &&
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
  sortMode.value = "updated_desc";
}

function clearSelectedTask() {
  selectedTaskId.value = "";
  selectedTaskDetail.value = null;
  selectedTaskTrace.value = [];
  selectedTaskError.value = "";
  writeQuery();
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

/**
 * 检查是否分组折叠。
 * @param groupKey 分组Key值
 */
function isGroupCollapsed(groupKey: string) {
  return Boolean(collapsedGroups.value[groupKey]);
}

/**
 * 处理切换分组。
 * @param groupKey 分组Key值
 */
function toggleGroup(groupKey: string) {
  collapsedGroups.value = {
    ...collapsedGroups.value,
    [groupKey]: !collapsedGroups.value[groupKey]
  };
}

function quickActionCount(task: TaskListItem) {
  let count = 1;
  if (["PENDING", "ANALYZING", "PLANNING"].includes(task.status)) {
    count += 1;
  }
  if (["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(task.status)) {
    count += 1;
  }
  if (task.status === "FAILED" || task.status === "PAUSED") {
    count += 1;
  }
  return count;
}

function boardTaskToneClass(status: TaskStatus) {
  switch (status) {
    case "COMPLETED":
      return "board-task-tone-completed";
    case "FAILED":
      return "board-task-tone-failed";
    case "RENDERING":
      return "board-task-tone-rendering";
    default:
      return "board-task-tone-pending";
  }
}

async function handleRetry(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await retryTask(task.id);
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "任务重试失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handlePause(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await pauseTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "暂停任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleContinueTask(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await continueTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "继续任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleTerminate(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const ok = window.confirm(`确认终止任务“${task.title}”吗？终止后任务会变为失败状态，可再删除或重试。`);
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await terminateTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "终止任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleDelete(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const ok = window.confirm(`确认删除任务“${task.title}”吗？已生成的输出和日志也会一并清理。`);
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await deleteTask(task.id);
    if (selectedTaskId.value === task.id) {
      selectedTaskId.value = "";
      selectedTaskDetail.value = null;
      selectedTaskTrace.value = [];
      selectedTaskError.value = "";
      writeQuery();
    }
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除任务失败";
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
  await loadSelectedTaskDetails();
}, 5000);

watch(
  () => route.query,
  () => {
    applyRouteFilters();
    void loadSelectedTaskDetails();
  },
  { immediate: true, deep: true }
);

watch([searchText, statusFilter, sortMode, viewMode], () => {
  scheduleWriteQuery();
});

onMounted(async () => {
  await start();
});

onUnmounted(() => {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
    querySyncTimer = null;
  }
});

</script>

<style scoped>
.tasks-view {
  height: 100%;
  min-height: 0;
  color: var(--text-strong);
}

.tasks-layout {
  display: grid;
  gap: 0;
  height: 100%;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr) 310px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0 0 24px 24px;
  overflow: hidden;
}

.tasks-board {
  min-width: 0;
  min-height: 0;
  padding: 18px 18px 18px 24px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow: auto;
}

.tasks-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.tasks-title {
  margin: 0;
  font-family: "Sora", "Inter", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  background: linear-gradient(90deg, #c567ff 0%, #8a8fff 46%, #67caff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.tasks-last-updated {
  color: var(--text-muted);
  font-size: 0.72rem;
}

.tasks-toolbar {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1.2fr) minmax(0, 1.7fr) auto;
  align-items: center;
  padding: 14px;
  margin-bottom: 18px;
}

.toolbar-search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.toolbar-search svg {
  width: 18px;
  height: 18px;
  color: rgba(255, 255, 255, 0.46);
}

.toolbar-search input {
  width: 100%;
  border: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.86);
}

.toolbar-search input::placeholder {
  color: rgba(255, 255, 255, 0.34);
}

.toolbar-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.toolbar-pill,
.toolbar-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.8);
}

.toolbar-pill-active {
  border-color: rgba(145, 180, 255, 0.36);
  box-shadow: var(--shadow-glow);
}

.toolbar-pill__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.toolbar-pill__dot-pending {
  background: #ffcf74;
}

.toolbar-pill__dot-rendering {
  background: #8ea5ff;
}

.toolbar-pill__dot-completed {
  background: #63dc97;
}

.toolbar-select {
  padding-right: 10px;
}

.toolbar-select select {
  border: 0;
  background: transparent;
  color: inherit;
}

.toolbar-select__icon {
  color: rgba(255, 255, 255, 0.44);
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  justify-self: end;
}

.toolbar-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.7);
}

.toolbar-icon-active {
  color: rgba(255, 255, 255, 0.96);
  border-color: rgba(145, 180, 255, 0.32);
}

.toolbar-icon svg {
  width: 18px;
  height: 18px;
}

.tasks-alert,
.tasks-loading,
.tasks-empty-board {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px;
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
  color: rgba(255, 255, 255, 0.94);
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

.board-columns {
  display: grid;
  gap: 14px;
  min-height: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.board-column {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
  padding: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    rgba(18, 21, 28, 0.82);
}

.board-column__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.board-column__head h3 {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.94);
}

.board-column__more {
  color: rgba(255, 255, 255, 0.48);
}

.board-column__list {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
  overflow: auto;
}

.board-column__collapsed {
  color: var(--text-muted);
  font-size: 0.78rem;
}

.board-task {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
  padding: 10px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    rgba(255, 255, 255, 0.03);
  text-align: left;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.board-task:hover {
  transform: translateY(-1px);
}

.board-task-active {
  box-shadow: var(--shadow-glow);
}

.board-task-tone-pending {
  border-color: rgba(176, 92, 255, 0.34);
}

.board-task-tone-rendering {
  border-color: rgba(78, 219, 255, 0.34);
}

.board-task-tone-completed {
  border-color: rgba(99, 220, 151, 0.28);
}

.board-task-tone-failed {
  border-color: rgba(255, 118, 150, 0.28);
}

.board-task__media {
  border-radius: 10px;
  min-height: 96px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01)),
    radial-gradient(circle at 50% 28%, rgba(247, 223, 167, 0.22), transparent 34%),
    linear-gradient(135deg, rgba(52, 67, 84, 0.72), rgba(15, 18, 24, 0.96));
}

.board-task__content {
  min-width: 0;
  display: grid;
  gap: 9px;
}

.board-task__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.board-task__head h4 {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.3;
  color: rgba(255, 255, 255, 0.94);
}

.board-task__menu {
  color: rgba(255, 255, 255, 0.44);
}

.board-task__progress {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.board-task__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #a96eff 0%, #59d7ff 100%);
}

.board-task__meta,
.board-task__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: rgba(255, 255, 255, 0.52);
  font-size: 0.76rem;
}

.board-task__rating {
  color: #ffc559;
}

.task-details-panel {
  display: grid;
  min-height: 0;
  gap: 18px;
  align-content: start;
  padding: 16px 16px 20px;
  border-radius: 0;
  border: 0;
  box-shadow: none;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    rgba(7, 10, 16, 0.92);
  overflow: auto;
}

.task-details-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-details-panel__head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.96);
}

.task-details-panel__close {
  color: rgba(255, 255, 255, 0.54);
  font-size: 1.5rem;
  line-height: 1;
}

.task-details-panel__empty,
.task-details-panel__error {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-muted);
}

.task-details-panel__error {
  color: #ffabc0;
}

.task-details-panel__title {
  display: grid;
  gap: 8px;
}

.task-details-panel__title p,
.task-details-panel__title strong {
  margin: 0;
}

.task-details-panel__title p {
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.94);
}

.task-details-panel__title strong {
  color: rgba(255, 255, 255, 0.86);
}

.detail-stage-line {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.04));
}

.detail-stage-line__bar::after {
  content: "";
  position: absolute;
  inset: 3px auto 3px calc(50% - 6px);
  width: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
}

.task-stage-row--done {
  background: linear-gradient(90deg, rgba(176, 92, 255, 0.9), rgba(78, 219, 255, 0.82));
}

.task-stage-row--done::after,
.task-stage-row--active::after {
  background: rgba(255, 255, 255, 0.78);
}

.task-stage-row--active {
  background: linear-gradient(90deg, rgba(176, 92, 255, 0.92), rgba(78, 219, 255, 0.9));
}

.task-stage-row--paused {
  background: linear-gradient(90deg, rgba(255, 190, 100, 0.6), rgba(255, 255, 255, 0.06));
}

.task-stage-row--failed {
  background: linear-gradient(90deg, rgba(255, 118, 150, 0.68), rgba(255, 255, 255, 0.06));
}

.task-stage-row--pending {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.05));
}

.detail-stage-line__item p {
  margin: 0;
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.72rem;
  line-height: 1.35;
}

.detail-section {
  display: grid;
  gap: 12px;
}

.detail-section h3 {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.94);
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-overview {
  display: grid;
  gap: 10px;
}

.detail-overview__row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  color: rgba(255, 255, 255, 0.64);
}

.detail-overview__row strong {
  color: rgba(255, 255, 255, 0.9);
}

.detail-overview__row-progress {
  grid-template-columns: auto 1fr auto;
  align-items: center;
}

.detail-overview__progress {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.detail-overview__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #8f71ff 0%, #59d7ff 100%);
}

.detail-params {
  display: grid;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  overflow: hidden;
}

.detail-params__row {
  display: grid;
  grid-template-columns: minmax(90px, 0.8fr) minmax(0, 1fr);
  min-height: 40px;
}

.detail-params__row span,
.detail-params__row strong {
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 0.82rem;
}

.detail-params__row span {
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.58);
}

.detail-params__row strong {
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.86);
  font-weight: 500;
}

.detail-traces {
  display: grid;
  gap: 8px;
  max-height: 300px;
  overflow: auto;
}

.detail-traces__item,
.detail-traces__empty {
  padding: 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.detail-traces__item p,
.detail-traces__item small {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.detail-traces__item p {
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.76rem;
  line-height: 1.55;
}

.detail-traces__item small {
  display: block;
  margin-top: 0.32rem;
  color: rgba(255, 255, 255, 0.42);
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

@media (max-width: 1200px) {
  .tasks-layout {
    grid-template-columns: 1fr;
  }

  .tasks-board {
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .board-columns {
    grid-template-columns: 1fr;
  }

  .task-details-panel {
    border-radius: 0 0 24px 24px;
  }
}

@media (max-width: 900px) {
  .tasks-toolbar {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    justify-self: start;
  }

  .detail-stage-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .tasks-board {
    padding: 14px;
  }

  .board-task {
    grid-template-columns: 60px minmax(0, 1fr);
  }

  .detail-overview__row-progress {
    grid-template-columns: 1fr;
  }
}
</style>
