<template>
  <section class="grid gap-6 xl:grid-cols-[0.98fr_1.02fr]">
    <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.88),rgba(8,11,24,0.78))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
      <PageHeader
        eyebrow="Progress"
        :title="task?.title || '任务详情'"
        description="查看任务状态、阶段进度、规划方案和渲染输出，快速判断当前素材的生产质量。"
      >
        <div class="flex flex-wrap gap-2">
          <button class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-100 transition duration-200 hover:border-rose-300/40 hover:bg-white/10" type="button" @click="openCloneFlow">
            复制参数
          </button>
          <button
            v-if="task?.status === 'FAILED'"
            class="rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-white transition duration-200 hover:bg-rose-400"
            type="button"
            @click="handleRetry"
          >
            失败重试
          </button>
        </div>
      </PageHeader>

      <div v-if="errorMessage" class="mb-4 rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p>{{ errorMessage }}</p>
          <button class="rounded-full border border-rose-300/30 px-4 py-2 text-xs font-medium text-rose-50 transition hover:bg-rose-500/20" type="button" @click="loadTask">
            重新加载
          </button>
        </div>
      </div>

      <div v-if="loading" class="rounded-[24px] border border-white/10 bg-white/[0.04] p-6 text-sm text-slate-300">
        正在加载任务详情...
      </div>

      <template v-else-if="task">
        <div class="grid gap-4 rounded-[28px] border border-white/10 bg-white/[0.04] p-5">
          <div class="flex flex-wrap items-center gap-3">
            <StatusBadge :status="task.status" />
            <span class="text-sm text-slate-300">{{ task.progress }}%</span>
            <span class="text-sm text-slate-400">{{ statusHint }}</span>
          </div>

          <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">输出数量</p>
              <p class="mt-2 text-lg font-semibold text-white">{{ completedOutputCount }} / {{ task.outputCount }}</p>
            </div>
            <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">重试次数</p>
              <p class="mt-2 text-lg font-semibold text-white">{{ task.retryCount ?? 0 }}</p>
            </div>
            <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">开始时间</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ formatTime(task.startedAt) }}</p>
            </div>
            <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">结束时间</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ formatTime(task.finishedAt) }}</p>
            </div>
          </div>

          <div class="grid gap-3">
            <TimelineStage label="素材分析" description="读取源文件、探测时长和基础轨道信息。" :state="getStageState('analysis')" />
            <TimelineStage label="剪辑规划" description="生成切条方案，选择更适合投放的片段。" :state="getStageState('planning')" />
            <TimelineStage label="视频渲染" description="输出预览版和下载版素材。" :state="getStageState('rendering')" />
          </div>
        </div>

        <div class="mt-6 grid gap-4 rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
          <div class="grid gap-1">
            <span class="text-xs uppercase tracking-[0.24em] text-slate-400">任务配置</span>
            <span class="text-sm text-slate-200">{{ task.platform }} · {{ task.aspectRatio }} · {{ task.minDurationSeconds }}-{{ task.maxDurationSeconds }} 秒 · {{ task.outputCount }} 条</span>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">源文件</p>
              <p class="mt-2 text-sm text-white">{{ task.sourceFileName }}</p>
              <p v-if="task.source?.originalFileName" class="mt-1 text-xs text-slate-400">原始资产：{{ task.source.originalFileName }}</p>
            </div>
            <div v-if="task.creativePrompt">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">创意补充</p>
              <p class="mt-2 text-sm leading-6 text-slate-300">{{ task.creativePrompt }}</p>
            </div>
          </div>

          <div v-if="task.hasTranscript" class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">语义规划输入</p>
            <p class="mt-2 text-sm font-medium text-white">{{ task.hasTimedTranscript ? "已提供带时间戳字幕/台词" : "已提供纯文本台词/字幕" }}</p>
            <p class="mt-1 text-xs text-slate-400">时间轴片段：{{ task.transcriptCueCount ?? 0 }} 条</p>
            <p v-if="task.transcriptPreview" class="mt-2 text-sm leading-6 text-slate-300">{{ task.transcriptPreview }}</p>
          </div>

          <div v-if="task.plan?.length" class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">规划方案</p>
            <div v-if="task.plan?.length" class="mt-4 grid gap-3">
              <article v-for="clip in task.plan" :key="clip.clipIndex" class="rounded-2xl border border-white/8 bg-slate-950/50 p-4">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-semibold text-white">#{{ clip.clipIndex }} {{ clip.title }}</p>
                    <p class="mt-2 text-sm leading-6 text-slate-300">{{ clip.reason }}</p>
                  </div>
                  <span class="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200">{{ clip.durationSeconds.toFixed(1) }}s</span>
                </div>
                <div class="mt-4 grid grid-cols-3 gap-3 text-xs text-slate-400">
                  <div>起点 {{ clip.startSeconds.toFixed(1) }}s</div>
                  <div>终点 {{ clip.endSeconds.toFixed(1) }}s</div>
                  <div>时长 {{ clip.durationSeconds.toFixed(1) }}s</div>
                </div>
              </article>
            </div>
          </div>

          <div v-if="task.source" class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">素材信息</p>
              <p class="mt-2 text-sm text-white">{{ formatDuration(task.source.durationSeconds) }}</p>
              <p class="mt-1 text-xs text-slate-400">{{ formatResolution(task.source.width, task.source.height) }}</p>
            </div>
            <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">音轨 / 体积</p>
              <p class="mt-2 text-sm text-white">{{ task.source.hasAudio === false ? "无音轨" : "含音轨" }}</p>
              <p class="mt-1 text-xs text-slate-400">{{ formatBytes(task.source.sizeBytes) }}</p>
            </div>
          </div>

          <div v-if="task.errorMessage" class="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-200">
            {{ task.errorMessage }}
          </div>
        </div>

        <div class="mt-6 rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Trace</p>
              <h3 class="mt-2 text-lg font-semibold text-white">全链路日志追踪</h3>
              <p class="mt-1 text-sm text-slate-400">包含 API 创建、调度、分析、规划、LLM 调用、渲染与失败信息。</p>
            </div>
            <button class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-100 transition duration-200 hover:border-rose-300/40 hover:bg-white/10" type="button" @click="loadTrace">
              刷新日志
            </button>
          </div>

          <div v-if="traceLoading" class="mt-4 text-sm text-slate-400">正在加载任务日志...</div>
          <div v-else-if="traceErrorMessage" class="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
            {{ traceErrorMessage }}
          </div>
          <div v-else-if="traceEvents.length === 0" class="mt-4 rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
            当前任务还没有可展示的 trace 事件。
          </div>
          <div v-else class="mt-4 grid gap-3">
            <article
              v-for="entry in traceEvents"
              :key="`${entry.timestamp}-${entry.event}`"
              class="rounded-2xl border border-white/8 bg-white/[0.04] p-4"
            >
              <div class="flex flex-wrap items-center gap-2">
                <span :class="traceStageClass(entry.stage)" class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
                  {{ entry.stage }}
                </span>
                <span :class="traceLevelClass(entry.level)" class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
                  {{ entry.level }}
                </span>
                <span class="text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</span>
              </div>
              <p class="mt-3 text-sm font-medium text-white">{{ entry.message }}</p>
              <p class="mt-1 font-mono text-xs text-slate-500">{{ entry.event }}</p>
              <pre v-if="Object.keys(entry.payload || {}).length" class="mt-3 overflow-x-auto rounded-xl border border-white/8 bg-slate-950/70 p-3 text-xs leading-6 text-slate-300">{{ formatTracePayload(entry.payload) }}</pre>
            </article>
          </div>
        </div>
      </template>
    </div>

    <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.86),rgba(8,11,24,0.72))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <PageHeader
        eyebrow="Outputs"
        title="生成结果"
        description="预览和下载生成素材，并按片段查看每条内容的规划理由。"
      />

      <div v-if="loading && !task" class="rounded-[24px] border border-dashed border-white/15 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
        任务完成后会在这里展示剪辑结果。
      </div>

      <div v-else-if="!task || task.outputs.length === 0" class="rounded-[24px] border border-dashed border-white/15 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
        任务完成后会在这里展示剪辑结果。
      </div>

      <div v-else class="grid gap-4">
        <div class="grid grid-cols-2 gap-3 rounded-[24px] border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
          <div>
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">完成输出</p>
            <p class="mt-2 text-lg font-semibold text-white">{{ completedOutputCount }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">渲染目标</p>
            <p class="mt-2 text-lg font-semibold text-white">{{ task.outputCount }}</p>
          </div>
        </div>

        <article v-for="output in task.outputs" :key="output.id" class="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
          <div class="flex flex-col gap-4 xl:flex-row">
            <video :src="resolveStorageUrl(output.previewUrl)" controls class="aspect-[9/16] w-full max-w-[240px] rounded-2xl border border-white/10 bg-black object-cover"></video>
            <div class="flex-1">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h3 class="text-lg font-semibold text-white">{{ output.title }}</h3>
                  <p class="mt-2 text-sm leading-6 text-slate-300">{{ output.reason }}</p>
                </div>
                <a :href="resolveStorageUrl(output.downloadUrl)" class="rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-white transition duration-200 hover:bg-rose-400" download>
                  下载
                </a>
              </div>
              <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300 sm:grid-cols-4">
                <div>序号：{{ output.clipIndex }}</div>
                <div>起点：{{ output.startSeconds.toFixed(1) }}s</div>
                <div>终点：{{ output.endSeconds.toFixed(1) }}s</div>
                <div>时长：{{ output.durationSeconds.toFixed(1) }}s</div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getRuntimeConfig } from "@/api/runtime-config";
import { fetchTask, fetchTaskTrace, retryTask } from "@/api/tasks";
import type { TaskDetail, TaskStatus, TaskTraceEvent } from "@/types";
import PageHeader from "@/components/PageHeader.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import TimelineStage from "@/components/TimelineStage.vue";
import { usePolling } from "@/composables/usePolling";
import { formatTaskStatus, getTaskLifecycleGroup, isTerminalTaskStatus } from "@/utils/task";
import { resolveRuntimeUrl } from "@/utils/url";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const loading = ref(true);
const errorMessage = ref("");
const traceEvents = ref<TaskTraceEvent[]>([]);
const traceLoading = ref(false);
const traceErrorMessage = ref("");

const taskId = computed(() => {
  const value = route.params.id;
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return typeof value === "string" ? value : "";
});

const statusHint = computed(() => {
  if (!task.value) {
    return "";
  }
  return formatTaskStatus(task.value.status);
});

const completedOutputCount = computed(() => task.value?.completedOutputCount ?? task.value?.outputs.length ?? 0);

function resolveStorageUrl(value: string) {
  return resolveRuntimeUrl(value, getRuntimeConfig().storageBaseUrl);
}

function formatTime(value?: string | null) {
  if (!value) {
    return "等待生成";
  }
  return new Date(value).toLocaleString();
}

function formatDuration(value?: number | null) {
  if (typeof value !== "number") {
    return "时长未知";
  }
  return `${value.toFixed(1)} 秒`;
}

function formatResolution(width?: number | null, height?: number | null) {
  if (!width || !height) {
    return "分辨率待探测";
  }
  return `${width} × ${height}`;
}

function formatBytes(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "体积未知";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function getStageState(stage: "analysis" | "planning" | "rendering") {
  if (!task.value) {
    return "pending" as const;
  }

  const progress = task.value.progress ?? 0;
  if (task.value.status === "COMPLETED") {
    return "done" as const;
  }

  if (task.value.status === "FAILED") {
    if (stage === "analysis") {
      return progress >= 10 ? "done" as const : "current" as const;
    }
    if (stage === "planning") {
      return progress >= 25 ? "done" as const : progress >= 10 ? "current" as const : "pending" as const;
    }
    return progress >= 40 ? "current" as const : progress >= 25 ? "current" as const : "pending" as const;
  }

  if (task.value.status === "PENDING") {
    return stage === "analysis" ? "current" as const : "pending" as const;
  }

  if (task.value.status === "ANALYZING") {
    if (stage === "analysis") {
      return "current" as const;
    }
    return "pending" as const;
  }

  if (task.value.status === "PLANNING") {
    if (stage === "analysis") {
      return "done" as const;
    }
    if (stage === "planning") {
      return "current" as const;
    }
    return "pending" as const;
  }

  if (task.value.status === "RENDERING") {
    if (stage === "rendering") {
      return "current" as const;
    }
    return "done" as const;
  }

  return getTaskLifecycleGroup(task.value.status as TaskStatus) === "completed" ? "done" : "pending";
}

async function loadTask() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    loading.value = false;
    stop();
    return;
  }
  loading.value = task.value === null;
  try {
    task.value = await fetchTask(taskId.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载任务详情失败";
  } finally {
    loading.value = false;
  }
}

async function loadTrace() {
  traceErrorMessage.value = "";
  if (!taskId.value) {
    traceEvents.value = [];
    return;
  }
  traceLoading.value = true;
  try {
    traceEvents.value = await fetchTaskTrace(taskId.value, 800);
  } catch (error) {
    traceErrorMessage.value = error instanceof Error ? error.message : "加载任务日志失败";
  } finally {
    traceLoading.value = false;
  }
}

async function handleRetry() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    return;
  }
  loading.value = true;
  try {
    task.value = await retryTask(taskId.value);
    await loadTrace();
    if (isTerminalTaskStatus(task.value.status)) {
      stop();
    } else {
      await start(false);
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    loading.value = false;
  }
}

function openCloneFlow() {
  if (!taskId.value) {
    return;
  }
  router.push({ path: "/tasks/new", query: { cloneFrom: taskId.value } });
}

function traceStageClass(stage: string) {
  switch (stage) {
    case "llm":
      return "bg-fuchsia-500/15 text-fuchsia-100";
    case "render":
      return "bg-amber-500/15 text-amber-100";
    case "analysis":
      return "bg-cyan-500/15 text-cyan-100";
    case "planning":
      return "bg-sky-500/15 text-sky-100";
    case "api":
      return "bg-emerald-500/15 text-emerald-100";
    default:
      return "bg-white/10 text-slate-200";
  }
}

function traceLevelClass(level: string) {
  switch (level.toUpperCase()) {
    case "ERROR":
      return "bg-rose-500/15 text-rose-100";
    case "WARN":
      return "bg-amber-500/15 text-amber-100";
    default:
      return "bg-white/10 text-slate-200";
  }
}

function formatTracePayload(payload: Record<string, unknown>) {
  return JSON.stringify(payload, null, 2);
}

const { start, stop } = usePolling(async () => {
  await loadTask();
  await loadTrace();
  if (task.value && isTerminalTaskStatus(task.value.status)) {
    stop();
  }
}, 3000);

watch(
  taskId,
  async (_, __, onCleanup) => {
    onCleanup(stop);
    task.value = null;
    errorMessage.value = "";
    traceEvents.value = [];
    traceErrorMessage.value = "";
    loading.value = true;
    await start();
  },
  { immediate: true }
);
</script>
