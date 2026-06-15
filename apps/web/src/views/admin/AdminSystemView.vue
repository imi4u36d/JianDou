<template>
  <section class="admin-page admin-system-view">
    <div class="admin-panel px-5 py-5">
      <div class="admin-heading-block">
        <p class="admin-eyebrow">System</p>
        <h2 class="admin-title">系统配置</h2>
        <p class="admin-subtitle">查看运行时、模型和日志，支持按条件筛选排障信息。</p>
      </div>
    </div>

    <ModelStatusStrip />

    <section class="admin-panel overflow-hidden">
      <div class="admin-panel-header">
        <div>
          <h3 class="text-base font-semibold text-slate-900">运行时日志</h3>
          <p class="mt-1 text-sm text-slate-600">按任务、级别、阶段筛选最新 trace 事件。</p>
        </div>
        <button class="admin-btn-secondary" type="button" @click="loadTraces">
          刷新
        </button>
      </div>

      <div class="space-y-4 p-5">
        <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <label class="grid gap-1 text-xs text-slate-600">
            任务 ID
            <input v-model="taskIdFilter" class="admin-field" placeholder="可选" type="text" />
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            级别
            <AppSelect v-model="levelFilter" :options="levelFilterOptions" variant="admin" />
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            阶段
            <AppSelect v-model="stageFilter" :options="stageFilterOptions" variant="admin" />
          </label>
          <label class="grid gap-1 text-xs text-slate-600">
            关键词
            <input v-model="keywordFilter" class="admin-field" placeholder="消息关键词" type="text" />
          </label>
        </div>

        <div v-if="loading" class="admin-panel-soft px-3 py-6 text-center text-sm text-slate-500">
          正在加载日志...
        </div>
        <div v-else-if="traces.length === 0" class="admin-empty">
          当前没有日志。
        </div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>任务</th>
                <th>级别</th>
                <th>阶段</th>
                <th>事件</th>
                <th>消息</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in traces" :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`">
                <td class="text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                <td>{{ entry.taskTitle || entry.taskId }}</td>
                <td>
                  <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                </td>
                <td>{{ entry.stage }}</td>
                <td class="break-all text-xs text-slate-500">{{ entry.event }}</td>
                <td>{{ entry.message }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
/**
 * 管理系统页面组件。
 */
import { onMounted, ref, watch } from "vue";
import { fetchAdminTraces } from "@/features/admin";
import AppSelect from "@/components/common/AppSelect.vue";
import ModelStatusStrip from "@/components/ModelStatusStrip.vue";
import { messageApi } from "@/composables/useMessage";
import type { AppSelectOption } from "@/components/common/app-select";
import type { AdminTraceEvent } from "@/types";

const traces = ref<AdminTraceEvent[]>([]);
const loading = ref(false);
const taskIdFilter = ref("");
const levelFilter = ref("");
const stageFilter = ref("");
const keywordFilter = ref("");
let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null;
const levelFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "ERROR", value: "ERROR" },
  { label: "WARN", value: "WARN" },
  { label: "INFO", value: "INFO" },
];
const stageFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "api", value: "api" },
  { label: "worker", value: "worker" },
  { label: "planning", value: "planning" },
  { label: "render", value: "render" },
  { label: "llm", value: "llm" },
];

/**
 * 格式化时间。
 * @param value 待处理的值
 */
function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

/**
 * 处理日志Level样式类。
 * @param level level值
 */
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
  try {
    traces.value = (await fetchAdminTraces({
      limit: 30,
      taskId: taskIdFilter.value || undefined,
      level: levelFilter.value || undefined,
      stage: stageFilter.value || undefined,
      q: keywordFilter.value || undefined,
    })) ?? [];
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "读取日志失败");
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

<style scoped>
.admin-system-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-system-view :deep(.admin-panel-soft) {
  border: 1px solid #dbe4ee;
  background: #f8fafc;
}

.admin-system-view :deep(.admin-table th) {
  background: #f1f5f9;
}
</style>
