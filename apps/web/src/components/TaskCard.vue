<template>
  <article
    class="group relative min-w-0 overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.9),rgba(8,11,24,0.76))] p-5 shadow-[0_20px_60px_rgba(0,0,0,0.32)] transition duration-200 hover:-translate-y-0.5 hover:border-rose-300/30 hover:shadow-[0_24px_80px_rgba(225,29,72,0.12)]"
    :class="statusFrameClass"
  >
    <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
    <div class="pointer-events-none absolute left-0 top-0 h-full w-1 rounded-r-full" :class="statusRailClass"></div>
    <div class="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-rose-500/10 blur-3xl transition duration-300 group-hover:bg-amber-500/12"></div>
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">{{ task.platform }} / {{ task.aspectRatio ?? "9:16" }}</p>
        <h3 class="mt-2 line-clamp-2 text-[17px] font-semibold leading-6 text-white">{{ task.title }}</h3>
        <p class="mt-2 truncate text-sm leading-6 text-slate-300" :title="task.sourceFileName || '源文件信息待同步'">
          {{ task.sourceFileName || "源文件信息待同步" }}
        </p>
      </div>
      <div class="shrink-0">
        <StatusBadge :status="task.status" />
      </div>
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <span v-if="task.mixcutEnabled" class="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1 text-[11px] font-medium text-rose-100">多素材混剪</span>
      <span v-if="task.hasTimedTranscript" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-[11px] font-medium text-sky-100">时间轴字幕</span>
      <span v-else-if="task.hasTranscript" class="rounded-full border border-fuchsia-400/20 bg-fuchsia-500/10 px-3 py-1 text-[11px] font-medium text-fuchsia-100">文本语义</span>
      <span v-if="task.status === 'FAILED'" class="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1 text-[11px] font-medium text-rose-100">需要处理</span>
      <span v-if="task.status === 'COMPLETED'" class="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-medium text-emerald-100">可复盘</span>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300">
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">进度</p>
        <p class="mt-2 text-base font-semibold text-white">{{ task.progress }}%</p>
      </div>
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">输出</p>
        <p class="mt-2 text-base font-semibold text-white">{{ completedOutputCount }} / {{ task.outputCount }}</p>
      </div>
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">时长</p>
        <p class="mt-2 text-base font-semibold text-white">{{ durationLabel }}</p>
      </div>
      <div class="rounded-2xl border border-white/8 bg-white/[0.04] p-3">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">重试</p>
        <p class="mt-2 text-base font-semibold text-white">{{ retryCount }}</p>
      </div>
    </div>

    <div class="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
      <div class="h-full rounded-full bg-gradient-to-r from-rose-500 via-orange-400 to-amber-300 transition-all duration-300" :style="{ width: `${task.progress}%` }"></div>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
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
      return "bg-gradient-to-b from-emerald-400/80 via-emerald-300/50 to-cyan-300/40";
    case "failed":
      return "bg-gradient-to-b from-rose-400/80 via-red-300/50 to-amber-300/40";
    case "running":
      return "bg-gradient-to-b from-sky-400/80 via-cyan-300/50 to-fuchsia-300/40";
    default:
      return "bg-gradient-to-b from-slate-400/60 via-slate-300/35 to-slate-200/20";
  }
});
const statusFrameClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "hover:shadow-[0_24px_80px_rgba(16,185,129,0.12)]";
    case "failed":
      return "hover:shadow-[0_24px_80px_rgba(244,63,94,0.12)]";
    case "running":
      return "hover:shadow-[0_24px_80px_rgba(56,189,248,0.12)]";
    default:
      return "";
  }
});
</script>
