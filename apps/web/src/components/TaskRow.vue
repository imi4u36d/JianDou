<template>
  <article class="relative grid min-w-0 gap-4 overflow-hidden rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.9),rgba(8,11,24,0.76))] px-4 py-4 shadow-[0_14px_40px_rgba(0,0,0,0.2)] lg:grid-cols-[minmax(0,2.15fr)_minmax(0,1.05fr)_minmax(220px,240px)]">
    <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
    <div class="pointer-events-none absolute left-0 top-0 h-full w-1 rounded-r-full" :class="statusRailClass"></div>
    <div class="min-w-0 pl-2 sm:pl-3">
      <div class="flex flex-wrap items-center gap-2">
        <StatusBadge :status="task.status" />
        <span class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{{ task.platform }} / {{ task.aspectRatio ?? "9:16" }}</span>
        <span v-if="task.mixcutEnabled" class="rounded-full border border-rose-400/20 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-100">多素材混剪</span>
        <span v-if="task.hasTimedTranscript" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-[11px] text-sky-100">时间轴字幕</span>
        <span v-else-if="task.hasTranscript" class="rounded-full border border-fuchsia-400/20 bg-fuchsia-500/10 px-2.5 py-1 text-[11px] text-fuchsia-100">文本语义</span>
      </div>
      <h3 class="mt-3 line-clamp-2 text-[15px] font-semibold leading-6 text-white">{{ task.title }}</h3>
      <p class="mt-1 truncate text-sm text-slate-300" :title="task.sourceFileName || '源文件信息待同步'">{{ task.sourceFileName || "源文件信息待同步" }}</p>
      <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div class="h-full rounded-full bg-gradient-to-r from-rose-500 via-orange-400 to-amber-300 transition-all duration-300" :style="{ width: `${task.progress}%` }"></div>
      </div>
      <div class="mt-3 flex flex-wrap gap-3 text-xs text-slate-400">
        <span>进度 {{ task.progress }}%</span>
        <span>输出 {{ completedOutputCount }} / {{ task.outputCount }}</span>
        <span>时长 {{ durationLabel }}</span>
        <span>重试 {{ retryCount }}</span>
      </div>
    </div>

    <div class="grid gap-2 text-sm text-slate-300 sm:grid-cols-2 lg:grid-cols-1">
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-[11px] uppercase tracking-[0.24em] text-slate-500">更新时间</p>
        <p class="mt-2 text-sm font-medium text-white">{{ updatedAtLabel }}</p>
      </div>
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-[11px] uppercase tracking-[0.24em] text-slate-500">状态说明</p>
        <p class="mt-2 text-sm font-medium text-white">{{ lifecycleLabel }}</p>
      </div>
    </div>

    <div class="grid gap-2 sm:grid-cols-2 lg:w-[230px] lg:grid-cols-1">
      <RouterLink :to="`/tasks/${task.id}`" class="btn-secondary w-full">
        查看详情
      </RouterLink>
      <button
        class="btn-primary w-full"
        :disabled="busy"
        type="button"
        @click="$emit('clone', task)"
      >
        复制参数
      </button>
      <button
        v-if="task.status === 'FAILED'"
        class="btn-warning w-full"
        :disabled="busy"
        type="button"
        @click="$emit('retry', task)"
      >
        失败重试
      </button>
      <button
        class="btn-danger w-full"
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
      return "已完成，可直接复盘";
    case "failed":
      return "失败，建议重试或删除";
    case "running":
      return "正在处理，请稍后";
    default:
      return "等待开始";
  }
});
const statusRailClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "bg-gradient-to-b from-emerald-400/80 via-emerald-300/50 to-cyan-300/40";
    case "failed":
      return "bg-gradient-to-b from-rose-400/80 via-red-300/50 to-amber-300/40";
    case "running":
      return "bg-gradient-to-b from-sky-400/80 via-cyan-300/50 to-fuchsia-300/40";
    default:
      return "bg-gradient-to-b from-slate-400/60 via-slate-300/35 to-slate-200/20";
  }
});
</script>
