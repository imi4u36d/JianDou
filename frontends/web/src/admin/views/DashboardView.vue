<template>
  <section class="dashboard-page">
    <div class="surface-card dashboard-page__hero">
      <div class="dashboard-page__hero-meta">
        <span>{{ lastUpdatedLabel }}</span>
        <el-tag :type="overview?.modelReady ? 'success' : 'danger'" effect="plain">
          {{ overview?.modelReady ? "模型已就绪" : "模型未就绪" }}
        </el-tag>
      </div>
      <el-button :icon="Refresh" :loading="refreshing" plain @click="loadDashboard">刷新</el-button>
    </div>

    <!-- Skeleton: stat cards -->
    <template v-if="initialLoading">
      <div class="dashboard-page__stats">
        <div v-for="i in 6" :key="i" class="skeleton-card">
          <el-skeleton :rows="3" animated />
        </div>
      </div>
      <div class="dashboard-page__grid">
        <div class="skeleton-card">
          <el-skeleton :rows="5" animated />
        </div>
        <div class="skeleton-card">
          <el-skeleton :rows="5" animated />
        </div>
      </div>
    </template>

    <transition v-else name="fade" mode="out-in">
      <div key="content" class="dashboard-page__content">
        <div class="dashboard-page__stats">
          <el-card
            v-for="item in summaryCards"
            :key="item.label"
            :class="['surface-card', 'dashboard-page__stat-card', `is-${item.tone}`]"
            shadow="never"
          >
            <p>{{ item.label }}</p>
            <strong>{{ item.value }}</strong>
            <span>{{ item.note }}</span>
          </el-card>
        </div>

        <div class="dashboard-page__grid">
          <el-card class="surface-card dashboard-page__panel" shadow="never">
            <template #header>
              <div class="dashboard-page__panel-header">
                <h4>系统脉搏</h4>
              </div>
            </template>

            <div class="dashboard-page__pulse">
              <div v-for="item in pulseItems" :key="item.label" class="dashboard-page__pulse-item">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <small>{{ item.note }}</small>
              </div>
            </div>
          </el-card>

          <el-card class="surface-card dashboard-page__panel" shadow="never">
            <template #header>
              <div class="dashboard-page__panel-header">
                <h4>最近失败</h4>
              </div>
            </template>

            <div v-if="recentFailures.length" class="dashboard-page__failure-list">
              <article v-for="task in recentFailures" :key="task.id" class="dashboard-page__failure-item">
                <div class="dashboard-page__failure-main">
                  <strong>{{ task.title || task.id }}</strong>
                  <span>{{ task.id }}</span>
                </div>
                <div class="dashboard-page__failure-meta">
                  <el-tag :type="statusTagType(task.status)" effect="light">{{ statusLabel(task.status) }}</el-tag>
                  <time>{{ formatDateTime(task.updatedAt) }}</time>
                </div>
              </article>
            </div>
            <el-empty v-else description="最近没有失败任务" />
          </el-card>
        </div>

        <el-card class="surface-card dashboard-page__panel" shadow="never">
          <template #header>
            <div class="dashboard-page__panel-header">
              <h4>队列额度</h4>
            </div>
          </template>

          <el-table :data="userQueues" class="dashboard-page__table">
            <el-table-column label="队列" min-width="180">
              <template #default="{ row }">
                <div class="dashboard-page__task-cell">
                  <strong>{{ row.ownerDisplayName || row.ownerUsername || "系统任务" }}</strong>
                  <span>{{ row.ownerUsername || "system" }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="额度" min-width="90" prop="taskConcurrencyLimit" />
            <el-table-column label="运行中" min-width="90" prop="runningTaskCount" />
            <el-table-column label="排队中" min-width="90" prop="queuedTaskCount" />
            <el-table-column label="最早排队任务" min-width="240">
              <template #default="{ row }">
                <div class="dashboard-page__task-cell">
                  <strong>{{ row.oldestQueuedTaskTitle || row.oldestQueuedTaskId || "无排队" }}</strong>
                  <span>{{ row.oldestQueuedTaskId || "" }}</span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="surface-card dashboard-page__panel" shadow="never">
          <template #header>
            <div class="dashboard-page__panel-header">
              <h4>最新任务</h4>
            </div>
          </template>

          <el-table v-loading="refreshing" :data="recentTasks" class="dashboard-page__table">
            <el-table-column label="任务" min-width="240">
              <template #default="{ row }">
                <div class="dashboard-page__task-cell">
                  <strong>{{ row.title || row.id }}</strong>
                  <span>{{ row.id }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="plain">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" min-width="180">
              <template #default="{ row }">
                <div class="dashboard-page__progress-cell">
                  <el-progress :percentage="normalizePercent(row.progress)" :show-text="false" :stroke-width="8" />
                  <span>{{ normalizePercent(row.progress) }}%</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="诊断" min-width="120">
              <template #default="{ row }">
                <el-tag :type="severityTagType(row.diagnosisSeverity)" effect="light">
                  {{ severityLabel(row.diagnosisSeverity) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="阶段" min-width="120">
              <template #default="{ row }">
                {{ row.currentStage || "等待处理" }}
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { fetchAdminOverview } from "@/admin/features/dashboard/services/dashboardService";
import { fetchAdminUsers } from "@/admin/features/users/services/userService";
import type { AdminOverviewResponse, AdminTaskListItem, AdminUser, TaskStatus } from "@/types";

const loading = ref(false);
const refreshing = ref(false);
const initialLoading = ref(true);
const overview = ref<AdminOverviewResponse | null>(null);
const users = ref<AdminUser[]>([]);

const summaryCards = computed(() => {
  const counts = overview.value?.counts;
  return [
    { label: "用户", value: users.value.length, note: "全部账号", tone: "accent" },
    { label: "任务", value: counts?.totalTasks ?? 0, note: "总数", tone: "secondary" },
    { label: "成功", value: counts?.completedTasks ?? 0, note: "已完成", tone: "success" },
    { label: "失败", value: counts?.failedTasks ?? 0, note: "待排查", tone: "danger" },
    { label: "运行", value: counts?.runningTasks ?? 0, note: "执行中", tone: "warning" },
    { label: "排队", value: counts?.queuedTasks ?? 0, note: "等待中", tone: "neutral" }
  ];
});

const pulseItems = computed(() => {
  const counts = overview.value?.counts;
  const activeUsers = users.value.filter((user) => user.status === "ACTIVE").length;
  const disabledUsers = users.value.filter((user) => user.status === "DISABLED").length;
  const adminUsers = users.value.filter((user) => user.role === "ADMIN").length;
  return [
    { label: "活跃用户", value: activeUsers, note: "可登录" },
    { label: "管理员", value: adminUsers, note: "后台" },
    { label: "禁用账号", value: disabledUsers, note: "已暂停" },
    { label: "在线 Worker", value: overview.value?.workers?.onlineCount ?? 0, note: "工作节点" },
    { label: "队列积压", value: overview.value?.queue?.queueLength ?? 0, note: "未开始" },
    { label: "高风险", value: counts?.highRiskTasks ?? 0, note: "需关注" },
    { label: "Trace", value: overview.value?.recentTraceCount ?? 0, note: "近期记录" },
    { label: "平均进度", value: `${counts?.averageProgress ?? 0}%`, note: "整体" }
  ];
});

const recentTasks = computed<AdminTaskListItem[]>(() => overview.value?.recentTasks ?? []);
const recentFailures = computed<AdminTaskListItem[]>(() => overview.value?.recentFailures ?? []);
const userQueues = computed(() => overview.value?.queue?.userQueues ?? []);
const lastUpdatedLabel = computed(() => formatDateTime(overview.value?.generatedAt));

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "未记录";
  }
  return date.toLocaleString("zh-CN");
}

function normalizePercent(value: number | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function statusLabel(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "排队中";
    case "PAUSED":
      return "已暂停";
    case "ANALYZING":
      return "分析中";
    case "PLANNING":
      return "编排中";
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

function statusTagType(status: TaskStatus): "" | "success" | "warning" | "info" | "danger" {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "FAILED":
      return "danger";
    case "RENDERING":
    case "ANALYZING":
    case "PLANNING":
      return "warning";
    default:
      return "info";
  }
}

function severityLabel(severity?: AdminTaskListItem["diagnosisSeverity"]) {
  switch (severity) {
    case "high":
      return "高风险";
    case "medium":
      return "中风险";
    case "low":
      return "低风险";
    case "info":
      return "正常";
    default:
      return "待分析";
  }
}

function severityTagType(severity?: AdminTaskListItem["diagnosisSeverity"]): "" | "success" | "warning" | "info" | "danger" {
  switch (severity) {
    case "high":
      return "danger";
    case "medium":
      return "warning";
    case "low":
      return "success";
    default:
      return "info";
  }
}

async function loadDashboard() {
  if (initialLoading.value) {
    loading.value = true;
  } else {
    refreshing.value = true;
  }
  const [overviewResult, usersResult] = await Promise.allSettled([fetchAdminOverview(), fetchAdminUsers()]);
  const errors: string[] = [];

  if (overviewResult.status === "fulfilled") {
    overview.value = overviewResult.value ?? null;
  } else {
    errors.push(overviewResult.reason instanceof Error ? overviewResult.reason.message : "读取任务概览失败");
  }

  if (usersResult.status === "fulfilled") {
    users.value = usersResult.value?.items ?? [];
  } else {
    errors.push(usersResult.reason instanceof Error ? usersResult.reason.message : "读取用户统计失败");
  }

  if (errors.length) {
    ElMessage.error(errors.join("；"));
  }
  loading.value = false;
  refreshing.value = false;
  initialLoading.value = false;
}

onMounted(async () => {
  await loadDashboard();
});
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 20px;
}

.dashboard-page > *,
.dashboard-page__content,
.dashboard-page__hero,
.dashboard-page__stats,
.dashboard-page__grid,
.dashboard-page__panel {
  min-width: 0;
  max-width: 100%;
}

.dashboard-page__alert {
  margin-bottom: 4px;
}

.dashboard-page__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 18px;
}

.dashboard-page__hero h3,
.dashboard-page__panel-header h4 {
  margin: 0;
  font-family: inherit;
}

.dashboard-page__hero-copy {
  margin: 10px 0 0;
  max-width: 620px;
  color: var(--jd-text-soft);
}

.dashboard-page__hero-actions {
  display: grid;
  justify-items: end;
  gap: 12px;
}

.dashboard-page__hero-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.dashboard-page__stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
}

.dashboard-page__stat-card,
.dashboard-page__panel {
  border-radius: 24px;
}

.dashboard-page__stat-card :deep(.el-card__body) {
  display: grid;
  gap: 8px;
}

.dashboard-page__stat-card p,
.dashboard-page__stat-card span {
  margin: 0;
  color: var(--jd-text-soft);
}

.dashboard-page__stat-card strong {
  font-family: inherit;
  font-size: 2rem;
}

.dashboard-page__stat-card.is-accent {
  background: linear-gradient(180deg, rgba(0, 169, 187, 0.15), rgba(255, 255, 255, 0.8));
}

.dashboard-page__stat-card.is-secondary {
  background: linear-gradient(180deg, rgba(47, 122, 136, 0.14), rgba(255, 255, 255, 0.8));
}

.dashboard-page__stat-card.is-success {
  background: linear-gradient(180deg, rgba(103, 194, 58, 0.14), rgba(255, 255, 255, 0.8));
}

.dashboard-page__stat-card.is-danger {
  background: linear-gradient(180deg, rgba(191, 78, 78, 0.14), rgba(255, 255, 255, 0.8));
}

.dashboard-page__stat-card.is-warning {
  background: linear-gradient(180deg, rgba(230, 162, 60, 0.14), rgba(255, 255, 255, 0.8));
}

.dashboard-page__stat-card.is-neutral {
  background: linear-gradient(180deg, rgba(144, 147, 153, 0.12), rgba(255, 255, 255, 0.8));
}

.dashboard-page__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 20px;
}

.dashboard-page__panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dashboard-page__pulse {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.dashboard-page__pulse-item {
  display: grid;
  gap: 4px;
  padding: 16px;
  border: 1px solid var(--jd-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.66);
}

.dashboard-page__pulse-item span,
.dashboard-page__pulse-item small,
.dashboard-page__task-cell span,
.dashboard-page__failure-main span,
.dashboard-page__failure-meta time {
  color: var(--jd-text-soft);
}

.dashboard-page__pulse-item strong {
  font-size: 1.3rem;
  font-family: inherit;
}

.dashboard-page__failure-list {
  display: grid;
  gap: 12px;
}

.dashboard-page__failure-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(191, 78, 78, 0.14);
  border-radius: 18px;
  background: rgba(191, 78, 78, 0.05);
}

.dashboard-page__failure-main,
.dashboard-page__task-cell {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.dashboard-page__failure-main strong,
.dashboard-page__task-cell strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-page__failure-meta {
  display: grid;
  justify-items: end;
  gap: 8px;
}

.dashboard-page__table {
  width: 100%;
}

.dashboard-page__progress-cell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

@media (max-width: 1400px) {
  .dashboard-page__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dashboard-page__pulse {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .dashboard-page__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-page__hero {
    flex-direction: column;
  }

  .dashboard-page__hero-actions,
  .dashboard-page__hero-meta {
    width: 100%;
    justify-items: start;
    justify-content: flex-start;
  }

  .dashboard-page__stats,
  .dashboard-page__pulse {
    grid-template-columns: 1fr;
  }

  .dashboard-page__failure-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-page__failure-meta {
    justify-items: start;
  }
}
</style>
