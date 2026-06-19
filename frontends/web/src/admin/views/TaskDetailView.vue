<template>
  <section>
    <div v-if="loading" class="py-8 text-center text-sm text-slate-500">正在读取任务详情...</div>

    <template v-else-if="task">
      <div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <el-card class="surface-card admin-task-detail-card" shadow="never">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <h3 class="text-base font-semibold text-slate-900">基础信息</h3>
              <div class="flex flex-wrap gap-2">
                <el-button v-if="task?.status === 'FAILED'" type="warning" :disabled="actionLoading" @click="retryTaskAction">重试</el-button>
                <el-button type="danger" :disabled="actionLoading || runningTask" @click="deleteTaskAction">删除</el-button>
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

          <h4 class="mb-3 text-sm font-semibold text-slate-900">{{ planningSummary.label }}</h4>
          <p class="text-sm text-slate-700">{{ planningSummary.title }}</p>

          <el-divider v-if="monitoringRows.length" />

          <div v-if="monitoringRows.length">
            <div class="mb-3 flex items-center gap-2">
              <h4 class="text-sm font-semibold text-slate-900">执行监控</h4>
              <el-tag size="small">{{ monitoringStageLabel }}</el-tag>
            </div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item v-for="item in monitoringRows" :key="item.label" :label="item.label">
                {{ item.value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <el-divider v-if="durationDiagnostics.length" />

          <div v-if="durationDiagnostics.length">
            <div class="mb-3 flex items-center gap-2">
              <h4 class="text-sm font-semibold text-slate-900">镜头时长诊断</h4>
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
          </div>

          <el-divider v-if="artifactRows.length" />

          <div v-if="artifactRows.length">
            <div class="mb-3 flex items-center gap-2">
              <h4 class="text-sm font-semibold text-slate-900">产物目录</h4>
              <el-tag size="small">{{ artifactDirectoryHint }}</el-tag>
            </div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item v-for="item in artifactRows" :key="item.label" :label="item.label">
                {{ item.value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <el-divider />

          <div>
            <div class="mb-3 flex items-center gap-2">
              <h4 class="text-sm font-semibold text-slate-900">创建参数</h4>
              <el-tag size="small">时长模式 {{ requestDurationMode }}</el-tag>
            </div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item v-for="item in compactRequestRows" :key="item.label" :label="item.label">
                {{ item.value }}
              </el-descriptions-item>
            </el-descriptions>
            <el-alert v-if="task.creativePrompt" class="mt-3" :title="task.creativePrompt" type="info" :closable="false" />
            <el-alert v-if="requestTranscriptPreview" class="mt-3" :title="requestTranscriptPreview" type="info" :closable="false" />
          </div>

          <el-alert v-if="task.errorMessage" class="mt-4" :title="task.errorMessage" type="error" :closable="false" />

          <el-divider v-if="task.plan?.length" />

          <div v-if="task.plan?.length">
            <div class="mb-3 flex items-center gap-2">
              <h4 class="text-sm font-semibold text-slate-900">任务计划</h4>
              <el-tag size="small">{{ task.plan.length }} 条</el-tag>
            </div>
            <el-table :data="task.plan" stripe size="small">
              <el-table-column label="序号" width="60">
                <template #default="{ row }">#{{ (row as TaskPlanClip).clipIndex }}</template>
              </el-table-column>
              <el-table-column label="标题" min-width="200">
                <template #default="{ row }">
                  <p class="font-medium">{{ (row as TaskPlanClip).title }}</p>
                  <p class="text-xs text-slate-500">{{ (row as TaskPlanClip).reason }}</p>
                </template>
              </el-table-column>
              <el-table-column label="时长" width="80">
                <template #default="{ row }">{{ (row as TaskPlanClip).durationSeconds.toFixed(1) }}s</template>
              </el-table-column>
              <el-table-column label="时间窗" width="150">
                <template #default="{ row }">{{ (row as TaskPlanClip).startSeconds.toFixed(1) }}s - {{ (row as TaskPlanClip).endSeconds.toFixed(1) }}s</template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <el-card class="surface-card admin-task-detail-card" shadow="never">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 class="text-base font-semibold text-slate-900">任务日志</h3>
              </div>
              <div class="flex flex-wrap gap-2">
                <el-button size="small" @click="refresh">刷新</el-button>
                <el-button size="small" @click="traceExpanded = !traceExpanded">{{ traceExpanded ? "收起日志" : "展开日志" }}</el-button>
              </div>
            </div>
          </template>

          <div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="当前重点">
                {{ traceFocus?.message || "暂无日志" }}
                <template v-if="traceFocus?.timestamp">
                  <br><span class="text-xs text-slate-500">{{ formatTime(traceFocus.timestamp) }}</span>
                </template>
              </el-descriptions-item>
            </el-descriptions>

            <el-table v-if="traceEvents.length" class="mt-3" :data="traceExpanded ? orderedTraceEvents : tracePreview" stripe size="small">
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
                  <span class="text-xs text-slate-500">{{ (row as TaskTraceEvent).event }}</span>
                </template>
              </el-table-column>
            </el-table>
            <div v-else class="py-4 text-center text-sm text-slate-500">当前没有日志。</div>
          </div>
        </el-card>
      </div>

      <el-card v-if="diagnosis" class="surface-card mt-4" shadow="never">
        <template #header>
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 class="text-base font-semibold text-slate-900">任务诊断</h3>
              <p class="mt-1 text-sm text-slate-600">{{ diagnosis.summary }}</p>
            </div>
            <el-tag :type="diagnosisSeverityTag" effect="light">{{ diagnosisSeverityLabel }}</el-tag>
          </div>
        </template>
        <div class="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div class="space-y-3">
            <el-card v-for="finding in diagnosis.findings" :key="finding.code" shadow="never" class="border">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-semibold">{{ finding.title }}</p>
                <el-tag :type="findingSeverityTag(finding.severity)" effect="light" size="small">{{ diagnosisSeverityText(finding.severity) }}</el-tag>
              </div>
              <p class="mt-2 text-sm text-slate-700">{{ finding.detail }}</p>
            </el-card>
          </div>
          <div class="space-y-3">
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
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import {
  deleteAdminTask,
  fetchAdminTask,
  fetchAdminTaskDiagnosis,
  fetchAdminTaskTrace,
  retryAdminTask,
} from "@/admin/features/tasks/services/taskService";
import type { AdminTaskDiagnosis, TaskDetail, TaskDurationDiagnosticClip, TaskPlanClip, TaskTraceEvent } from "@/types";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const diagnosis = ref<AdminTaskDiagnosis | null>(null);
const loading = ref(true);
const actionLoading = ref(false);
const traceExpanded = ref(false);

const taskId = computed(() => String(route.params.id || ""));
const runningTask = computed(() => Boolean(task.value && (task.value.status === "ANALYZING" || task.value.status === "PLANNING" || task.value.status === "RENDERING")));

const planningSummary = computed(() => {
  if (!task.value?.plan?.length) {
    return { label: "未生成计划", title: "暂无计划", detail: "计划未生成。" };
  }
  if (task.value.hasTimedTranscript) {
    return { label: "时间轴输入", title: "按时间轴推进", detail: "按时间轴推进。" };
  }
  return { label: "任务生成", title: "标准生成链路", detail: "标准生成链路。" };
});

const requestSnapshot = computed(() => {
  return (task.value?.requestSnapshot ?? task.value) as Record<string, unknown>;
});

const requestDurationMode = computed(() => formatTaskDurationMode(requestSnapshot.value));

const requestTranscriptPreview = computed(() => previewTaskTranscript(requestSnapshot.value));

const requestRows = computed(() => {
  if (!task.value) return [];
  return [
    { label: "文本模型", value: formatTaskModelValue(requestSnapshot.value.textAnalysisModel) },
    { label: "关键帧模型", value: formatTaskModelValue(requestSnapshot.value.imageModel) },
    { label: "视频模型", value: formatTaskModelValue(requestSnapshot.value.videoModel) },
    { label: "清晰度 / 画幅", value: formatTaskModelValue(requestSnapshot.value.videoSize) },
    { label: "输出数量", value: formatTaskOutputCount(requestSnapshot.value) },
    { label: "请求时长", value: formatTaskRequestedDuration(requestSnapshot.value) },
    { label: "生效时长", value: formatTaskResolvedDuration(task.value) },
    { label: "任务 Seed", value: taskSeedLabel.value },
    { label: "提前停止视频生成", value: formatTaskStopBeforeVideoGeneration(requestSnapshot.value) },
    { label: "文本输入", value: formatTaskTranscriptSummary(requestSnapshot.value) },
  ];
});

const compactRequestRows = computed(() => requestRows.value.slice(0, 6));

const taskSeedLabel = computed(() => {
  const topLevelSeed = task.value?.taskSeed;
  if (typeof topLevelSeed === "number" && Number.isFinite(topLevelSeed)) {
    return String(Math.trunc(topLevelSeed));
  }
  return formatTaskSeed(requestSnapshot.value);
});

const monitoringStageLabel = computed(() => formatMonitoringValue(task.value?.monitoring?.currentStage));
const monitoringWorkerLabel = computed(() => formatMonitoringValue(task.value?.monitoring?.activeWorkerInstanceId));
const artifactDirectories = computed(() => task.value?.artifactDirectories ?? task.value?.monitoring?.artifactDirectories ?? null);
const artifactDirectoryHint = computed(() => formatMonitoringValue(artifactDirectories.value?.baseRelativeDir));
const durationDiagnostics = computed(() => task.value?.durationDiagnostics ?? []);

const monitoringRows = computed(() => {
  const monitoring = task.value?.monitoring;
  if (!monitoring) return [];
  return [
    { label: "Attempt 状态", value: formatMonitoringValue(monitoring.activeAttemptStatus) },
    { label: "恢复阶段", value: formatMonitoringValue(monitoring.resumeFromStage) },
    { label: "恢复镜头", value: formatMonitoringValue(monitoring.resumeFromClipIndex) },
    { label: "计划镜头数", value: formatMonitoringValue(monitoring.plannedClipCount) },
    { label: "已生成镜头数", value: formatMonitoringValue(monitoring.renderedClipCount) },
    { label: "连续完成镜头", value: formatMonitoringValue(monitoring.contiguousRenderedClipCount) },
    { label: "最新片段", value: formatMonitoringValue(monitoring.latestRenderedClipIndex) },
    { label: "最新拼接", value: formatMonitoringValue(monitoring.latestJoinName) },
  ].filter((item) => item.value !== "暂无");
});

const artifactRows = computed(() => {
  const value = artifactDirectories.value;
  if (!value) return [];
  return [
    { label: "Storage 根目录", value: formatMonitoringValue(value.storageRoot) },
    { label: "任务基目录", value: formatMonitoringValue(value.baseAbsoluteDir || value.baseRelativeDir) },
    { label: "运行目录", value: formatMonitoringValue(value.runningAbsoluteDir || value.runningRelativeDir) },
    { label: "拼接目录", value: formatMonitoringValue(value.joinedAbsoluteDir || value.joinedRelativeDir) },
    { label: "脚本文件", value: formatMonitoringValue(value.storyboardFileName) },
    { label: "首帧命名", value: formatMonitoringValue(value.firstFramePattern) },
    { label: "尾帧命名", value: formatMonitoringValue(value.lastFramePattern) },
    { label: "片段命名", value: formatMonitoringValue(value.clipPattern) },
    { label: "拼接命名", value: formatMonitoringValue(value.joinPattern) },
  ].filter((item) => item.value !== "暂无");
});

const orderedTraceEvents = computed(() => [...traceEvents.value].reverse());
const traceFocus = computed(() => orderedTraceEvents.value[0] ?? null);
const tracePreview = computed(() => orderedTraceEvents.value.slice(0, 5));
const diagnosisSeverityLabel = computed(() => diagnosisSeverityText(diagnosis.value?.severity || "info"));
const diagnosisSeverityTag = computed(() => severityTag(diagnosis.value?.severity || "info"));
const diagnosisRecoveryAction = computed(() => formatDiagnosisValue(diagnosis.value?.recovery?.recommendedAction));
const diagnosisRecoveryStart = computed(() => {
  if (!diagnosis.value) return "暂无";
  return `${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromStage)} / 镜头 ${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromClipIndex)}`;
});
const diagnosisContinuitySummary = computed(() => {
  if (!diagnosis.value) return "暂无";
  return `计划 ${formatDiagnosisValue(diagnosis.value.continuity?.plannedClipCount)}，连续完成 ${formatDiagnosisValue(diagnosis.value.continuity?.contiguousRenderedClipCount)}，缺失 ${formatDiagnosisValue((diagnosis.value.continuity?.missingClipIndices as unknown[] | undefined)?.join(", "))}`;
});
const diagnosisQueueSummary = computed(() => {
  if (!diagnosis.value) return "暂无";
  return `排队 ${formatDiagnosisValue(diagnosis.value.queue?.isQueued)}，位置 ${formatDiagnosisValue(diagnosis.value.queue?.queuePosition)}，Attempt ${formatDiagnosisValue(diagnosis.value.queue?.activeAttemptStatus)}`;
});

function logLevelTag(level: string) {
  if (level === "ERROR") return "danger";
  if (level === "WARN") return "warning";
  return "info";
}

function severityTag(severity: string) {
  switch (severity) {
    case "high": return "danger";
    case "medium": return "warning";
    case "low": return "info";
    default: return "success";
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatMonitoringValue(value: unknown) {
  if (value == null) return "暂无";
  if (typeof value === "number") return value > 0 ? String(value) : "暂无";
  const text = String(value).trim();
  return text || "暂无";
}

function formatDiagnosisValue(value: unknown) {
  if (typeof value === "boolean") return value ? "是" : "否";
  return formatMonitoringValue(value);
}

function diagnosisSeverityText(severity: string) {
  switch (severity) {
    case "high": return "高风险";
    case "medium": return "中风险";
    case "low": return "低风险";
    default: return "正常";
  }
}

function findingSeverityTag(severity: string) {
  switch (severity) {
    case "high": return "danger";
    case "medium": return "warning";
    case "low": return "info";
    default: return "success";
  }
}

function formatSecondsValue(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "暂无";
  return `${Number.isInteger(value) ? value : value.toFixed(1)}s`;
}

function formatSecondsRange(minValue: number | null | undefined, maxValue: number | null | undefined, targetValue?: number | null) {
  const min = typeof minValue === "number" && Number.isFinite(minValue) && minValue > 0 ? minValue : null;
  const max = typeof maxValue === "number" && Number.isFinite(maxValue) && maxValue > 0 ? maxValue : null;
  const target = typeof targetValue === "number" && Number.isFinite(targetValue) && targetValue > 0 ? targetValue : null;
  if (min == null && max == null) return "暂无";
  if (min != null && max != null && min === max) return formatSecondsValue(target ?? min);
  const range = `${formatSecondsValue(min)} - ${formatSecondsValue(max)}`;
  return target != null ? `${range} (目标 ${formatSecondsValue(target)})` : range;
}

function durationSourceLabel(item: TaskDurationDiagnosticClip) {
  switch (item.durationSource) {
    case "storyboard": return "分镜";
    case "task_average": return "任务均分";
    default: return "未知";
  }
}

function durationStatusLabel(status: TaskDurationDiagnosticClip["status"]) {
  switch (status) {
    case "rendered": return "已生成";
    case "pending": return "待生成";
    default: return "未知";
  }
}

function formatTaskModelValue(value: unknown) {
  if (!value || typeof value !== "string") return "未指定";
  return value;
}

function formatTaskDurationMode(snapshot: Record<string, unknown>) {
  const mode = snapshot.durationMode as string | undefined;
  return mode || "auto";
}

function formatTaskOutputCount(snapshot: Record<string, unknown>) {
  const count = snapshot.outputCount;
  if (count === "auto") return "自动";
  if (typeof count === "number" && count > 0) return String(count);
  return "默认";
}

function formatTaskRequestedDuration(snapshot: Record<string, unknown>) {
  const mode = snapshot.videoDurationSeconds;
  if (mode === "auto") return "自动";
  if (typeof mode === "number" && mode > 0) return `${mode}s`;
  return "未指定";
}

function formatTaskResolvedDuration(task: Record<string, unknown>) {
  const min = task.minDurationSeconds as number | undefined;
  const max = task.maxDurationSeconds as number | undefined;
  if (min && max) return `${min}-${max}s`;
  if (min) return `${min}s`;
  if (max) return `${max}s`;
  return "未指定";
}

function formatTaskSeed(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return String(Math.trunc(value));
  return "未设置";
}

function formatTaskStopBeforeVideoGeneration(snapshot: Record<string, unknown>) {
  return snapshot.stopBeforeVideoGeneration ? "已启用" : "否";
}

function formatTaskTranscriptSummary(snapshot: Record<string, unknown>) {
  return snapshot.transcriptText ? "已提供" : "无文本输入";
}

function previewTaskTranscript(snapshot: Record<string, unknown>) {
  const text = snapshot.transcriptText as string | undefined;
  if (!text) return null;
  return text.length > 200 ? text.slice(0, 200) + "..." : text;
}

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
  if (!window.confirm(`确认删除任务"${task.value?.title || taskId.value}"吗？`)) return;
  actionLoading.value = true;
  try {
    await deleteAdminTask(taskId.value);
    await router.push("/tasks");
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

<style scoped>
.admin-task-detail-card {
  min-width: 0;
}

.admin-task-detail-card :deep(.el-card__header) {
  padding: 16px 18px;
}

.admin-task-detail-card :deep(.el-card__body) {
  padding: 18px;
}
</style>
