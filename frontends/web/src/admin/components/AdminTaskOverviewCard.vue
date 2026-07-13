<template>
  <el-card class="surface-card admin-task-detail-card" shadow="never">
    <template #header>
      <div class="admin-task-detail-card__header">
        <h3>概览</h3>
        <div class="admin-task-detail-card__actions">
          <el-button v-if="task.status === 'FAILED'" size="small" type="warning" :disabled="actionLoading" @click="$emit('retry')">重试</el-button>
          <el-button size="small" type="danger" :disabled="actionLoading || runningTask" @click="$emit('delete')">删除</el-button>
        </div>
      </div>
    </template>

    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="任务标题" :span="2">{{ task.title }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ task.status }} · {{ task.progress }}%</el-descriptions-item>
      <el-descriptions-item label="比例">{{ task.aspectRatio }}</el-descriptions-item>
      <el-descriptions-item label="已生成结果">{{ task.completedOutputCount ?? task.outputs?.length ?? 0 }} 条</el-descriptions-item>
      <el-descriptions-item label="时长区间">{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒</el-descriptions-item>
      <el-descriptions-item label="源文件">{{ task.sourceFileName }}</el-descriptions-item>
      <el-descriptions-item label="当前阶段">{{ monitoringStageLabel }}</el-descriptions-item>
      <el-descriptions-item label="当前 Worker">{{ monitoringWorkerLabel }}</el-descriptions-item>
    </el-descriptions>

    <el-divider />
    <section class="admin-detail-section admin-detail-section-compact">
      <h4>{{ planningSummary.label }}</h4>
      <p>{{ planningSummary.title }}</p>
    </section>

    <template v-if="monitoringRows.length">
      <el-divider />
      <div class="admin-detail-section-title">
        <h4>执行监控</h4>
        <el-tag size="small">{{ monitoringStageLabel }}</el-tag>
      </div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item v-for="item in monitoringRows" :key="item.label" :label="item.label">{{ item.value }}</el-descriptions-item>
      </el-descriptions>
    </template>

    <template v-if="durationDiagnostics.length">
      <el-divider />
      <div class="admin-detail-section-title">
        <h4>镜头时长诊断</h4>
        <el-tag size="small">{{ durationDiagnostics.length }} 镜</el-tag>
      </div>
      <el-table :data="durationDiagnostics" stripe size="small">
        <el-table-column label="镜头" prop="clipIndex" width="60" />
        <el-table-column label="脚本时长">
          <template #default="{ row }">{{ formatSecondsRange((row as TaskDurationDiagnosticClip).scriptMinDurationSeconds, (row as TaskDurationDiagnosticClip).scriptMaxDurationSeconds) }}</template>
        </el-table-column>
        <el-table-column label="规划时长">
          <template #default="{ row }">{{ formatSecondsRange((row as TaskDurationDiagnosticClip).plannedMinDurationSeconds, (row as TaskDurationDiagnosticClip).plannedMaxDurationSeconds, (row as TaskDurationDiagnosticClip).plannedTargetDurationSeconds) }}</template>
        </el-table-column>
        <el-table-column label="模型请求">
          <template #default="{ row }">{{ formatSecondsValue((row as TaskDurationDiagnosticClip).requestedDurationSeconds) }}</template>
        </el-table-column>
        <el-table-column label="模型落档">
          <template #default="{ row }">{{ formatSecondsValue((row as TaskDurationDiagnosticClip).appliedDurationSeconds) }}</template>
        </el-table-column>
        <el-table-column label="实际输出">
          <template #default="{ row }">{{ formatSecondsValue((row as TaskDurationDiagnosticClip).actualDurationSeconds) }}</template>
        </el-table-column>
        <el-table-column label="来源/状态">
          <template #default="{ row }">{{ durationSourceLabel(row as TaskDurationDiagnosticClip) }} / {{ durationStatusLabel((row as TaskDurationDiagnosticClip).status) }}</template>
        </el-table-column>
      </el-table>
    </template>

    <template v-if="artifactRows.length">
      <el-divider />
      <div class="admin-detail-section-title">
        <h4>产物目录</h4>
        <el-tag size="small">{{ artifactDirectoryHint }}</el-tag>
      </div>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item v-for="item in artifactRows" :key="item.label" :label="item.label">{{ item.value }}</el-descriptions-item>
      </el-descriptions>
    </template>

    <el-divider />
    <div class="admin-detail-section-title">
      <h4>创建参数</h4>
      <el-tag size="small">时长模式 {{ requestDurationMode }}</el-tag>
    </div>
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item v-for="item in compactRequestRows" :key="item.label" :label="item.label">{{ item.value }}</el-descriptions-item>
    </el-descriptions>
    <section v-if="task.creativePrompt" class="admin-detail-text-block">
      <strong>创意提示</strong><p>{{ task.creativePrompt }}</p>
    </section>
    <section v-if="requestTranscriptPreview" class="admin-detail-text-block">
      <strong>正文预览</strong><p>{{ requestTranscriptPreview }}</p>
    </section>

    <el-alert v-if="task.errorMessage" class="admin-task-detail-error" :title="task.errorMessage" type="error" :closable="false" />

    <template v-if="task.plan?.length">
      <el-divider />
      <div class="admin-detail-section-title">
        <h4>任务计划</h4>
        <el-tag size="small">{{ task.plan.length }} 条</el-tag>
      </div>
      <el-table :data="task.plan" stripe size="small">
        <el-table-column label="序号" width="60">
          <template #default="{ row }">#{{ (row as TaskPlanClip).clipIndex }}</template>
        </el-table-column>
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <p class="font-medium">{{ (row as TaskPlanClip).title }}</p>
            <p class="admin-task-detail-muted">{{ (row as TaskPlanClip).reason }}</p>
          </template>
        </el-table-column>
        <el-table-column label="时长" width="80">
          <template #default="{ row }">{{ (row as TaskPlanClip).durationSeconds.toFixed(1) }}s</template>
        </el-table-column>
        <el-table-column label="时间窗" width="150">
          <template #default="{ row }">{{ (row as TaskPlanClip).startSeconds.toFixed(1) }}s - {{ (row as TaskPlanClip).endSeconds.toFixed(1) }}s</template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useAdminTaskDetailPresenters } from "@/admin/features/tasks/admin-task-detail-presenters";
import type {
  AdminTaskDiagnosis,
  TaskDetail,
  TaskDurationDiagnosticClip,
  TaskPlanClip,
  TaskTraceEvent,
} from "@/types";

const props = defineProps<{ task: TaskDetail; actionLoading: boolean }>();
defineEmits<{ retry: []; delete: [] }>();

const taskRef = computed<TaskDetail | null>(() => props.task);
const {
  runningTask,
  planningSummary,
  requestDurationMode,
  requestTranscriptPreview,
  compactRequestRows,
  monitoringStageLabel,
  monitoringWorkerLabel,
  artifactDirectoryHint,
  durationDiagnostics,
  monitoringRows,
  artifactRows,
  formatSecondsRange,
  formatSecondsValue,
  durationSourceLabel,
  durationStatusLabel,
} = useAdminTaskDetailPresenters({
  task: taskRef,
  traceEvents: ref<TaskTraceEvent[]>([]),
  diagnosis: ref<AdminTaskDiagnosis | null>(null),
});
</script>

<style scoped src="./admin-task-overview-card.css"></style>
