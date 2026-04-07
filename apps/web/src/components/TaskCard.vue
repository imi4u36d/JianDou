<template>
  <article
    class="group relative min-w-0 overflow-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] transition duration-200 hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)]"
    :class="statusFrameClass"
  >
    <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>
    <div class="pointer-events-none absolute left-0 top-0 h-full w-1 rounded-r-full" :class="statusRailClass"></div>
    <div class="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-cyan-100/70 blur-3xl transition duration-300 group-hover:bg-cyan-200/80"></div>
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{{ task.platform }} / {{ task.aspectRatio ?? "9:16" }}</p>
        <h3 class="mt-2 line-clamp-2 text-[18px] font-semibold leading-7 text-slate-900">{{ task.title }}</h3>
        <p class="mt-2 truncate text-sm leading-6 text-slate-600" :title="task.sourceFileName || '源文件信息待同步'">
          {{ task.sourceFileName || "源文件信息待同步" }}
        </p>
      </div>
      <div class="shrink-0">
        <StatusBadge :status="task.status" />
      </div>
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <span v-if="task.mixcutEnabled" class="surface-chip">多素材混剪</span>
      <span v-if="task.hasTimedTranscript" class="surface-chip">时间轴字幕</span>
      <span v-else-if="task.hasTranscript" class="surface-chip">文本语义</span>
      <span v-if="task.status === 'FAILED'" class="surface-chip">需要处理</span>
      <span v-if="task.status === 'COMPLETED'" class="surface-chip">可复盘</span>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-600">
      <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">进度</p>
        <p class="mt-2 text-base font-semibold text-slate-900">{{ task.progress }}%</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">输出</p>
        <p class="mt-2 text-base font-semibold text-slate-900">{{ completedOutputCount }} / {{ task.outputCount }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">时长</p>
        <p class="mt-2 text-base font-semibold text-slate-900">{{ durationLabel }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">重试</p>
        <p class="mt-2 text-base font-semibold text-slate-900">{{ retryCount }}</p>
      </div>
    </div>

    <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
      <div class="h-full rounded-full bg-gradient-to-r from-cyan-500 to-sky-500 transition-all duration-300" :style="{ width: `${task.progress}%` }"></div>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
      <span>更新时间 {{ updatedAtLabel }}</span>
      <span>{{ lifecycleLabel }}</span>
    </div>

    <div class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <RouterLink :to="`/tasks/${task.id}`" class="btn-secondary">
        查看详情
      </RouterLink>
      <button
        class="btn-primary"
        :disabled="busy"
        type="button"
        @click="$emit('clone', task)"
      >
        复制参数
      </button>
      <button
        v-if="task.status === 'FAILED'"
        class="btn-warning"
        :disabled="busy"
        type="button"
        @click="$emit('retry', task)"
      >
        失败重试
      </button>
      <button
        class="btn-danger"
        :disabled="busy || running"
        type="button"
        @click="$emit('delete', task)"
      >
        删除
      </button>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { TaskListItem } from "@/types";
import StatusBadge from "./StatusBadge.vue";
import { formatTaskRange, getTaskLifecycleGroup } from "@/utils/task";

const props = defineProps<{
  task: TaskListItem;
  busy?: boolean;
}>();

defineEmits<{
  (event: "clone", task: TaskListItem): void;
  (event: "retry", task: TaskListItem): void;
  (event: "delete", task: TaskListItem): void;
}>();

const completedOutputCount = computed(() => props.task.completedOutputCount ?? 0);
const retryCount = computed(() => props.task.retryCount ?? 0);
const lifecycleGroup = computed(() => getTaskLifecycleGroup(props.task.status));
const durationLabel = computed(() => {
  if (typeof props.task.minDurationSeconds === "number" && typeof props.task.maxDurationSeconds === "number") {
    return formatTaskRange(props.task.minDurationSeconds, props.task.maxDurationSeconds);
  }
  return "待配置";
});
const updatedAtLabel = computed(() => new Date(props.task.updatedAt).toLocaleString());
const running = computed(() => lifecycleGroup.value === "running");
const lifecycleLabel = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "归档完成";
    case "failed":
      return "处理失败";
    case "running":
      return "正在处理";
    default:
      return "等待开始";
  }
});
const statusRailClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "bg-gradient-to-b from-emerald-400 to-emerald-300";
    case "failed":
      return "bg-gradient-to-b from-rose-400 to-orange-300";
    case "running":
      return "bg-gradient-to-b from-sky-400 to-indigo-300";
    default:
      return "bg-gradient-to-b from-slate-300 to-slate-200";
  }
});
const statusFrameClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "hover:shadow-[0_18px_40px_rgba(16,185,129,0.14)]";
    case "failed":
      return "hover:shadow-[0_18px_40px_rgba(244,63,94,0.14)]";
    case "running":
      return "hover:shadow-[0_18px_40px_rgba(14,165,233,0.14)]";
    default:
      return "";
  }
});
</script>
