<template>
  <article
    class="group relative min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition duration-200 hover:border-slate-300 hover:shadow-md"
    :class="[statusFrameClass, selectable ? 'cursor-pointer' : '', selected ? 'border-slate-400 ring-2 ring-slate-200/80' : '']"
    @click="handleSelect"
  >
    <div class="pointer-events-none absolute left-0 top-0 h-full w-1" :class="statusRailClass"></div>
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0 pl-1">
        <p class="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">{{ task.aspectRatio ?? "9:16" }}</p>
        <h3 class="mt-2 line-clamp-2 text-[17px] font-semibold leading-7 text-slate-900">{{ task.title }}</h3>
        <p class="mt-1.5 truncate text-sm leading-6 text-slate-600" :title="task.sourceFileName || '文本生成任务'">
          {{ task.sourceFileName || "文本生成任务" }}
        </p>
      </div>
      <div class="shrink-0">
        <StatusBadge :status="task.status" />
      </div>
    </div>

    <div class="mt-3 flex flex-wrap gap-1.5">
      <span v-if="task.hasTimedTranscript" class="surface-chip">时间轴字幕</span>
      <span v-else-if="task.hasTranscript" class="surface-chip">文本输入</span>
      <span v-if="task.status === 'FAILED'" class="surface-chip">需要处理</span>
      <span v-if="task.status === 'COMPLETED'" class="surface-chip">可查看结果</span>
      <span v-if="task.status === 'PAUSED'" class="surface-chip">可继续生成</span>
    </div>

    <div class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-sm text-slate-600">
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-slate-500">进度</p>
        <p class="text-sm font-semibold text-slate-900">{{ task.progress }}%</p>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-slate-500">时长</p>
        <p class="text-sm font-semibold text-slate-900">{{ durationLabel }}</p>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-slate-500">重试</p>
        <p class="text-sm font-semibold text-slate-900">{{ retryCount }}</p>
      </div>
    </div>

    <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200">
      <div class="h-full rounded-full bg-slate-500 transition-all duration-300" :style="{ width: `${task.progress}%` }"></div>
    </div>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
      <span>更新时间 {{ updatedAtLabel }}</span>
      <span>{{ lifecycleLabel }}</span>
    </div>

    <div class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <button v-if="selectable" class="btn-secondary" type="button" @click.stop="handleSelect">
        {{ selected ? "已展开" : "展开详情" }}
      </button>
      <RouterLink v-else :to="{ path: '/tasks', query: { selected: task.id } }" class="btn-secondary">
        查看详情
      </RouterLink>
      <button
        v-if="canPause"
        class="btn-secondary"
        :disabled="busy"
        type="button"
        @click.stop="$emit('pause', task)"
      >
        暂停
      </button>
      <button
        v-if="canContinue"
        class="btn-primary"
        :disabled="busy"
        type="button"
        @click.stop="$emit('continue', task)"
      >
        继续生成
      </button>
      <button
        v-if="canTerminate"
        class="btn-warning"
        :disabled="busy"
        type="button"
        @click.stop="$emit('terminate', task)"
      >
        终止
      </button>
      <button
        v-if="showRetryAction && task.status === 'FAILED'"
        class="btn-warning"
        :disabled="busy"
        type="button"
        @click.stop="$emit('retry', task)"
      >
        失败重试
      </button>
      <button
        v-if="showDeleteAction"
        class="btn-danger"
        :disabled="busy || running"
        type="button"
        @click.stop="$emit('delete', task)"
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
  selectable?: boolean;
  selected?: boolean;
  showRetryAction?: boolean;
  showDeleteAction?: boolean;
}>();

const emit = defineEmits<{
  (event: "pause", task: TaskListItem): void;
  (event: "continue", task: TaskListItem): void;
  (event: "terminate", task: TaskListItem): void;
  (event: "retry", task: TaskListItem): void;
  (event: "delete", task: TaskListItem): void;
  (event: "select", task: TaskListItem): void;
}>();

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
const canPause = computed(() => ["PENDING", "ANALYZING", "PLANNING"].includes(props.task.status));
const canContinue = computed(() => props.task.status === "PAUSED");
const canTerminate = computed(() => ["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(props.task.status));
const lifecycleLabel = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "归档完成";
    case "failed":
      return "处理失败";
    case "paused":
      return "已暂停，可继续";
    case "running":
      return "正在处理";
    default:
      return "等待开始";
  }
});
const statusRailClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "bg-emerald-400";
    case "failed":
      return "bg-rose-400";
    case "paused":
      return "bg-amber-400";
    case "running":
      return "bg-sky-400";
    default:
      return "bg-slate-300";
  }
});
const statusFrameClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "hover:border-emerald-300";
    case "failed":
      return "hover:border-rose-300";
    case "paused":
      return "hover:border-amber-300";
    case "running":
      return "hover:border-sky-300";
    default:
      return "";
  }
});

const selectable = computed(() => Boolean(props.selectable));
const selected = computed(() => Boolean(props.selected));
const showRetryAction = computed(() => props.showRetryAction !== false);
const showDeleteAction = computed(() => props.showDeleteAction !== false);

function handleSelect() {
  if (!selectable.value) {
    return;
  }
  emit("select", props.task);
}
</script>
