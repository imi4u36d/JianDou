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

    <transition name="fade" mode="out-in">
      <div v-if="!initialLoading" key="content" class="dashboard-page__content">
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
                  <strong>{{ row.ownerUsername }}</strong>
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
import { Refresh } from "@element-plus/icons-vue";
import { useAdminDashboard } from "@/admin/composables/useAdminDashboard";
import {
  dashboardSeverityLabel as severityLabel,
  dashboardSeverityTagType as severityTagType,
  dashboardStatusLabel as statusLabel,
  dashboardStatusTagType as statusTagType,
  formatDashboardDateTime as formatDateTime,
  normalizeDashboardPercent as normalizePercent,
} from "@/admin/features/dashboard/dashboard-presenters";

const {
  refreshing, initialLoading, overview, summaryCards, pulseItems, recentTasks,
  recentFailures, userQueues, lastUpdatedLabel, loadDashboard,
} = useAdminDashboard();
</script>

<style scoped src="./dashboard-view.css"></style>
