<template>
  <section class="admin-page admin-dashboard-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Dashboard</p>
          <h2 class="admin-title">运营总览</h2>
          <p class="admin-subtitle">聚焦失败任务、进行中任务和最近系统日志。</p>
        </div>
        <div class="admin-action-row">
          <button :class="secondaryButtonClass" type="button" @click="refreshAll">刷新</button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="admin-alert-error">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="admin-panel px-4 py-8 text-sm text-slate-500">
      正在读取管理台总览...
    </div>

    <template v-else-if="overview">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <article
          v-for="metric in metricCards"
          :key="metric.key"
          class="admin-metric-card"
        >
          <p class="admin-eyebrow">{{ metric.label }}</p>
          <p class="admin-metric-value">{{ metric.value }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ metric.hint }}</p>
        </article>
      </div>

      <div class="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <div>
              <h3 class="text-base font-semibold text-slate-900">异常与待处理任务</h3>
              <p class="mt-1 text-sm text-slate-600">优先展示失败任务，其次是运行中任务。</p>
            </div>
            <RouterLink to="/admin/tasks" :class="secondaryButtonClass">进入任务管理</RouterLink>
          </div>

          <div class="space-y-5 p-5">
            <div class="mb-3 flex items-center justify-between">
              <p class="text-sm font-medium text-slate-800">失败任务</p>
              <span class="admin-chip">{{ overview.recentFailures.length }} 条</span>
            </div>

            <div v-if="overview.recentFailures.length" class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>任务</th>
                    <th>进度</th>
                    <th class="text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="task in overview.recentFailures" :key="task.id">
                    <td>
                      <p class="font-medium text-slate-900">{{ task.title }}</p>
                      <p class="mt-0.5 text-xs text-slate-500">{{ task.sourceFileName }}</p>
                    </td>
                    <td>{{ task.progress }}%</td>
                    <td class="text-right">
                      <RouterLink :to="`/admin/tasks/${task.id}`" class="admin-btn-secondary admin-btn-sm">查看</RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="admin-empty">
              当前没有失败任务。
            </div>

            <div class="mt-5 mb-3 flex items-center justify-between">
              <p class="text-sm font-medium text-slate-800">运行中任务</p>
              <span class="admin-chip">{{ overview.recentRunningTasks.length }} 条</span>
            </div>
            <div v-if="overview.recentRunningTasks.length" class="grid gap-2">
              <article
                v-for="task in overview.recentRunningTasks"
                :key="task.id"
                class="admin-panel-soft px-4 py-3"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="truncate text-sm font-medium text-slate-900">{{ task.title }}</p>
                  <span class="admin-chip">{{ task.status }} · {{ task.progress }}%</span>
                </div>
              </article>
            </div>
            <div v-else class="admin-empty">
              当前没有运行中的任务。
            </div>
          </div>
        </section>

        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <div>
              <h3 class="text-base font-semibold text-slate-900">最近系统日志</h3>
              <p class="mt-1 text-sm text-slate-600">支持按级别与阶段筛选。</p>
            </div>
          </div>

          <div class="space-y-4 p-5">
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="grid gap-1 text-xs text-slate-600">
                日志级别
                <select v-model="levelFilter" class="admin-field">
                  <option value="">全部级别</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARN">WARN</option>
                  <option value="INFO">INFO</option>
                </select>
              </label>
              <label class="grid gap-1 text-xs text-slate-600">
                阶段
                <select v-model="stageFilter" class="admin-field">
                  <option value="">全部阶段</option>
                  <option value="api">api</option>
                  <option value="worker">worker</option>
                  <option value="planning">planning</option>
                  <option value="render">render</option>
                  <option value="llm">llm</option>
                </select>
              </label>
            </div>

            <div v-if="traces.length" class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>级别</th>
                    <th>阶段</th>
                    <th>消息</th>
                    <th class="text-right">任务</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in traces" :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`">
                    <td class="text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                    <td>
                      <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                    </td>
                    <td>{{ entry.stage }}</td>
                    <td>{{ entry.message }}</td>
                    <td class="text-right">
                      <RouterLink :to="`/admin/tasks/${entry.taskId}`" class="admin-btn-secondary admin-btn-sm">打开</RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="admin-empty">
              当前没有符合筛选条件的日志。
            </div>
          </div>
        </section>
      </div>
    </template>
    <div v-else class="admin-alert-warn">
      暂未读取到管理台总览数据，请点击刷新重试。
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { fetchAdminOverview, fetchAdminTraces } from "@/api/admin";
import { usePolling } from "@/composables/usePolling";
import type { AdminOverview, AdminTraceEvent } from "@/types";

const overview = ref<AdminOverview | null>(null);
const traces = ref<AdminTraceEvent[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const levelFilter = ref("");
const stageFilter = ref("");

const secondaryButtonClass = "admin-btn-secondary";

const metricCards = computed(() => {
  if (!overview.value) {
    return [];
  }
  return [
    { key: "total", label: "总任务", value: overview.value.counts.totalTasks, hint: "系统任务总量" },
    { key: "running", label: "运行中", value: overview.value.counts.runningTasks, hint: "分析/规划/渲染中" },
    { key: "failed", label: "失败", value: overview.value.counts.failedTasks, hint: "需要优先处理" },
    { key: "progress", label: "平均进度", value: `${overview.value.counts.averageProgress}%`, hint: "任务池推进情况" },
    { key: "trace", label: "近期日志", value: overview.value.recentTraceCount, hint: "最近事件条数" },
  ];
});

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function logLevelClass(level: string) {
  if (level === "ERROR") {
    return "bg-rose-100 text-rose-700";
  }
  if (level === "WARN") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
}

async function loadOverview() {
  overview.value = await fetchAdminOverview();
}

async function loadTraces() {
  traces.value = await fetchAdminTraces({
    limit: 12,
    level: levelFilter.value || undefined,
    stage: stageFilter.value || undefined,
  });
}

async function refreshAll() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await Promise.all([loadOverview(), loadTraces()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取管理台总览失败";
  } finally {
    loading.value = false;
  }
}

const { start } = usePolling(refreshAll, 6000);

watch([levelFilter, stageFilter], () => {
  void loadTraces();
});

onMounted(async () => {
  await start();
});
</script>

<style scoped>
.admin-dashboard-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-dashboard-view :deep(.admin-metric-card) {
  border-color: #dbe4ee;
  background: #f8fafc;
}

.admin-dashboard-view :deep(.admin-table th) {
  background: #f1f5f9;
}
</style>
