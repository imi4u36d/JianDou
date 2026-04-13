<template>
  <section class="admin-page admin-task-detail-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Task Detail</p>
          <h2 class="admin-title">任务详情</h2>
          <p class="admin-subtitle">面向运维的任务生成诊断视图：状态、参数、进度、日志。</p>
        </div>
        <div class="admin-action-row">
          <button v-if="task?.status === 'FAILED'" :class="warningButtonClass" :disabled="actionLoading" type="button" @click="retryTaskAction">失败重试</button>
          <button :class="dangerButtonClass" :disabled="actionLoading || runningTask" type="button" @click="deleteTaskAction">删除</button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="admin-alert-error">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="admin-panel px-4 py-8 text-sm text-slate-500">
      正在读取任务详情...
    </div>

    <template v-else-if="task">
      <div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <h3 class="text-base font-semibold text-slate-900">基础信息</h3>
          </div>
          <div class="grid gap-3 p-5 sm:grid-cols-2">
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">任务标题</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.title }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">状态</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.status }} · {{ task.progress }}%</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">比例</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.aspectRatio }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">已生成结果</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.completedOutputCount ?? task.outputs?.length ?? 0 }} 条</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">时长区间</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">源文件</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ task.sourceFileName }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">当前阶段</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ monitoringStageLabel }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">当前 Worker</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ monitoringWorkerLabel }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">任务 Seed</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ taskSeedLabel }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">效果评分</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ effectRatingLabel }}</p>
            </article>
          </div>

          <div class="border-t border-slate-200/80 px-5 py-4">
            <h4 class="text-sm font-semibold text-slate-900">任务摘要</h4>
            <p class="mt-1 text-sm text-slate-700">{{ planningSummary.title }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ planningSummary.detail }}</p>
          </div>

          <div v-if="monitoringRows.length" class="border-t border-slate-200/80 px-5 py-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h4 class="text-sm font-semibold text-slate-900">执行监控</h4>
              <span class="admin-chip">{{ monitoringStageLabel }}</span>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <article v-for="item in monitoringRows" :key="item.label" class="admin-panel-soft p-4">
                <p class="text-xs uppercase tracking-wide text-slate-500">{{ item.label }}</p>
                <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ item.value }}</p>
              </article>
            </div>
          </div>

          <div v-if="artifactRows.length" class="border-t border-slate-200/80 px-5 py-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h4 class="text-sm font-semibold text-slate-900">产物目录</h4>
              <span class="admin-chip">{{ artifactDirectoryHint }}</span>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <article v-for="item in artifactRows" :key="item.label" class="admin-panel-soft p-4">
                <p class="text-xs uppercase tracking-wide text-slate-500">{{ item.label }}</p>
                <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ item.value }}</p>
              </article>
            </div>
          </div>

	          <div class="border-t border-slate-200/80 px-5 py-4">
	            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
	              <h4 class="text-sm font-semibold text-slate-900">创建参数</h4>
	              <span class="admin-chip">时长模式 {{ requestDurationMode }}</span>
	            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <article v-for="item in requestRows" :key="item.label" class="admin-panel-soft p-4">
                <p class="text-xs uppercase tracking-wide text-slate-500">{{ item.label }}</p>
                <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ item.value }}</p>
              </article>
            </div>
            <article v-if="task.creativePrompt" class="admin-panel-soft mt-3 p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">创意提示词</p>
              <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{{ task.creativePrompt }}</p>
            </article>
	            <article v-if="requestTranscriptPreview" class="admin-panel-soft mt-3 p-4">
	              <p class="text-xs uppercase tracking-wide text-slate-500">文本输入摘要</p>
	              <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{{ requestTranscriptPreview }}</p>
	            </article>
	          </div>

          <div class="border-t border-slate-200/80 px-5 py-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h4 class="text-sm font-semibold text-slate-900">效果评分</h4>
              <span class="admin-chip">{{ effectRatingLabel }}</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="score in [5, 4, 3, 2, 1]"
                :key="score"
                class="admin-btn-secondary admin-btn-sm"
                :class="ratingDraft === score ? 'ring-2 ring-slate-300' : ''"
                type="button"
                :disabled="actionLoading || ratingSaving"
                @click="ratingDraft = score"
              >
                {{ score }}/5
              </button>
            </div>
            <textarea
              v-model="ratingNote"
              class="admin-field mt-3 min-h-[96px]"
              rows="4"
              placeholder="记录当前 seed 或画面效果表现，例如稳定性、人物一致性、动作完成度。"
            ></textarea>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <button
                :class="warningButtonClass"
                type="button"
                :disabled="actionLoading || ratingSaving || !ratingDraft"
                @click="saveEffectRating"
              >
                {{ ratingSaving ? "保存中..." : "保存评分" }}
              </button>
              <span class="text-xs text-slate-500">
                {{ task.ratedAt ? `最近评分时间 ${formatTime(task.ratedAt)}` : "当前还没有保存过评分" }}
              </span>
            </div>
          </div>

	          <div v-if="task.errorMessage" class="border-t border-slate-200/80 px-5 py-4">
	            <div class="admin-alert-error">
	              {{ task.errorMessage }}
	            </div>
          </div>

          <div v-if="task.plan?.length" class="border-t border-slate-200/80 p-5">
            <div class="mb-2 flex items-center justify-between">
              <h4 class="text-sm font-semibold text-slate-900">任务计划</h4>
              <span class="admin-chip">{{ task.plan.length }} 条</span>
            </div>
            <div class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>序号</th>
                    <th>标题</th>
                    <th>时长</th>
                    <th>时间窗</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="clip in task.plan" :key="clip.clipIndex">
                    <td>#{{ clip.clipIndex }}</td>
                    <td>
                      <p class="font-medium text-slate-900">{{ clip.title }}</p>
                      <p class="mt-0.5 text-xs text-slate-500">{{ clip.reason }}</p>
                    </td>
                    <td>{{ clip.durationSeconds.toFixed(1) }}s</td>
                    <td>{{ clip.startSeconds.toFixed(1) }}s - {{ clip.endSeconds.toFixed(1) }}s</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <div>
              <h3 class="text-base font-semibold text-slate-900">任务日志</h3>
              <p class="mt-1 text-sm text-slate-600">默认显示最新摘要，可展开完整事件流。</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button :class="secondaryButtonClass" type="button" @click="refresh">刷新</button>
              <button :class="ghostButtonClass" type="button" @click="traceExpanded = !traceExpanded">{{ traceExpanded ? "收起日志" : "展开日志" }}</button>
            </div>
          </div>

          <div class="space-y-4 p-5">
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">当前重点</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ traceFocus?.message || "暂无日志" }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ traceFocus?.timestamp ? formatTime(traceFocus.timestamp) : "" }}</p>
            </article>

            <div v-if="traceEvents.length === 0" class="admin-empty">
              当前没有日志。
            </div>

            <div v-else class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>级别</th>
                    <th>阶段</th>
                    <th>消息</th>
                    <th>事件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="entry in traceExpanded ? orderedTraceEvents : tracePreview"
                    :key="`${entry.timestamp}-${entry.event}`"
                  >
                    <td class="text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                    <td>
                      <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                    </td>
                    <td>{{ entry.stage }}</td>
                    <td>{{ entry.message }}</td>
                    <td class="break-all text-xs text-slate-500">{{ entry.event }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      <section v-if="diagnosis" class="admin-panel mt-4 overflow-hidden">
        <div class="admin-panel-header">
          <div>
            <h3 class="text-base font-semibold text-slate-900">任务诊断</h3>
            <p class="mt-1 text-sm text-slate-600">{{ diagnosis.summary }}</p>
          </div>
          <span class="admin-chip">{{ diagnosisSeverityLabel }}</span>
        </div>
        <div class="grid gap-4 p-5 xl:grid-cols-[1.2fr_0.8fr]">
          <div class="space-y-3">
            <article
              v-for="finding in diagnosis.findings"
              :key="finding.code"
              class="admin-panel-soft p-4"
              :class="diagnosisFindingClass(finding.severity)"
            >
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-sm font-semibold text-slate-900">{{ finding.title }}</p>
                <span class="admin-chip">{{ diagnosisSeverityText(finding.severity) }}</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-slate-700">{{ finding.detail }}</p>
            </article>
          </div>
          <div class="space-y-3">
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">推荐动作</p>
              <p class="mt-2 text-sm leading-6 text-slate-900">{{ diagnosisRecoveryAction }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">恢复起点</p>
              <p class="mt-2 text-sm leading-6 text-slate-900">{{ diagnosisRecoveryStart }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">连续性摘要</p>
              <p class="mt-2 text-sm leading-6 text-slate-900">{{ diagnosisContinuitySummary }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">队列状态</p>
              <p class="mt-2 text-sm leading-6 text-slate-900">{{ diagnosisQueueSummary }}</p>
            </article>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteAdminTask, fetchAdminTask, fetchAdminTaskDiagnosis, fetchAdminTaskTrace, rateAdminTaskEffect, retryAdminTask } from "@/api/admin";
import type { AdminTaskDiagnosis, TaskDetail, TaskTraceEvent } from "@/types";
import {
  formatTaskDurationMode,
  formatTaskEffectRating,
  formatTaskModelValue,
  formatTaskOutputCount,
  formatTaskRequestedDuration,
  formatTaskResolvedDuration,
  formatTaskSeed,
  formatTaskStopBeforeVideoGeneration,
  formatTaskTranscriptSummary,
  getTaskRequestSnapshot,
  previewTaskTranscript,
} from "@/utils/task-request";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const diagnosis = ref<AdminTaskDiagnosis | null>(null);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const traceExpanded = ref(false);
const ratingDraft = ref<number | null>(null);
const ratingNote = ref("");
const ratingSaving = ref(false);

const ghostButtonClass = "admin-btn-ghost";
const secondaryButtonClass = "admin-btn-secondary";
const warningButtonClass = "admin-btn-warning";
const dangerButtonClass = "admin-btn-danger";

const taskId = computed(() => String(route.params.id || ""));
const runningTask = computed(() => Boolean(task.value && (task.value.status === "ANALYZING" || task.value.status === "PLANNING" || task.value.status === "RENDERING")));

const planningSummary = computed(() => {
  if (!task.value?.plan?.length) {
    return {
      label: "未生成计划",
      title: "当前还没有任务计划",
      detail: "任务如果失败或仍在处理中，计划可能尚未生成。"
    };
  }
  if (task.value.hasTimedTranscript) {
    return {
      label: "时间轴输入",
      title: "当前任务包含时间轴文本输入",
      detail: "系统会优先依据时间轴文本与阶段信号推进生成。"
    };
  }
  return {
    label: "任务生成",
    title: "当前任务使用标准生成链路",
    detail: "系统按分析、编排、渲染阶段持续推进。"
  };
});

const requestSnapshot = computed(() => getTaskRequestSnapshot(task.value));

const requestDurationMode = computed(() => formatTaskDurationMode(requestSnapshot.value));

const requestTranscriptPreview = computed(() => previewTaskTranscript(requestSnapshot.value));

const requestRows = computed(() => {
  if (!task.value) {
    return [];
  }
  return [
    { label: "文本模型", value: formatTaskModelValue(requestSnapshot.value.textAnalysisModel) },
    { label: "视觉模型", value: formatTaskModelValue(requestSnapshot.value.visionModel) },
    { label: "关键帧模型", value: formatTaskModelValue(requestSnapshot.value.imageModel) },
    { label: "视频模型", value: formatTaskModelValue(requestSnapshot.value.videoModel) },
    { label: "视频尺寸", value: formatTaskModelValue(requestSnapshot.value.videoSize) },
    { label: "输出数量", value: formatTaskOutputCount(requestSnapshot.value) },
    { label: "请求时长", value: formatTaskRequestedDuration(requestSnapshot.value) },
    { label: "生效时长", value: formatTaskResolvedDuration(task.value) },
    { label: "任务 Seed", value: taskSeedLabel.value },
    { label: "提前停止视频生成", value: formatTaskStopBeforeVideoGeneration(requestSnapshot.value) },
    { label: "文本输入", value: formatTaskTranscriptSummary(requestSnapshot.value) },
    { label: "创建平台", value: formatTaskModelValue(requestSnapshot.value.platform || task.value.platform) },
  ];
});

const effectRatingLabel = computed(() => formatTaskEffectRating(task.value?.effectRating));
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

const monitoringRows = computed(() => {
  const monitoring = task.value?.monitoring;
  if (!monitoring) {
    return [];
  }
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
  if (!value) {
    return [];
  }
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
const diagnosisRecoveryAction = computed(() => formatDiagnosisValue(diagnosis.value?.recovery?.recommendedAction));
const diagnosisRecoveryStart = computed(() => {
  if (!diagnosis.value) {
    return "暂无";
  }
  return `${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromStage)} / 镜头 ${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromClipIndex)}`;
});
const diagnosisContinuitySummary = computed(() => {
  if (!diagnosis.value) {
    return "暂无";
  }
  return `计划 ${formatDiagnosisValue(diagnosis.value.continuity?.plannedClipCount)}，连续完成 ${formatDiagnosisValue(diagnosis.value.continuity?.contiguousRenderedClipCount)}，缺失 ${formatDiagnosisValue((diagnosis.value.continuity?.missingClipIndices as unknown[] | undefined)?.join(", "))}`;
});
const diagnosisQueueSummary = computed(() => {
  if (!diagnosis.value) {
    return "暂无";
  }
  return `排队 ${formatDiagnosisValue(diagnosis.value.queue?.isQueued)}，位置 ${formatDiagnosisValue(diagnosis.value.queue?.queuePosition)}，Attempt ${formatDiagnosisValue(diagnosis.value.queue?.activeAttemptStatus)}`;
});

function logLevelClass(level: string) {
  if (level === "ERROR") {
    return "bg-rose-100 text-rose-700";
  }
  if (level === "WARN") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatMonitoringValue(value: unknown) {
  if (value == null) {
    return "暂无";
  }
  if (typeof value === "number") {
    return value > 0 ? String(value) : "暂无";
  }
  const text = String(value).trim();
  return text ? text : "暂无";
}

function formatDiagnosisValue(value: unknown) {
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return formatMonitoringValue(value);
}

function diagnosisSeverityText(severity: string) {
  switch (severity) {
    case "high":
      return "高风险";
    case "medium":
      return "中风险";
    case "low":
      return "低风险";
    default:
      return "正常";
  }
}

function diagnosisFindingClass(severity: string) {
  switch (severity) {
    case "high":
      return "border border-rose-200 bg-rose-50";
    case "medium":
      return "border border-amber-200 bg-amber-50";
    case "low":
      return "border border-sky-200 bg-sky-50";
    default:
      return "";
  }
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
  errorMessage.value = "";
  try {
    await Promise.all([loadTask(), loadTrace(), loadDiagnosis()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取任务详情失败";
  } finally {
    loading.value = false;
  }
}

async function saveEffectRating() {
  if (!taskId.value || !ratingDraft.value) {
    return;
  }
  ratingSaving.value = true;
  errorMessage.value = "";
  try {
    await rateAdminTaskEffect(taskId.value, {
      effectRating: ratingDraft.value,
      effectRatingNote: ratingNote.value.trim() || undefined,
    });
    await refresh();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "保存评分失败";
  } finally {
    ratingSaving.value = false;
  }
}

async function retryTaskAction() {
  actionLoading.value = true;
  try {
    await retryAdminTask(taskId.value);
    await refresh();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function deleteTaskAction() {
  if (!window.confirm(`确认删除任务“${task.value?.title || taskId.value}”吗？`)) {
    return;
  }
  actionLoading.value = true;
  try {
    await deleteAdminTask(taskId.value);
    router.push("/admin/tasks");
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除失败";
  } finally {
    actionLoading.value = false;
  }
}

watch(taskId, () => {
  traceExpanded.value = false;
  void refresh();
}, { immediate: true });

watch(task, (value) => {
  ratingDraft.value = typeof value?.effectRating === "number" && value.effectRating > 0 ? Math.trunc(value.effectRating) : null;
  ratingNote.value = value?.effectRatingNote?.trim() || "";
}, { immediate: true });
</script>

<style scoped>
.admin-task-detail-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-task-detail-view :deep(.admin-panel-soft) {
  border: 1px solid #dbe4ee;
  background: #f8fafc;
}

.admin-task-detail-view :deep(.admin-table th) {
  background: #f1f5f9;
}
</style>
