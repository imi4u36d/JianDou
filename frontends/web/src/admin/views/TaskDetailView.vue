<template>
  <section>
    <div v-if="loading" class="admin-task-detail-loading">加载中</div>

    <template v-else-if="task">
      <div class="admin-task-detail-grid">
        <AdminTaskOverviewCard
          :task="task"
          :action-loading="actionLoading"
          @retry="retryTaskAction"
          @delete="deleteTaskAction"
        />

        <el-card class="surface-card admin-task-detail-card" shadow="never">
          <template #header>
            <div class="admin-task-detail-card__header">
              <h3>日志</h3>
              <div class="admin-task-detail-card__actions">
                <el-button size="small" @click="refresh">刷新</el-button>
                <el-button
                  size="small"
                  circle
                  :aria-label="traceExpanded ? '收起日志' : '展开日志'"
                  :title="traceExpanded ? '收起' : '展开'"
                  @click="traceExpanded = !traceExpanded"
                >
                  <el-icon>
                    <ArrowUp v-if="traceExpanded" />
                    <ArrowDown v-else />
                  </el-icon>
                </el-button>
              </div>
            </div>
          </template>

          <div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="当前重点">
                {{ traceFocus?.message || "暂无日志" }}
                <template v-if="traceFocus?.timestamp">
                  <br><span class="admin-task-detail-muted">{{ formatTime(traceFocus.timestamp) }}</span>
                </template>
              </el-descriptions-item>
            </el-descriptions>

            <el-table v-if="traceEvents.length" class="admin-task-detail-trace-table" :data="traceExpanded ? orderedTraceEvents : tracePreview" stripe size="small">
              <el-table-column label="时间" min-width="160">
                <template #default="{ row }">{{ formatTime((row as TaskTraceEvent).timestamp) }}</template>
              </el-table-column>
              <el-table-column label="级别" width="70">
                <template #default="{ row }">
                  <el-tag :type="logLevelTag((row as TaskTraceEvent).level)" effect="light" size="small">{{ (row as TaskTraceEvent).level }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="阶段" width="90">
                <template #default="{ row }">{{ (row as TaskTraceEvent).stage }}</template>
              </el-table-column>
              <el-table-column label="消息" min-width="200">
                <template #default="{ row }">{{ (row as TaskTraceEvent).message }}</template>
              </el-table-column>
              <el-table-column label="事件" min-width="120">
                <template #default="{ row }">
                  <span class="admin-task-detail-muted">{{ (row as TaskTraceEvent).event }}</span>
                </template>
              </el-table-column>
            </el-table>
            <div v-else class="admin-task-detail-empty">暂无日志</div>
          </div>
        </el-card>
      </div>

      <el-card v-if="diagnosis" class="surface-card admin-task-detail-diagnosis" shadow="never">
        <template #header>
          <div class="admin-task-detail-diagnosis__head">
            <div>
              <h3>诊断</h3>
              <p>{{ diagnosis.summary }}</p>
            </div>
            <el-tag :type="diagnosisSeverityTag" effect="light">{{ diagnosisSeverityLabel }}</el-tag>
          </div>
        </template>
        <div class="admin-task-detail-diagnosis__grid">
          <div class="admin-task-detail-finding-list">
            <article v-for="finding in diagnosis.findings" :key="finding.code" class="admin-task-detail-finding">
              <div class="admin-task-detail-finding__head">
                <p>{{ finding.title }}</p>
                <el-tag :type="findingSeverityTag(finding.severity)" effect="light" size="small">{{ diagnosisSeverityText(finding.severity) }}</el-tag>
              </div>
              <p class="admin-task-detail-finding__detail">{{ finding.detail }}</p>
            </article>
          </div>
          <div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="推荐动作">{{ diagnosisRecoveryAction }}</el-descriptions-item>
              <el-descriptions-item label="恢复起点">{{ diagnosisRecoveryStart }}</el-descriptions-item>
              <el-descriptions-item label="连续性摘要">{{ diagnosisContinuitySummary }}</el-descriptions-item>
              <el-descriptions-item label="队列状态">{{ diagnosisQueueSummary }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-card>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ArrowDown, ArrowUp } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import {
  deleteAdminTask,
  fetchAdminTask,
  fetchAdminTaskDiagnosis,
  fetchAdminTaskTrace,
  retryAdminTask,
} from "@/admin/features/tasks/services/taskService";
import { useAdminTaskDetailPresenters } from "@/admin/features/tasks/admin-task-detail-presenters";
import AdminTaskOverviewCard from "@/admin/components/AdminTaskOverviewCard.vue";
import type { AdminTaskDiagnosis, TaskDetail, TaskTraceEvent } from "@/types";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const diagnosis = ref<AdminTaskDiagnosis | null>(null);
const loading = ref(true);
const actionLoading = ref(false);
const traceExpanded = ref(false);

const taskId = computed(() => String(route.params.id || ""));
const {
  orderedTraceEvents,
  traceFocus,
  tracePreview,
  diagnosisSeverityLabel,
  diagnosisSeverityTag,
  diagnosisRecoveryAction,
  diagnosisRecoveryStart,
  diagnosisContinuitySummary,
  diagnosisQueueSummary,
  logLevelTag,
  findingSeverityTag,
  diagnosisSeverityText,
  formatTime,
} = useAdminTaskDetailPresenters({ task, traceEvents, diagnosis });

async function loadTask() {
  task.value = await fetchAdminTask(taskId.value);
}

async function loadTrace() {
  traceEvents.value = await fetchAdminTaskTrace(taskId.value, 500);
}

async function loadDiagnosis() {
  diagnosis.value = await fetchAdminTaskDiagnosis(taskId.value);
}

async function refresh() {
  loading.value = true;
  try {
    await Promise.all([loadTask(), loadTrace(), loadDiagnosis()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取任务详情失败");
  } finally {
    loading.value = false;
  }
}

async function retryTaskAction() {
  actionLoading.value = true;
  try {
    await retryAdminTask(taskId.value);
    await refresh();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "重试失败");
  } finally {
    actionLoading.value = false;
  }
}

async function deleteTaskAction() {
  try {
    await ElMessageBox.confirm(`删除后不可恢复，确认删除任务 ${task.value?.title || taskId.value} 吗？`, "删除任务", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      confirmButtonClass: "el-button--danger",
    });
  } catch {
    return;
  }
  actionLoading.value = true;
  try {
    await deleteAdminTask(taskId.value);
    await router.push("/admin/tasks");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "删除失败");
  } finally {
    actionLoading.value = false;
  }
}

watch(taskId, () => {
  traceExpanded.value = false;
  void refresh();
}, { immediate: true });
</script>

<style scoped src="./task-detail-view.css"></style>
