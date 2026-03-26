<template>
  <section class="space-y-4">
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-900">系统配置</h2>
      <p class="mt-1 text-sm text-slate-600">查看运行时、模型和日志，支持按条件筛选排障信息。</p>
    </div>

    <ModelStatusStrip />

    <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h3 class="text-base font-semibold text-slate-900">运行时日志</h3>
          <p class="mt-1 text-sm text-slate-600">按任务、级别、阶段筛选最新 trace 事件。</p>
        </div>
        <button class="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50" type="button" @click="loadTraces">
          刷新
        </button>
      </div>

      <div class="space-y-3 p-4">
        <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <label class="grid gap-1 text-xs text-slate-600">
            任务 ID
            <input v-model="taskIdFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" placeholder="可选" type="text" />
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            级别
            <select v-model="levelFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
              <option value="">全部</option>
              <option value="ERROR">ERROR</option>
              <option value="WARN">WARN</option>
              <option value="INFO">INFO</option>
            </select>
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            阶段
            <select v-model="stageFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
              <option value="">全部</option>
              <option value="api">api</option>
              <option value="worker">worker</option>
              <option value="planning">planning</option>
              <option value="render">render</option>
              <option value="llm">llm</option>
            </select>
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            关键词
            <input v-model="keywordFilter" class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" placeholder="消息关键词" type="text" />
          </label>
        </div>

        <div v-if="loading" class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">
          正在加载日志...
        </div>
        <div v-else-if="errorMessage" class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {{ errorMessage }}
        </div>
        <div v-else-if="traces.length === 0" class="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
          当前没有日志。
        </div>
        <div v-else class="overflow-x-auto rounded-lg border border-slate-200">
          <table class="min-w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-3 py-2 text-left font-medium">时间</th>
                <th class="px-3 py-2 text-left font-medium">任务</th>
                <th class="px-3 py-2 text-left font-medium">级别</th>
                <th class="px-3 py-2 text-left font-medium">阶段</th>
                <th class="px-3 py-2 text-left font-medium">事件</th>
                <th class="px-3 py-2 text-left font-medium">消息</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in traces" :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`" class="border-t border-slate-200">
                <td class="px-3 py-2 text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                <td class="px-3 py-2 text-slate-700">{{ entry.taskTitle || entry.taskId }}</td>
                <td class="px-3 py-2">
                  <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                </td>
                <td class="px-3 py-2 text-slate-700">{{ entry.stage }}</td>
                <td class="px-3 py-2 break-all text-xs text-slate-500">{{ entry.event }}</td>
                <td class="px-3 py-2 text-slate-700">{{ entry.message }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { fetchAdminTraces } from "@/api/admin";
import ModelStatusStrip from "@/components/ModelStatusStrip.vue";
import type { AdminTraceEvent } from "@/types";

const traces = ref<AdminTraceEvent[]>([]);
const loading = ref(false);
const errorMessage = ref("");
const taskIdFilter = ref("");
const levelFilter = ref("");
const stageFilter = ref("");
const keywordFilter = ref("");
let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null;

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

async function loadTraces() {
  loading.value = true;
  errorMessage.value = "";
  try {
    traces.value = await fetchAdminTraces({
      limit: 30,
      taskId: taskIdFilter.value || undefined,
      level: levelFilter.value || undefined,
      stage: stageFilter.value || undefined,
      q: keywordFilter.value || undefined,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取日志失败";
  } finally {
    loading.value = false;
  }
}

watch([taskIdFilter, levelFilter, stageFilter, keywordFilter], () => {
  if (refreshDebounceTimer) {
    clearTimeout(refreshDebounceTimer);
  }
  refreshDebounceTimer = setTimeout(() => {
    void loadTraces();
  }, 300);
});

onMounted(async () => {
  await loadTraces();
});
</script>
