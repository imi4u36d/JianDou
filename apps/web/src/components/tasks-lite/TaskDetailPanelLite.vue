<template>
  <section class="surface-panel panel-shell p-5 md:p-6">
    <div v-if="task" class="space-y-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">任务详情</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-[-0.03em] text-slate-900">{{ task.title }}</h2>
          <p class="mt-2 text-sm text-slate-500">{{ task.id }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class="surface-chip">{{ formatTaskStatus(task.status) }}</span>
          <span v-if="task.platform" class="surface-chip">{{ task.platform }}</span>
          <span v-if="task.aspectRatio" class="surface-chip">{{ task.aspectRatio }}</span>
        </div>
      </header>

      <div class="surface-tile p-4">
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-medium text-slate-700">实时进度</p>
          <p class="text-sm font-semibold text-slate-900">{{ normalizedProgress }}%</p>
        </div>
        <div class="progress-track mt-2">
          <div class="progress-fill" :style="{ width: `${normalizedProgress}%` }"></div>
        </div>
        <div class="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
          <p>创建于 {{ formatTime(task.createdAt) }}</p>
          <p>更新于 {{ formatTime(task.updatedAt) }}</p>
          <p>输出 {{ task.completedOutputCount ?? task.outputs.length }} / {{ task.outputCount }}</p>
        </div>
      </div>

      <div v-if="task.errorMessage" class="surface-tile border border-rose-200 bg-rose-50/90 p-4">
        <p class="text-sm font-medium text-rose-700">失败原因</p>
        <p class="mt-2 text-sm leading-6 text-rose-700">{{ task.errorMessage }}</p>
      </div>

      <article class="surface-tile p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <p class="text-sm font-medium text-slate-700">任务结果查询</p>
          <span class="surface-chip text-xs">SeedDance</span>
        </div>
        <p class="mt-2 text-xs text-slate-500">
          输入远端任务 ID 后查询火山任务状态与视频地址。若详情日志包含 taskId，会自动填入。
        </p>
        <div class="mt-3 flex flex-wrap items-center gap-2">
          <input
            v-model.trim="remoteTaskIdInput"
            class="field-input min-w-[16rem] flex-1"
            placeholder="例如：cgt-20260408-xxxx"
            type="text"
          />
          <button
            class="btn-secondary"
            :disabled="queryLoading || !canQueryRemoteTask"
            type="button"
            @click="handleQueryRemoteTask"
          >
            {{ queryLoading ? "查询中..." : "查询任务结果" }}
          </button>
        </div>
        <p v-if="queryError" class="mt-3 text-sm text-rose-600">{{ queryError }}</p>
        <div v-else-if="remoteTaskResult" class="mt-3 rounded-xl border border-slate-200/80 bg-white/70 p-3">
          <div class="flex flex-wrap items-center gap-2 text-sm">
            <span class="text-slate-500">任务ID</span>
            <code class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{{ remoteTaskResult.taskId }}</code>
            <span class="surface-chip text-[11px]">状态 {{ remoteTaskResult.status }}</span>
          </div>
          <p v-if="remoteTaskResult.message" class="mt-2 text-xs text-slate-600">{{ remoteTaskResult.message }}</p>
          <a
            v-if="remoteTaskResult.videoUrl"
            class="btn-primary mt-3 inline-flex items-center justify-center"
            :href="resolveOutputUrl(remoteTaskResult.videoUrl)"
            rel="noopener noreferrer"
            target="_blank"
          >
            打开远端视频结果
          </a>
        </div>
      </article>

      <article v-if="displayMaterials.length" class="surface-tile p-4">
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium text-slate-700">任务素材</p>
          <span class="surface-chip text-xs">{{ displayMaterials.length }} 项</span>
        </div>
        <div class="material-grid mt-4">
          <article v-for="material in displayMaterials" :key="material.id" class="material-card">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-slate-900">{{ material.title }}</p>
              <span class="surface-chip text-[11px]">{{ material.kind === "source" ? "源素材" : "生成素材" }}</span>
            </div>
            <p class="mt-1 text-xs text-slate-500">
              {{ material.durationSeconds ? formatDuration(material.durationSeconds) : "时长待补充" }}
            </p>
            <div v-if="material.mediaType === 'video' && resolveOutputUrl(material.previewUrl || material.fileUrl)" class="mt-3 overflow-hidden rounded-xl bg-slate-900/90">
              <video
                class="h-40 w-full object-cover"
                controls
                playsinline
                preload="metadata"
                :src="resolveOutputUrl(material.previewUrl || material.fileUrl)"
              ></video>
            </div>
            <a
              class="btn-secondary mt-3 inline-flex w-full items-center justify-center"
              :href="resolveOutputUrl(material.fileUrl)"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看素材
            </a>
          </article>
        </div>
      </article>

      <article v-if="task.storyboardScript" class="surface-tile p-4">
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium text-slate-700">分镜脚本</p>
          <span class="surface-chip text-xs">任务详情可追溯</span>
        </div>
        <div class="markdown-body mt-4" v-html="renderedStoryboard"></div>
      </article>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.9fr)]">
        <article class="surface-tile p-4">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-slate-700">生成结果</p>
            <span class="surface-chip text-xs">{{ task.outputs.length }} 条</span>
          </div>
          <div v-if="task.outputs.length === 0" class="mt-4 rounded-xl border border-dashed border-slate-300/70 p-6 text-sm text-slate-500">
            {{ task.errorMessage || "当前还没有可用结果。" }}
          </div>
          <div v-else class="result-grid mt-4">
            <article v-for="output in task.outputs" :key="output.id" class="result-card">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-semibold text-slate-900">片段 #{{ output.clipIndex }}</p>
                <span class="surface-chip text-[11px]">{{ formatDuration(output.durationSeconds) }}</span>
              </div>
              <p class="mt-2 line-clamp-2 text-sm text-slate-700">{{ output.title }}</p>
              <p class="mt-1 line-clamp-2 text-xs text-slate-500">{{ output.reason }}</p>
              <div class="mt-3 overflow-hidden rounded-xl bg-slate-900/90">
                <video
                  v-if="resolveOutputUrl(output.previewUrl)"
                  class="h-40 w-full object-cover"
                  controls
                  playsinline
                  preload="metadata"
                  :src="resolveOutputUrl(output.previewUrl)"
                ></video>
              </div>
              <a
                class="btn-primary mt-3 inline-flex w-full items-center justify-center"
                :href="resolveOutputUrl(output.downloadUrl)"
                target="_blank"
                rel="noopener noreferrer"
              >
                查看生成结果
              </a>
            </article>
          </div>
        </article>

        <article class="surface-tile p-4">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-slate-700">任务实时日志</p>
            <span class="surface-chip text-xs">{{ trace.length }} 条</span>
          </div>
          <div v-if="traceLoading" class="mt-4 text-sm text-slate-500">正在加载日志...</div>
          <ol v-else-if="trace.length" class="trace-list mt-4">
            <li v-for="(item, index) in trace" :key="`${item.timestamp}-${index}`" class="trace-item">
              <div class="flex items-center justify-between gap-2 text-xs text-slate-500">
                <span>{{ formatTime(item.timestamp) }}</span>
                <span>{{ item.stage }}</span>
              </div>
              <p class="mt-1 text-sm font-medium text-slate-800">{{ item.event }}</p>
              <p class="mt-1 text-xs text-slate-600">{{ item.message }}</p>
            </li>
          </ol>
          <div v-else class="mt-4 rounded-xl border border-dashed border-slate-300/70 p-5 text-sm text-slate-500">
            暂无日志。
          </div>
        </article>
      </div>
    </div>

    <div v-else-if="loading" class="surface-tile p-6 text-sm text-slate-600">正在加载任务详情...</div>
    <div v-else class="surface-tile p-6 text-sm text-slate-600">点击右侧任务卡片后，会在这里展开任务详情。</div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fetchSeeddanceTaskResult } from "@/api/tasks";
import type { SeeddanceTaskQueryResult, TaskDetail, TaskMaterial, TaskTraceEvent } from "@/types";
import { formatTaskStatus } from "@/utils/task";
import { resolveRuntimeUrl } from "@/utils/url";
import { renderMarkdownToHtml } from "@/utils/markdown";

type TaskDetailWithRemote = TaskDetail & {
  sourceKind?: "task" | "agent-run";
  remoteTaskId?: string | null;
};

const props = defineProps<{
  task: TaskDetailWithRemote | null;
  trace: TaskTraceEvent[];
  storageBaseUrl: string;
  loading: boolean;
  traceLoading: boolean;
}>();

const remoteTaskIdInput = ref("");
const remoteTaskResult = ref<SeeddanceTaskQueryResult | null>(null);
const queryLoading = ref(false);
const queryError = ref("");

const canQueryRemoteTask = computed(() => Boolean(props.task && remoteTaskIdInput.value.trim()));

const normalizedProgress = computed(() => {
  if (!props.task) {
    return 0;
  }
  return Math.max(0, Math.min(100, props.task.progress ?? 0));
});

const displayMaterials = computed<TaskMaterial[]>(() => {
  if (!props.task?.materials?.length) {
    return [];
  }
  const sourceMaterials = props.task.materials.filter((item) => item.kind === "source");
  return sourceMaterials.length ? sourceMaterials : props.task.materials;
});

const renderedStoryboard = computed(() => renderMarkdownToHtml(props.task?.storyboardScript || ""));

watch(
  () => props.task?.id ?? "",
  () => {
    remoteTaskIdInput.value = "";
    remoteTaskResult.value = null;
    queryError.value = "";
    const detected = detectRemoteTaskId();
    if (detected) {
      remoteTaskIdInput.value = detected;
    }
  },
  { immediate: true }
);

watch(
  () => props.trace,
  () => {
    if (remoteTaskIdInput.value.trim()) {
      return;
    }
    const detected = detectRemoteTaskId();
    if (detected) {
      remoteTaskIdInput.value = detected;
    }
  },
  { deep: true }
);

function resolveOutputUrl(url: string) {
  return resolveRuntimeUrl(url, props.storageBaseUrl);
}

function asRecord(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function extractTaskIdFromText(value: unknown) {
  const text = asString(value);
  if (!text) {
    return "";
  }
  const markerMatch = text.match(/\[seeddance_task_id=([^\]]+)\]/i);
  if (markerMatch?.[1]) {
    return markerMatch[1].trim();
  }
  const genericMatch = text.match(/\btask[_\s-]*id[:=\s]+([A-Za-z0-9._:-]+)/i);
  if (genericMatch?.[1]) {
    return genericMatch[1].trim();
  }
  return "";
}

function detectRemoteTaskId() {
  if (!props.task) {
    return "";
  }
  const direct = asString(props.task.remoteTaskId);
  if (direct) {
    return direct;
  }
  const fromError = extractTaskIdFromText(props.task.errorMessage);
  if (fromError) {
    return fromError;
  }
  const reversedTrace = [...props.trace].reverse();
  for (const item of reversedTrace) {
    const payload = asRecord(item.payload) ?? {};
    const payloadTaskId = asString(payload.taskId) || asString(payload.task_id);
    if (payloadTaskId) {
      return payloadTaskId;
    }
    const details = asRecord(payload.details) ?? {};
    const detailsTaskId = asString(details.taskId) || asString(details.task_id);
    if (detailsTaskId) {
      return detailsTaskId;
    }
    const fromMessage = extractTaskIdFromText(item.message);
    if (fromMessage) {
      return fromMessage;
    }
  }
  return "";
}

async function handleQueryRemoteTask() {
  const taskId = remoteTaskIdInput.value.trim();
  if (!taskId) {
    queryError.value = "请先输入任务 ID。";
    remoteTaskResult.value = null;
    return;
  }
  queryLoading.value = true;
  queryError.value = "";
  try {
    remoteTaskResult.value = await fetchSeeddanceTaskResult(taskId);
  } catch (error) {
    remoteTaskResult.value = null;
    queryError.value = error instanceof Error ? error.message : "查询任务结果失败";
  } finally {
    queryLoading.value = false;
  }
}

function formatDuration(seconds: number) {
  return `${Math.max(0, Math.round(seconds))}s`;
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}
</script>

<style scoped>
.panel-shell {
  min-height: min(100%, calc(100vh - 9rem));
}

.progress-track {
  height: 0.52rem;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.24);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #4f7cff, #2dd4bf);
}

.material-grid,
.result-grid {
  display: grid;
  gap: 0.8rem;
}

@media (min-width: 900px) {
  .material-grid,
  .result-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.material-card,
.result-card {
  border-radius: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.68));
  padding: 0.8rem;
}

.trace-list {
  max-height: 32rem;
  overflow: auto;
  display: grid;
  gap: 0.65rem;
  padding-right: 0.2rem;
}

.trace-item {
  border-radius: 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.74);
  padding: 0.65rem 0.7rem;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  color: rgb(15 23 42);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.markdown-body :deep(h1) {
  font-size: 1.4rem;
}

.markdown-body :deep(h2) {
  font-size: 1.1rem;
  margin-top: 1.15rem;
}

.markdown-body :deep(h3) {
  font-size: 1rem;
  margin-top: 1rem;
}

.markdown-body :deep(p),
.markdown-body :deep(li),
.markdown-body :deep(td),
.markdown-body :deep(th),
.markdown-body :deep(blockquote) {
  color: rgb(71 85 105);
  line-height: 1.75;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.25rem;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.75rem;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid rgba(148, 163, 184, 0.24);
  padding: 0.55rem 0.65rem;
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: rgba(241, 245, 249, 0.85);
}

.markdown-body :deep(code) {
  background: rgba(226, 232, 240, 0.7);
  border-radius: 0.35rem;
  padding: 0.1rem 0.3rem;
}

.markdown-body :deep(pre) {
  overflow: auto;
  border-radius: 1rem;
  background: rgb(15 23 42);
  color: white;
  padding: 0.9rem 1rem;
}
</style>
