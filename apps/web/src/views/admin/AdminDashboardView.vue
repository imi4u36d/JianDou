<template>
  <section class="space-y-4">
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-slate-900">运营总览</h2>
          <p class="mt-1 text-sm text-slate-600">聚焦失败任务、进行中任务和最近系统日志。</p>
        </div>
        <button :class="secondaryButtonClass" type="button" @click="refreshAll">刷新</button>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="rounded-lg border border-slate-200 bg-white px-4 py-8 text-sm text-slate-500">
      正在读取管理台总览...
    </div>

    <template v-else-if="overview">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <article
          v-for="metric in metricCards"
          :key="metric.key"
          class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <p class="text-xs uppercase tracking-wide text-slate-500">{{ metric.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ metric.value }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ metric.hint }}</p>
        </article>
      </div>

      <div class="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h3 class="text-base font-semibold text-slate-900">异常与待处理任务</h3>
              <p class="mt-1 text-sm text-slate-600">优先展示失败任务，其次是运行中任务。</p>
            </div>
            <RouterLink to="/admin/tasks" :class="secondaryButtonClass">进入任务管理</RouterLink>
          </div>

          <div class="p-4">
            <div class="mb-3 flex items-center justify-between">
              <p class="text-sm font-medium text-slate-800">失败任务</p>
              <span class="text-xs text-slate-500">{{ overview.recentFailures.length }} 条</span>
            </div>

            <div v-if="overview.recentFailures.length" class="overflow-x-auto rounded-lg border border-slate-200">
              <table class="min-w-full text-sm">
                <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium">任务</th>
                    <th class="px-3 py-2 text-left font-medium">平台</th>
                    <th class="px-3 py-2 text-left font-medium">进度</th>
                    <th class="px-3 py-2 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="task in overview.recentFailures" :key="task.id" class="border-t border-slate-200">
                    <td class="px-3 py-2">
                      <p class="font-medium text-slate-900">{{ task.title }}</p>
                      <p class="mt-0.5 text-xs text-slate-500">{{ task.sourceFileName }}</p>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ task.platform }}</td>
                    <td class="px-3 py-2 text-slate-700">{{ task.progress }}%</td>
                    <td class="px-3 py-2 text-right">
                      <RouterLink :to="`/admin/tasks/${task.id}`" class="text-sm font-medium text-slate-700 hover:text-slate-900">查看</RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
              当前没有失败任务。
            </div>

            <div class="mt-5 mb-3 flex items-center justify-between">
              <p class="text-sm font-medium text-slate-800">运行中任务</p>
              <span class="text-xs text-slate-500">{{ overview.recentRunningTasks.length }} 条</span>
            </div>
            <div v-if="overview.recentRunningTasks.length" class="grid gap-2">
              <article
                v-for="task in overview.recentRunningTasks"
                :key="task.id"
                class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="truncate text-sm font-medium text-slate-900">{{ task.title }}</p>
                  <span class="text-xs text-slate-500">{{ task.status }} · {{ task.progress }}%</span>
                </div>
              </article>
            </div>
            <div v-else class="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
              当前没有运行中的任务。
            </div>
          </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h3 class="text-base font-semibold text-slate-900">最近系统日志</h3>
              <p class="mt-1 text-sm text-slate-600">支持按级别与阶段筛选。</p>
            </div>
          </div>

          <div class="space-y-3 p-4">
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="grid gap-1 text-xs text-slate-600">
                日志级别
                <select v-model="levelFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                  <option value="">全部级别</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARN">WARN</option>
                  <option value="INFO">INFO</option>
                </select>
              </label>
              <label class="grid gap-1 text-xs text-slate-600">
                阶段
                <select v-model="stageFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                  <option value="">全部阶段</option>
                  <option value="api">api</option>
                  <option value="worker">worker</option>
                  <option value="planning">planning</option>
                  <option value="render">render</option>
                  <option value="llm">llm</option>
                </select>
              </label>
            </div>

            <div v-if="traces.length" class="overflow-x-auto rounded-lg border border-slate-200">
              <table class="min-w-full text-sm">
                <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium">时间</th>
                    <th class="px-3 py-2 text-left font-medium">级别</th>
                    <th class="px-3 py-2 text-left font-medium">阶段</th>
                    <th class="px-3 py-2 text-left font-medium">消息</th>
                    <th class="px-3 py-2 text-right font-medium">任务</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in traces" :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`" class="border-t border-slate-200">
                    <td class="px-3 py-2 text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                    <td class="px-3 py-2">
                      <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ entry.stage }}</td>
                    <td class="px-3 py-2 text-slate-700">{{ entry.message }}</td>
                    <td class="px-3 py-2 text-right">
                      <RouterLink :to="`/admin/tasks/${entry.taskId}`" class="text-sm font-medium text-slate-700 hover:text-slate-900">打开</RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
              当前没有符合筛选条件的日志。
            </div>
          </div>
        </section>
      </div>
    </template>
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

const secondaryButtonClass =
  "inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50";

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
