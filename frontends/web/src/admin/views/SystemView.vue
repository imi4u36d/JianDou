<template>
  <section class="system-page">
    <ModelStatusStrip />

    <el-card class="surface-card system-page__card" shadow="never">
      <template #header>
        <div class="system-page__toolbar">
          <span class="system-page__toolbar-spacer" aria-hidden="true"></span>
          <el-button :icon="Refresh" :loading="loading" @click="loadTraces">刷新</el-button>
        </div>
      </template>

      <div class="system-page__body">
        <div class="system-page__filters">
          <label class="system-page__field">
            <span>任务 ID</span>
            <el-input v-model="taskIdFilter" placeholder="可选" />
          </label>
          <label class="system-page__field">
            <span>级别</span>
            <el-select v-model="levelFilter" placeholder="全部">
              <el-option v-for="opt in levelFilterOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </label>
          <label class="system-page__field">
            <span>阶段</span>
            <el-select v-model="stageFilter" placeholder="全部">
              <el-option v-for="opt in stageFilterOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </label>
          <label class="system-page__field">
            <span>关键词</span>
            <el-input v-model="keywordFilter" placeholder="消息关键词" />
          </label>
        </div>

        <el-alert v-if="loading" :closable="false" title="加载中" type="info" show-icon />
        <el-empty v-else-if="traces.length === 0" description="暂无日志" />
        <el-table v-else :data="traces" stripe size="small">
          <el-table-column label="时间" min-width="160" prop="timestamp">
            <template #default="{ row }">{{ formatTime((row as AdminTraceEvent).timestamp) }}</template>
          </el-table-column>
          <el-table-column label="任务" min-width="140">
            <template #default="{ row }">{{ (row as AdminTraceEvent).taskTitle || (row as AdminTraceEvent).taskId }}</template>
          </el-table-column>
          <el-table-column label="级别" width="70">
            <template #default="{ row }">
              <el-tag :type="logLevelTag((row as AdminTraceEvent).level)" effect="light" size="small">{{ (row as AdminTraceEvent).level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="阶段" width="90" prop="stage" />
          <el-table-column label="事件" min-width="120">
            <template #default="{ row }">
              <span class="system-page__muted">{{ (row as AdminTraceEvent).event }}</span>
            </template>
          </el-table-column>
          <el-table-column label="消息" min-width="200" prop="message" />
        </el-table>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { getJson } from "@/api/client";
import ModelStatusStrip from "@/admin/components/ModelStatusStrip.vue";
import type { AdminTraceEvent } from "@/types";

const traces = ref<AdminTraceEvent[]>([]);
const loading = ref(false);
const taskIdFilter = ref("");
const levelFilter = ref("");
const stageFilter = ref("");
const keywordFilter = ref("");
let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const levelFilterOptions = [
  { label: "全部", value: "" },
  { label: "ERROR", value: "ERROR" },
  { label: "WARN", value: "WARN" },
  { label: "INFO", value: "INFO" },
];

const stageFilterOptions = [
  { label: "全部", value: "" },
  { label: "api", value: "api" },
  { label: "worker", value: "worker" },
  { label: "planning", value: "planning" },
  { label: "render", value: "render" },
  { label: "llm", value: "llm" },
];

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function logLevelTag(level: string) {
  if (level === "ERROR") return "danger";
  if (level === "WARN") return "warning";
  return "info";
}

async function loadTraces() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    params.set("limit", "30");
    if (taskIdFilter.value) params.set("taskId", taskIdFilter.value);
    if (levelFilter.value) params.set("level", levelFilter.value);
    if (stageFilter.value) params.set("stage", stageFilter.value);
    if (keywordFilter.value) params.set("q", keywordFilter.value);
    traces.value = (await getJson<AdminTraceEvent[]>(`/admin/traces?${params.toString()}`)) ?? [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取日志失败");
  } finally {
    loading.value = false;
  }
}

watch([taskIdFilter, levelFilter, stageFilter, keywordFilter], () => {
  if (refreshDebounceTimer) clearTimeout(refreshDebounceTimer);
  refreshDebounceTimer = setTimeout(() => { void loadTraces(); }, 300);
});

onMounted(async () => {
  await loadTraces();
});
</script>

<style scoped>
.system-page {
  display: grid;
  gap: 18px;
}

.system-page__card {
  min-width: 0;
}

.system-page__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.system-page__toolbar-spacer {
  flex: 1 1 auto;
  min-width: 0;
}

.system-page__body {
  display: grid;
  gap: 16px;
}

.system-page__filters {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 10px;
}

.system-page__field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.system-page__field span,
.system-page__muted {
  color: var(--jd-text-soft);
  font-size: 0.84rem;
}

.system-page__field span {
  font-weight: 760;
}

@media (max-width: 1024px) {
  .system-page__filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .system-page__filters {
    grid-template-columns: 1fr;
  }

  .system-page__toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
