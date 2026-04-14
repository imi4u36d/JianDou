<template>
  <section class="tasks-view space-y-6">
    <PageHeader
      eyebrow="Workspace"
      title="任务"
      description="筛选并监控任务执行，实时查看进度与阶段。"
    >
      <div class="flex items-center gap-2">
        <HintBell
          title="任务页说明"
          text="这是统一任务看板，支持列表筛选、实时轮询和单任务详情展开。"
          :items="[
            '卡片视图便于快速浏览，列表视图便于巡检',
            '点击任务即可展开详情并查看阶段日志',
            '新建任务后会自动高亮最新任务'
          ]"
        />
        <RouterLink to="/tasks/new" class="btn-primary">
          创建新任务
        </RouterLink>
      </div>
    </PageHeader>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="surface-panel p-5">
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_200px]">
          <label class="grid gap-2 text-sm text-slate-700">
            搜索任务
            <input
              v-model="searchText"
              class="field-input"
              placeholder="按标题、文件名检索"
              type="search"
            />
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            状态
            <select v-model="statusFilter" class="field-select">
              <option value="all">全部状态</option>
              <option value="PENDING">排队中</option>
              <option value="PAUSED">已暂停</option>
              <option value="ANALYZING">分析中</option>
              <option value="PLANNING">编排中</option>
              <option value="RENDERING">渲染中</option>
              <option value="COMPLETED">已完成</option>
              <option value="FAILED">失败</option>
            </select>
          </label>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <div class="segmented-shell">
            <button class="btn-segment" :class="viewMode === 'rows' ? 'btn-segment-active' : ''" type="button" @click="viewMode = 'rows'">
              列表
            </button>
            <button class="btn-segment" :class="viewMode === 'cards' ? 'btn-segment-active' : ''" type="button" @click="viewMode = 'cards'">
              卡片
            </button>
          </div>
          <label class="ml-auto min-w-[180px] max-w-[220px] grow text-sm text-slate-700 sm:ml-0 sm:grow-0">
            <select v-model="sortMode" class="field-select">
              <option value="updated_desc">最近更新</option>
              <option value="created_desc">最新创建</option>
              <option value="progress_desc">进度优先</option>
              <option value="semantic_desc">文本输入优先</option>
              <option value="effect_rating_desc">评分最高</option>
            </select>
          </label>
          <button :class="isFilterActive ? 'btn-warning' : 'btn-ghost'" type="button" @click="clearFilters">
            清空筛选
          </button>
          <span class="surface-chip">{{ filteredTasks.length }} / {{ tasks.length }}</span>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">进行中</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.running }}</p>
          <p class="mt-2 text-sm text-slate-600">分析、编排和渲染阶段的任务。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">已完成</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.completed }}</p>
          <p class="mt-2 text-sm text-slate-600">可直接预览、下载和查看结果。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">需要处理</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.failed }}</p>
          <p class="mt-2 text-sm text-slate-600">失败任务可重试或直接删除。</p>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="surface-tile tasks-alert p-4 text-sm text-rose-700">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{{ errorMessage }}</p>
        <button class="btn-secondary btn-sm" type="button" @click="loadTasks">
          重新加载
        </button>
      </div>
    </div>

    <div v-if="loading" class="surface-tile tasks-loading p-10 text-center text-slate-600">
      正在加载任务列表...
    </div>

    <template v-else>
      <div v-if="filteredTasks.length === 0" class="surface-panel tasks-empty p-0">
        <div class="tasks-empty__copy">
          <p class="tasks-empty__eyebrow">{{ isFilterActive ? "当前筛选下无结果" : "Task Workspace" }}</p>
          <h3 class="tasks-empty__title">{{ isFilterActive ? "没有匹配的任务" : "先创建第一个生成任务" }}</h3>
          <p class="tasks-empty__description">
            {{
              isFilterActive
                ? "当前搜索词或状态过滤后没有结果。你可以先清空筛选，再继续巡检所有任务。"
                : "这里会集中展示排队、运行、完成和失败任务。创建后可在同一页查看进度、日志和产物目录。"
            }}
          </p>
          <div class="tasks-empty__actions">
            <button v-if="isFilterActive" class="btn-warning" type="button" @click="clearFilters">
              清空筛选
            </button>
            <RouterLink v-else to="/tasks/new" class="btn-primary">
              创建任务
            </RouterLink>
            <RouterLink to="/generate" class="btn-secondary">
              打开生成器
            </RouterLink>
          </div>
          <div class="tasks-empty__chips">
            <span class="surface-chip">TXT 导入</span>
            <span class="surface-chip">进度轮询</span>
            <span class="surface-chip">结果可回看</span>
          </div>
        </div>
        <div class="tasks-empty__preview">
          <div class="tasks-empty__preview-head">
            <span>Ready Queue</span>
            <strong>{{ isFilterActive ? 0 : metrics.total }}</strong>
          </div>
          <div class="tasks-empty__preview-body">
            <article class="tasks-empty__preview-card">
              <p>分析队列</p>
              <strong>{{ metrics.running }}</strong>
              <small>创建任务后会优先显示进行中的执行链路。</small>
            </article>
            <article class="tasks-empty__preview-card">
              <p>结果归档</p>
              <strong>{{ metrics.completed }}</strong>
              <small>完成后可在这里进入详情、查看评分和下载产物。</small>
            </article>
            <article class="tasks-empty__preview-card tasks-empty__preview-card-accent">
              <p>下一步</p>
              <strong>{{ isFilterActive ? "调整筛选" : "启动首个任务" }}</strong>
              <small>{{ isFilterActive ? "检查状态或关键词条件。" : "从文本输入、模型选择和提示词开始。" }}</small>
            </article>
          </div>
        </div>
      </div>

      <div v-else class="grid gap-5">
        <section v-for="group in groupedTasks" :key="group.key" class="surface-panel p-5">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">任务分组</p>
              <h3 class="mt-2 text-xl font-semibold tracking-[-0.03em] text-slate-900">{{ group.title }}</h3>
              <p class="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{{ group.description }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="surface-chip">{{ group.items.length }} 条</span>
              <button class="btn-ghost btn-sm" type="button" @click="toggleGroup(group.key)">
                {{ isGroupCollapsed(group.key) ? "展开" : "折叠" }}
              </button>
            </div>
          </div>
          <div v-if="!isGroupCollapsed(group.key) && group.items.length" class="mt-5">
            <div v-if="viewMode === 'cards'" class="grid min-w-0 gap-4 xl:grid-cols-2 2xl:grid-cols-3">
              <TaskCard
                v-for="task in group.items"
                :key="task.id"
                :busy="managingTaskId === task.id"
                :task="task"
                :selectable="true"
                :selected="task.id === selectedTaskId"
                @select="handleSelectTask"
                @pause="handlePause"
                @continue="handleContinueTask"
                @terminate="handleTerminate"
                @retry="handleRetry"
                @delete="handleDelete"
              />
            </div>
            <div v-else class="grid gap-3">
              <TaskRow
                v-for="task in group.items"
                :key="task.id"
                :busy="managingTaskId === task.id"
                :task="task"
                :selectable="true"
                :selected="task.id === selectedTaskId"
                @select="handleSelectTask"
                @pause="handlePause"
                @continue="handleContinueTask"
                @terminate="handleTerminate"
                @retry="handleRetry"
                @delete="handleDelete"
              />
            </div>
          </div>
          <div v-else class="surface-tile mt-5 p-4 text-sm text-slate-600">
            该分组已折叠，点击右上角可展开查看。
          </div>
        </section>
      </div>
    </template>

    <section v-if="selectedTaskId" class="surface-panel p-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">任务详情</p>
          <h3 class="mt-2 text-lg font-semibold text-slate-900">
            {{ selectedTaskDetail?.title || selectedTaskSummary?.title || "加载中..." }}
          </h3>
          <p class="mt-1 text-sm text-slate-600">
            {{ selectedTaskDetail?.id || selectedTaskId }} · 当前阶段 {{ selectedTaskStageLabel }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="surface-chip">进度 {{ selectedTaskDetail?.progress ?? selectedTaskSummary?.progress ?? 0 }}%</span>
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
            继续生成
          </button>
          <button class="btn-secondary btn-sm" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
            刷新详情
          </button>
        </div>
      </div>

      <div v-if="selectedTaskError" class="surface-tile mt-4 border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
        {{ selectedTaskError }}
      </div>

      <div v-else class="mt-4 grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div class="surface-tile p-4">
          <p class="text-sm font-semibold text-slate-900">阶段时间线</p>
          <div class="mt-3 grid gap-2">
            <div
              v-for="stage in selectedTaskStages"
              :key="stage.key"
              class="task-stage-row flex items-center justify-between rounded-xl px-3 py-2 text-sm"
              :class="stageStateClass(stage.state)"
            >
              <span>{{ stage.label }}</span>
              <span class="font-semibold">{{ stage.stateLabel }}</span>
            </div>
          </div>
          <p class="mt-3 text-xs text-slate-500">
            开始 {{ formatDateTime(selectedTaskDetail?.startedAt) }} · 完成 {{ formatDateTime(selectedTaskDetail?.finishedAt) }}
          </p>
        </div>

        <div class="surface-tile p-4">
          <p class="text-sm font-semibold text-slate-900">结果概览</p>
          <div class="mt-3 grid gap-2 text-sm text-slate-600">
            <div class="flex items-center justify-between">
              <span>已生成结果</span>
              <span class="font-semibold text-slate-900">
                {{ selectedTaskDetail?.completedOutputCount ?? selectedTaskDetail?.outputs?.length ?? 0 }} 条
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span>比例</span>
              <span class="font-semibold text-slate-900">{{ selectedTaskDetail?.aspectRatio ?? selectedTaskSummary?.aspectRatio ?? "-" }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span>当前 Worker</span>
              <span class="max-w-[180px] truncate font-semibold text-slate-900">{{ selectedTaskWorkerLabel }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span>Join 进度</span>
              <span class="max-w-[180px] truncate font-semibold text-slate-900">{{ selectedTaskJoinLabel }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span>效果评分</span>
              <span class="max-w-[180px] truncate font-semibold text-slate-900">{{ selectedTaskEffectRatingLabel }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span>任务 Seed</span>
              <span class="max-w-[180px] truncate font-semibold text-slate-900">{{ selectedTaskSeedLabel }}</span>
            </div>
          </div>
        </div>

        <div v-if="selectedTaskDetail" class="surface-tile p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-semibold text-slate-900">效果评分</p>
            <span class="surface-chip">{{ selectedTaskEffectRatingLabel }}</span>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="score in [5, 4, 3, 2, 1]"
              :key="score"
              class="btn-secondary btn-sm"
              :class="selectedTaskRatingDraft === score ? 'rating-button-active' : ''"
              type="button"
              :disabled="selectedTaskRatingSaving"
              @click="selectedTaskRatingDraft = score"
            >
              {{ score }}/5
            </button>
          </div>
          <textarea
            v-model="selectedTaskRatingNote"
            class="field-textarea mt-3"
            rows="3"
            placeholder="可选：记录这个 seed 在当前任务上的效果观察。"
          ></textarea>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <button class="btn-primary btn-sm" type="button" :disabled="selectedTaskRatingSaving || !selectedTaskRatingDraft" @click="saveSelectedTaskRating">
              {{ selectedTaskRatingSaving ? "保存中..." : "保存评分" }}
            </button>
            <span class="text-xs text-slate-500">评分对成功和失败任务都开放，并可用于按评分倒序筛选 seed。</span>
          </div>
        </div>

        <div v-if="selectedTaskMonitoringRows.length" class="surface-tile p-4">
          <p class="text-sm font-semibold text-slate-900">执行监控</p>
          <div class="mt-3 grid gap-2 text-sm text-slate-600">
            <div v-for="item in selectedTaskMonitoringRows" :key="item.label" class="flex items-center justify-between gap-3">
              <span>{{ item.label }}</span>
              <span class="max-w-[180px] truncate font-semibold text-slate-900">{{ item.value }}</span>
            </div>
          </div>
        </div>

        <div v-if="selectedTaskArtifactRows.length" class="surface-tile p-4 xl:col-span-2">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-semibold text-slate-900">产物目录</p>
            <span class="surface-chip">{{ selectedTaskArtifactDirectoryHint }}</span>
          </div>
          <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <div
              v-for="item in selectedTaskArtifactRows"
              :key="item.label"
              class="detail-card rounded-xl px-3 py-3 text-sm"
            >
              <p class="text-xs text-slate-500">{{ item.label }}</p>
              <p class="mt-1 break-all font-semibold text-slate-900">{{ item.value }}</p>
            </div>
          </div>
        </div>

        <div v-if="selectedTaskDetail" class="surface-tile p-4 xl:col-span-2">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-semibold text-slate-900">创建参数</p>
            <span class="surface-chip">时长模式 {{ selectedTaskDurationModeLabel }}</span>
          </div>
          <div class="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <div
              v-for="item in selectedTaskParameterRows"
              :key="item.label"
              class="detail-card rounded-xl px-3 py-3 text-sm"
            >
              <p class="text-xs text-slate-500">{{ item.label }}</p>
              <p class="mt-1 break-all font-semibold text-slate-900">{{ item.value }}</p>
            </div>
          </div>
          <div v-if="selectedTaskDetail.creativePrompt" class="detail-panel mt-4 rounded-xl px-3 py-3">
            <p class="text-xs text-slate-500">创意提示词</p>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{{ selectedTaskDetail.creativePrompt }}</p>
          </div>
          <div v-if="selectedTaskTranscriptPreview" class="detail-panel mt-4 rounded-xl px-3 py-3">
            <p class="text-xs text-slate-500">文本输入摘要</p>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{{ selectedTaskTranscriptPreview }}</p>
          </div>
        </div>
      </div>

      <div class="surface-tile mt-4 p-4">
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-semibold text-slate-900">最近阶段日志</p>
          <span class="surface-chip">{{ selectedTaskTrace.length }} 条</span>
        </div>
        <ul class="mt-3 grid gap-2 text-sm text-slate-600">
          <li v-if="selectedTaskTrace.length === 0" class="trace-log-card trace-log-card--empty rounded-xl px-3 py-2 text-slate-500">
            暂无日志，任务刚启动时可能需要等待几秒。
          </li>
          <li
            v-for="event in selectedTaskTrace.slice(0, 8)"
            :key="`${event.timestamp}-${event.event}-${event.stage}`"
            class="trace-log-card rounded-xl px-3 py-2"
          >
            <p class="text-xs text-slate-500">{{ formatDateTime(event.timestamp) }} · {{ event.stage }} · {{ event.level }}</p>
            <p class="mt-1 text-slate-800">{{ event.message }}</p>
          </li>
        </ul>
      </div>
    </section>

    <p class="text-xs text-slate-500">最近刷新：{{ lastLoadedAt }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, rateTaskEffect, retryTask, terminateTask } from "@/api/tasks";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import HintBell from "@/components/HintBell.vue";
import PageHeader from "@/components/PageHeader.vue";
import TaskCard from "@/components/TaskCard.vue";
import TaskRow from "@/components/TaskRow.vue";
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

function normalizeQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] == null ? "" : String(value[0]);
  }
  return value == null ? "" : String(value);
}

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
    { label: "任务 Seed", value: selectedTaskSeedLabel.value },
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
    { label: "Attempt 状态", value: formatMonitoringValue(monitoring.activeAttemptStatus) },
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
    { label: "Storage 根目录", value: formatMonitoringValue(artifactDirectories.storageRoot) },
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

async function loadTasks() {
  errorMessage.value = "";
  loading.value = tasks.value.length === 0;
  try {
    // Keep filtering local so typing and toggling view mode do not trigger extra requests.
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

function scheduleWriteQuery() {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
  }
  querySyncTimer = window.setTimeout(() => {
    querySyncTimer = null;
    writeQuery();
  }, 160);
}

function clearFilters() {
  searchText.value = "";
  statusFilter.value = "all";
  sortMode.value = "updated_desc";
}

function handleSelectTask(task: TaskListItem) {
  selectedTaskId.value = task.id;
  writeQuery();
  void loadSelectedTaskDetails();
}

function isGroupCollapsed(groupKey: string) {
  return Boolean(collapsedGroups.value[groupKey]);
}

function toggleGroup(groupKey: string) {
  collapsedGroups.value = {
    ...collapsedGroups.value,
    [groupKey]: !collapsedGroups.value[groupKey]
  };
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
  color: var(--text-strong);
}

.tasks-view :deep(.surface-panel) {
  border-radius: 1.5rem;
  background: var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.tasks-view :deep(.surface-tile) {
  border-radius: 1rem;
  background: var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.tasks-view :deep(.surface-chip) {
  background: var(--bg-surface);
  color: var(--text-body);
  box-shadow: var(--shadow-pressed);
}

.tasks-view :deep(.segmented-shell) {
  background: var(--bg-surface);
  box-shadow: var(--shadow-pressed);
}

.tasks-view :deep(.btn-segment-active) {
  background: var(--bg-surface);
  color: var(--text-strong);
  box-shadow: var(--shadow-pressed);
}

.tasks-view :deep(.btn-primary) {
  background: linear-gradient(145deg, var(--bg-accent-soft), var(--bg-accent));
}

.tasks-view :deep(.btn-primary:hover:not(:disabled)) {
  box-shadow: var(--shadow-accent);
}

.tasks-alert,
.tasks-loading,
.tasks-empty,
.detail-card,
.detail-panel,
.trace-log-card,
.task-stage-row {
  background: var(--bg-surface);
  box-shadow: var(--shadow-pressed);
  border: 0;
}

.tasks-alert {
  color: #a8707b;
}

.task-stage-row {
  color: var(--text-body);
}

.task-stage-row--done {
  color: #7e9d8d;
}

.task-stage-row--active {
  color: var(--accent-strong);
}

.task-stage-row--paused {
  color: #b79b79;
}

.task-stage-row--failed {
  color: #b37d87;
}

.task-stage-row--pending {
  color: var(--text-muted);
}

.detail-card,
.detail-panel,
.trace-log-card {
  color: var(--text-strong);
}

.rating-button-active {
  box-shadow: var(--shadow-pressed);
}

.tasks-empty {
  display: grid;
  overflow: hidden;
  border-radius: 1.6rem;
  border: 1px solid var(--surface-border);
  background:
    radial-gradient(circle at top right, rgba(255, 183, 174, 0.18), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise);
}

.tasks-empty__copy,
.tasks-empty__preview {
  padding: 1.5rem;
}

.tasks-empty__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.tasks-empty__title {
  margin: 0.7rem 0 0;
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  line-height: 1.05;
  letter-spacing: -0.05em;
  color: var(--text-strong);
}

.tasks-empty__description {
  margin: 0.85rem 0 0;
  max-width: 38rem;
  font-size: 0.96rem;
  line-height: 1.8;
  color: var(--text-body);
}

.tasks-empty__actions,
.tasks-empty__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.2rem;
}

.tasks-empty__preview {
  border-top: 1px solid rgba(128, 144, 167, 0.12);
  background: rgba(255, 255, 255, 0.28);
}

.tasks-empty__preview-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.tasks-empty__preview-head span {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.tasks-empty__preview-head strong {
  font-size: 2.4rem;
  line-height: 1;
  letter-spacing: -0.08em;
  color: var(--text-strong);
}

.tasks-empty__preview-body {
  display: grid;
  gap: 0.85rem;
}

.tasks-empty__preview-card {
  border-radius: 1rem;
  border: 1px solid var(--surface-border);
  padding: 1rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.3)),
    var(--bg-surface);
  box-shadow: var(--shadow-pressed);
}

.tasks-empty__preview-card p,
.tasks-empty__preview-card strong,
.tasks-empty__preview-card small {
  display: block;
}

.tasks-empty__preview-card p {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.tasks-empty__preview-card strong {
  margin-top: 0.45rem;
  font-size: 1.35rem;
  line-height: 1.15;
  color: var(--text-strong);
}

.tasks-empty__preview-card small {
  margin-top: 0.45rem;
  line-height: 1.7;
  color: var(--text-body);
}

.tasks-empty__preview-card-accent {
  border-color: rgba(197, 108, 115, 0.18);
  background:
    linear-gradient(180deg, rgba(255, 240, 236, 0.9), rgba(255, 255, 255, 0.38)),
    var(--bg-surface);
}

@media (min-width: 960px) {
  .tasks-empty {
    grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
  }

  .tasks-empty__preview {
    border-top: 0;
    border-left: 1px solid rgba(128, 144, 167, 0.12);
  }
}
</style>
