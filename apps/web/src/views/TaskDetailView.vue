<template>
  <section class="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
    <div class="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-panel">
      <PageHeader
        eyebrow="Progress"
        :title="task?.title || '任务详情'"
        description="查看任务状态、阶段进度和参数配置。"
      />

      <div v-if="errorMessage" class="mb-4 rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p>{{ errorMessage }}</p>
          <button class="rounded-full border border-rose-300/30 px-4 py-2 text-xs font-medium text-rose-50 transition hover:bg-rose-500/20" @click="loadTask">
            重新加载
          </button>
        </div>
      </div>

      <div v-if="loading" class="text-sm text-slate-300">正在加载任务详情...</div>

      <template v-else-if="task">
        <div class="flex items-center gap-3">
          <StatusBadge :status="task.status" />
          <span class="text-sm text-slate-300">{{ task.progress }}%</span>
          <span class="text-sm text-slate-400">{{ statusHint }}</span>
        </div>

        <div class="mt-5 grid gap-3">
          <TimelineStage label="素材分析" :active="['ANALYZING', 'PLANNING', 'RENDERING', 'COMPLETED'].includes(task.status)" />
          <TimelineStage label="剪辑规划" :active="['PLANNING', 'RENDERING', 'COMPLETED'].includes(task.status)" />
          <TimelineStage label="视频渲染" :active="['RENDERING', 'COMPLETED'].includes(task.status)" />
        </div>

        <div class="mt-6 grid gap-4 rounded-[24px] border border-white/10 bg-slate-950/40 p-5 text-sm text-slate-300">
          <div class="grid gap-1">
            <span class="text-xs uppercase tracking-[0.25em] text-slate-400">源文件</span>
            <span>{{ task.sourceFileName }}</span>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>平台：{{ task.platform }}</div>
            <div>比例：{{ task.aspectRatio }}</div>
            <div>时长：{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒</div>
            <div>产出：{{ task.outputCount }} 条</div>
            <div>片头：{{ task.introTemplate }}</div>
            <div>片尾：{{ task.outroTemplate }}</div>
          </div>
          <div v-if="task.creativePrompt">
            <span class="text-xs uppercase tracking-[0.25em] text-slate-400">创意补充</span>
            <p class="mt-1 leading-6">{{ task.creativePrompt }}</p>
          </div>
          <div v-if="task.errorMessage" class="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-200">
            {{ task.errorMessage }}
          </div>
          <button
            v-if="task.status === 'FAILED'"
            @click="handleRetry"
            class="w-fit rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-400"
          >
            失败重试
          </button>
        </div>
      </template>
    </div>

    <div class="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-panel">
      <PageHeader
        eyebrow="Outputs"
        title="生成结果"
        description="当前版本支持预览和下载生成素材。"
      />

      <div v-if="loading && !task" class="rounded-[24px] border border-dashed border-white/15 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
        任务完成后会在这里展示剪辑结果。
      </div>

      <div v-else-if="!task || task.outputs.length === 0" class="rounded-[24px] border border-dashed border-white/15 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
        任务完成后会在这里展示剪辑结果。
      </div>

      <div v-else class="grid gap-4">
        <article v-for="output in task.outputs" :key="output.id" class="rounded-[24px] border border-white/10 bg-slate-950/40 p-4">
          <div class="flex flex-col gap-4 xl:flex-row">
            <video :src="resolveStorageUrl(output.previewUrl)" controls class="aspect-[9/16] w-full max-w-[240px] rounded-2xl border border-white/10 bg-black object-cover"></video>
            <div class="flex-1">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h3 class="text-lg font-medium text-white">{{ output.title }}</h3>
                  <p class="mt-2 text-sm leading-6 text-slate-300">{{ output.reason }}</p>
                </div>
                <a :href="resolveStorageUrl(output.downloadUrl)" class="rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-400" download>下载</a>
              </div>
              <div class="mt-4 grid grid-cols-3 gap-3 text-sm text-slate-300">
                <div>片段序号：{{ output.clipIndex }}</div>
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
import { useRoute } from "vue-router";
import { getRuntimeConfig } from "@/api/runtime-config";
import { fetchTask, retryTask } from "@/api/tasks";
import type { TaskDetail } from "@/types";
import PageHeader from "@/components/PageHeader.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import TimelineStage from "@/components/TimelineStage.vue";
import { usePolling } from "@/composables/usePolling";
import { formatTaskStatus, isTerminalTaskStatus } from "@/utils/task";
import { resolveRuntimeUrl } from "@/utils/url";

const route = useRoute();
const task = ref<TaskDetail | null>(null);
const loading = ref(true);
const errorMessage = ref("");

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

function resolveStorageUrl(value: string) {
  return resolveRuntimeUrl(value, getRuntimeConfig().storageBaseUrl);
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

async function handleRetry() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    return;
  }
  loading.value = true;
  try {
    task.value = await retryTask(taskId.value);
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

const { start, stop } = usePolling(async () => {
  await loadTask();
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
    loading.value = true;
    await start();
  },
  { immediate: true }
);
</script>
