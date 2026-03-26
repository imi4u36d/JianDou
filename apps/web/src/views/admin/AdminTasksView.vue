<template>
  <section class="space-y-6">
    <PageHeader
      eyebrow="Admin Tasks"
      title="任务管理"
      description="高密度 ops 任务台，支持搜索、筛选、批量操作和直达详情，适合大量任务的扫视与处置。"
    >
      <div class="flex flex-wrap gap-2">
        <RouterLink
          to="/tasks/new"
          :class="adminPrimaryButton"
        >
          新建任务
        </RouterLink>
        <button
          :class="adminSecondaryButton"
          type="button"
          @click="refreshAll"
        >
          刷新
        </button>
      </div>
    </PageHeader>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        :class="summaryToneClass(card.tone)"
        class="rounded-[24px] border p-5 shadow-[0_16px_50px_rgba(0,0,0,0.16)]"
      >
        <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">{{ card.label }}</p>
        <p class="mt-3 text-3xl font-semibold text-slate-950">{{ card.value }}</p>
        <p class="mt-2 text-sm leading-6 text-slate-700">{{ card.hint }}</p>
      </article>
    </div>

    <section class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.96),rgba(8,14,28,0.92))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.38)]">
      <div class="grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(0,0.72fr))]">
        <input
          v-model="searchText"
          class="field-input"
          placeholder="搜索标题、文件名、平台、比例"
          type="search"
        />
        <select v-model="statusFilter" class="field-select">
          <option value="all">全部状态</option>
          <option value="PENDING">排队中</option>
          <option value="ANALYZING">分析中</option>
          <option value="PLANNING">规划中</option>
          <option value="RENDERING">渲染中</option>
          <option value="COMPLETED">已完成</option>
          <option value="FAILED">失败</option>
        </select>
        <select v-model="platformFilter" class="field-select">
          <option value="all">全部平台</option>
          <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platform }}</option>
        </select>
        <select v-model="sortMode" class="field-select">
          <option value="updated_desc">最近更新</option>
          <option value="created_desc">最新创建</option>
          <option value="progress_desc">进度优先</option>
          <option value="status_desc">状态优先</option>
        </select>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <button :class="adminWarningButton" :disabled="selectedIds.length === 0 || actionLoading" type="button" @click="handleBulkRetry">
          批量重试
        </button>
        <button :class="adminDangerButton" :disabled="selectedIds.length === 0 || actionLoading" type="button" @click="handleBulkDelete">
          批量删除
        </button>
        <button :class="adminGhostButton" type="button" @click="toggleSelectVisible">
          {{ allVisibleSelected ? "取消选择可见项" : "选择可见项" }}
        </button>
        <button :class="adminGhostButton" type="button" @click="clearSelection">
          清空选择
        </button>
        <span class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-slate-200">
          已选 {{ selectedIds.length }} 条
        </span>
        <span class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-slate-200">
          可见 {{ sortedTasks.length }} / {{ tasks.length }}
        </span>
      </div>
    </section>

    <div v-if="errorMessage" class="rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      {{ errorMessage }}
    </div>
    <div v-else-if="actionMessage" :class="actionMessageTone === 'warn' ? 'border-amber-400/20 bg-amber-500/10 text-amber-100' : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100'" class="rounded-[24px] border p-4 text-sm">
      {{ actionMessage }}
    </div>

    <section class="overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.96),rgba(8,14,28,0.92))] shadow-[0_24px_80px_rgba(0,0,0,0.38)]">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div>
          <p class="text-[11px] uppercase tracking-[0.3em] text-sky-300/80">Ops Table</p>
          <h3 class="mt-2 text-lg font-semibold text-white">任务扫视表</h3>
          <p class="mt-1 text-sm text-slate-400">默认按最新更新排序，失败和语义任务会更明显露出。</p>
        </div>
        <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-200">
          {{ summaryFooterLabel }}
        </span>
      </div>

      <div v-if="loading" class="p-6 text-sm text-slate-300">正在读取任务...</div>
      <div v-else-if="sortedTasks.length === 0" class="p-6 text-sm text-slate-400">当前没有符合筛选条件的任务。</div>
      <div v-else class="overflow-x-auto">
        <div class="min-w-[1500px]">
          <div class="sticky top-0 z-10 grid grid-cols-[42px_minmax(0,2.1fr)_minmax(0,0.86fr)_minmax(0,0.92fr)_minmax(0,0.86fr)_minmax(0,0.92fr)_auto] gap-3 border-b border-white/10 bg-[rgba(8,14,28,0.94)] px-5 py-3 text-[11px] uppercase tracking-[0.24em] text-slate-500 backdrop-blur">
            <span></span>
            <span>任务</span>
            <span>状态 / 平台</span>
            <span>语义信号</span>
            <span>进度</span>
            <span>时间</span>
            <span class="text-right">操作</span>
          </div>

          <div class="divide-y divide-white/6">
            <article
              v-for="task in sortedTasks"
              :key="task.id"
              :class="rowToneClass(task.status)"
              class="grid grid-cols-[42px_minmax(0,2.1fr)_minmax(0,0.86fr)_minmax(0,0.92fr)_minmax(0,0.86fr)_minmax(0,0.92fr)_auto] gap-3 px-5 py-4 transition duration-200 hover:bg-white/[0.03]"
            >
              <div class="flex items-start pt-1">
                <input
                  :checked="selectedIds.includes(task.id)"
                  class="h-4 w-4 rounded border-white/20 bg-slate-950/70 text-sky-500"
                  type="checkbox"
                  @change="toggleSelected(task.id)"
                />
              </div>

              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span :class="statusPillClass(task.status)" class="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
                    {{ statusLabel(task.status) }}
                  </span>
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-200">
                    {{ task.platform }}
                  </span>
                </div>
                <p class="mt-3 break-words text-sm font-semibold text-white">{{ task.title }}</p>
                <p class="mt-1 break-all text-xs text-slate-400">{{ task.sourceFileName }}</p>
                <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">{{ task.aspectRatio }}</span>
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">{{ task.minDurationSeconds }}-{{ task.maxDurationSeconds }} 秒</span>
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">输出 {{ task.completedOutputCount ?? 0 }}/{{ task.outputCount }}</span>
                </div>
              </div>

              <div class="text-sm text-slate-300">
                <p class="font-medium text-white">{{ task.platform }}</p>
                <p class="mt-1 text-xs text-slate-400">{{ task.retryCount ?? 0 }} 次重试</p>
                <p v-if="task.startedAt" class="mt-1 text-xs text-slate-500">开始 {{ formatShortDate(task.startedAt) }}</p>
              </div>

              <div class="text-sm text-slate-300">
                <p v-if="task.hasTimedTranscript" class="font-medium text-sky-100">时间轴字幕</p>
                <p v-else-if="task.hasTranscript" class="font-medium text-fuchsia-100">文本语义</p>
                <p v-else class="text-slate-500">无语义输入</p>
                <p class="mt-1 text-xs text-slate-400">{{ semanticHint(task) }}</p>
                <div class="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-slate-300">{{ task.completedOutputCount ?? 0 }} / {{ task.outputCount }} 输出</span>
                </div>
              </div>

              <div class="text-sm text-slate-300">
                <p class="font-medium text-white">{{ task.progress }}%</p>
                <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div class="h-full rounded-full" :class="progressBarClass(task.status)" :style="{ width: `${task.progress}%` }"></div>
                </div>
                <p class="mt-2 text-xs text-slate-400">{{ progressLabel(task) }}</p>
              </div>

              <div class="text-sm text-slate-300">
                <p class="font-medium text-white">{{ formatShortDate(task.updatedAt) }}</p>
                <p class="mt-1 text-xs text-slate-400">创建 {{ formatShortDate(task.createdAt) }}</p>
                <p v-if="task.finishedAt" class="mt-1 text-xs text-slate-500">完成 {{ formatShortDate(task.finishedAt) }}</p>
              </div>

              <div class="flex flex-wrap justify-end gap-2">
                <RouterLink
                  :to="`/admin/tasks/${task.id}`"
                  :class="adminSecondaryButtonSm"
                >
                  详情
                </RouterLink>
                <button
                  :class="adminGhostButtonSm"
                  :disabled="actionLoading"
                  type="button"
                  @click="cloneTask(task.id)"
                >
                  复制
                </button>
                <button
                  v-if="task.status === 'FAILED'"
                  :class="adminWarningButtonSm"
                  :disabled="actionLoading"
                  type="button"
                  @click="retrySingle(task.id)"
                >
                  重试
                </button>
                <button
                  :class="adminDangerButtonSm"
                  :disabled="actionLoading || runningStatus(task.status)"
                  type="button"
                  @click="deleteSingle(task.id, task.title)"
                >
                  删除
                </button>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { bulkDeleteAdminTasks, bulkRetryAdminTasks, cloneAdminTask, deleteAdminTask, fetchAdminTasks, retryAdminTask } from "@/api/admin";
import PageHeader from "@/components/PageHeader.vue";
import { usePolling } from "@/composables/usePolling";
import type { TaskListItem, TaskStatus } from "@/types";

const router = useRouter();
const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const actionMessage = ref("");
const actionMessageTone = ref<"success" | "warn">("success");
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const platformFilter = ref<string | "all">("all");
const sortMode = ref<"updated_desc" | "created_desc" | "progress_desc" | "status_desc">("updated_desc");
const selectedIds = ref<string[]>([]);
let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const adminPrimaryButton = "btn-primary";
const adminSecondaryButton = "btn-secondary";
const adminGhostButton = "btn-ghost";
const adminWarningButton = "btn-warning";
const adminDangerButton = "btn-danger";
const adminSecondaryButtonSm = "btn-secondary btn-sm";
const adminGhostButtonSm = "btn-ghost btn-sm";
const adminWarningButtonSm = "btn-warning btn-sm";
const adminDangerButtonSm = "btn-danger btn-sm";

const platformOptions = computed(() => Array.from(new Set(tasks.value.map((task) => task.platform).filter(Boolean))).sort());

const filteredTasks = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (platformFilter.value !== "all" && task.platform !== platformFilter.value) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [task.title, task.sourceFileName, task.platform, task.aspectRatio].join(" ").toLowerCase().includes(keyword);
  });
});

const sortedTasks = computed(() => {
  const items = [...filteredTasks.value];
  if (sortMode.value === "created_desc") {
    return items.sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  }
  if (sortMode.value === "progress_desc") {
    return items.sort((left, right) => (right.progress ?? 0) - (left.progress ?? 0));
  }
  if (sortMode.value === "status_desc") {
    return items.sort((left, right) => String(left.status).localeCompare(String(right.status)));
  }
  return items.sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime());
});

const allVisibleSelected = computed(() => sortedTasks.value.length > 0 && sortedTasks.value.every((task) => selectedIds.value.includes(task.id)));

const summaryCards = computed(() => {
  const total = tasks.value.length;
  const running = tasks.value.filter((task) => runningStatus(task.status)).length;
  const failed = tasks.value.filter((task) => task.status === "FAILED").length;
  const semantic = tasks.value.filter((task) => task.hasTranscript || task.hasTimedTranscript).length;
  const timedSemantic = tasks.value.filter((task) => task.hasTimedTranscript).length;
  const average = total ? Math.round(tasks.value.reduce((sum, task) => sum + (task.progress ?? 0), 0) / total) : 0;

  return [
    { key: "total", label: "任务总量", value: total, hint: "全部任务与历史任务", tone: "blue" as const },
    { key: "running", label: "运行中", value: running, hint: "持续观察的任务", tone: "sky" as const },
    { key: "failed", label: "异常", value: failed, hint: "优先处理的失败任务", tone: "rose" as const },
    { key: "semantic", label: "语义任务", value: semantic, hint: "带字幕或文本线索", tone: "amber" as const },
    { key: "timed", label: "时间轴字幕", value: timedSemantic, hint: "可直接用于卡点判断", tone: "slate" as const },
    { key: "average", label: "平均进度", value: `${average}%`, hint: "整体推进速度", tone: "teal" as const },
  ];
});

const summaryFooterLabel = computed(() => {
  if (loading.value) {
    return "正在同步任务...";
  }
  return `${sortedTasks.value.length} / ${tasks.value.length} 可见`;
});

function summaryToneClass(tone: "blue" | "sky" | "rose" | "amber" | "slate" | "teal") {
  switch (tone) {
    case "blue":
      return "bg-[linear-gradient(180deg,rgba(219,234,254,0.96),rgba(191,219,254,0.9))] border-sky-200/80";
    case "sky":
      return "bg-[linear-gradient(180deg,rgba(224,242,254,0.96),rgba(186,230,253,0.9))] border-sky-200/80";
    case "rose":
      return "bg-[linear-gradient(180deg,rgba(255,228,230,0.96),rgba(254,202,202,0.9))] border-rose-200/70";
    case "amber":
      return "bg-[linear-gradient(180deg,rgba(254,243,199,0.96),rgba(253,230,138,0.9))] border-amber-200/70";
    case "teal":
      return "bg-[linear-gradient(180deg,rgba(204,251,241,0.96),rgba(153,246,228,0.9))] border-teal-200/70";
    default:
      return "bg-[linear-gradient(180deg,rgba(241,245,249,0.96),rgba(226,232,240,0.92))] border-slate-200/80";
  }
}

function statusLabel(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "排队中";
    case "ANALYZING":
      return "分析中";
    case "PLANNING":
      return "规划中";
    case "RENDERING":
      return "渲染中";
    case "COMPLETED":
      return "已完成";
    case "FAILED":
      return "失败";
    default:
      return status;
  }
}

function statusPillClass(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "border border-slate-300/10 bg-white/[0.04] text-slate-200";
    case "ANALYZING":
      return "border border-sky-300/20 bg-sky-500/10 text-sky-100";
    case "PLANNING":
      return "border border-cyan-300/20 bg-cyan-500/10 text-cyan-100";
    case "RENDERING":
      return "border border-amber-300/20 bg-amber-500/10 text-amber-100";
    case "COMPLETED":
      return "border border-emerald-300/20 bg-emerald-500/10 text-emerald-100";
    case "FAILED":
      return "border border-rose-300/20 bg-rose-500/10 text-rose-100";
    default:
      return "border border-white/10 bg-white/[0.04] text-slate-200";
  }
}

function progressBarClass(status: TaskStatus) {
  if (status === "FAILED") {
    return "bg-gradient-to-r from-rose-500 via-rose-400 to-amber-300";
  }
  if (status === "COMPLETED") {
    return "bg-gradient-to-r from-emerald-500 via-cyan-300 to-sky-400";
  }
  if (status === "RENDERING") {
    return "bg-gradient-to-r from-amber-500 via-orange-300 to-rose-300";
  }
  return "bg-gradient-to-r from-sky-500 via-cyan-300 to-amber-300";
}

function rowToneClass(status: TaskStatus) {
  if (status === "FAILED") {
    return "border-l-2 border-l-rose-400/60 bg-rose-500/5";
  }
  if (status === "RENDERING") {
    return "border-l-2 border-l-amber-400/40 bg-amber-500/5";
  }
  if (status === "PLANNING" || status === "ANALYZING") {
    return "border-l-2 border-l-sky-400/40 bg-sky-500/5";
  }
  if (status === "COMPLETED") {
    return "border-l-2 border-l-emerald-400/35 bg-emerald-500/[0.04]";
  }
  return "border-l-2 border-l-white/10";
}

function semanticHint(task: TaskListItem) {
  if (task.hasTimedTranscript) {
    return "可参与字幕 + 视觉 + 音频融合规划";
  }
  if (task.hasTranscript) {
    return "文本语义可参与剧情理解";
  }
  return "建议补充字幕以提升切点精度";
}

function progressLabel(task: TaskListItem) {
  if (task.status === "FAILED") {
    return "任务异常，等待人工处置";
  }
  if (task.status === "COMPLETED") {
    return "任务已完成，可检查输出";
  }
  if (task.status === "RENDERING") {
    return "FFmpeg 渲染阶段";
  }
  if (task.status === "PLANNING") {
    return "大模型规划阶段";
  }
  if (task.status === "ANALYZING") {
    return "素材分析阶段";
  }
  return "等待进入处理流水线";
}

function formatShortDate(value: string) {
  return new Date(value).toLocaleString();
}

function runningStatus(status: TaskStatus) {
  return status === "ANALYZING" || status === "PLANNING" || status === "RENDERING";
}

function toggleSelected(taskId: string) {
  const index = selectedIds.value.indexOf(taskId);
  if (index >= 0) {
    selectedIds.value.splice(index, 1);
    return;
  }
  selectedIds.value.push(taskId);
}

function toggleSelectVisible() {
  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter((id) => !sortedTasks.value.some((task) => task.id === id));
    return;
  }

  const merged = new Set(selectedIds.value);
  sortedTasks.value.forEach((task) => merged.add(task.id));
  selectedIds.value = Array.from(merged);
}

function clearSelection() {
  selectedIds.value = [];
}

async function loadTasks() {
  tasks.value = await fetchAdminTasks({
    q: searchText.value.trim() || undefined,
    status: statusFilter.value,
    platform: platformFilter.value,
  });
}

async function refreshAll() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取任务失败";
  } finally {
    loading.value = false;
  }
}

async function retrySingle(taskId: string) {
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    await retryAdminTask(taskId);
    actionMessage.value = "任务已提交重试。";
    actionMessageTone.value = "success";
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function deleteSingle(taskId: string, title: string) {
  if (!window.confirm(`确认删除任务“${title}”吗？`)) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    await deleteAdminTask(taskId);
    selectedIds.value = selectedIds.value.filter((id) => id !== taskId);
    actionMessage.value = "任务已删除。";
    actionMessageTone.value = "success";
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除失败";
  } finally {
    actionLoading.value = false;
  }
}

async function handleBulkRetry() {
  if (selectedIds.value.length === 0) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    const result = await bulkRetryAdminTasks(selectedIds.value);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedIds.value = result.failed.length
      ? selectedIds.value.filter((id) => failedIds.has(id))
      : [];
    if (result.failed.length) {
      actionMessage.value = `已重试 ${result.succeededTaskIds.length} 条，${result.failed.length} 条未成功：${result.failed
        .slice(0, 3)
        .map((item) => `${item.taskId}（${item.reason}）`)
        .join("；")}`;
      actionMessageTone.value = "warn";
    } else {
      actionMessage.value = `已批量重试 ${result.succeededTaskIds.length} 条任务。`;
      actionMessageTone.value = "success";
    }
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "批量重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function handleBulkDelete() {
  if (selectedIds.value.length === 0) {
    return;
  }
  if (!window.confirm(`确认删除选中的 ${selectedIds.value.length} 个任务吗？`)) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    const result = await bulkDeleteAdminTasks(selectedIds.value);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedIds.value = result.failed.length
      ? selectedIds.value.filter((id) => failedIds.has(id))
      : [];
    if (result.failed.length) {
      actionMessage.value = `已删除 ${result.succeededTaskIds.length} 条，${result.failed.length} 条未成功：${result.failed
        .slice(0, 3)
        .map((item) => `${item.taskId}（${item.reason}）`)
        .join("；")}`;
      actionMessageTone.value = "warn";
    } else {
      actionMessage.value = `已批量删除 ${result.succeededTaskIds.length} 条任务。`;
      actionMessageTone.value = "success";
    }
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "批量删除失败";
  } finally {
    actionLoading.value = false;
  }
}

async function cloneTask(taskId: string) {
  const draft = await cloneAdminTask(taskId);
  router.push({ path: "/tasks/new", query: { cloneFrom: draft.sourceTaskId } });
}

watch([searchText, statusFilter, platformFilter, sortMode], () => {
  selectedIds.value = selectedIds.value.filter((id) => sortedTasks.value.some((task) => task.id === id));
}, { deep: false });

watch([searchText, statusFilter, platformFilter], () => {
  if (refreshDebounceTimer) {
    clearTimeout(refreshDebounceTimer);
  }
  refreshDebounceTimer = setTimeout(() => {
    void refreshAll();
  }, 260);
}, { deep: false });

const { start } = usePolling(refreshAll, 6000);

onMounted(async () => {
  await start();
});
</script>
