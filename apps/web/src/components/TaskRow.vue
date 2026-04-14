<template>
  <article
    class="relative grid min-w-0 gap-4 overflow-hidden rounded-[32px] bg-transparent px-4 py-4 neo-row"
    :class="[selectable ? 'cursor-pointer' : '', selected ? 'neo-row-selected' : '', busy ? 'neo-card-busy' : '']"
    @click="handleSelect"
  >
    <div class="pointer-events-none absolute left-4 top-4 h-[calc(100%-2rem)] w-1.5 rounded-full task-row__rail" :class="statusRailClass"></div>
    <div class="min-w-0 pl-2 sm:pl-3">
      <div class="flex flex-wrap items-center gap-2">
        <StatusBadge :status="task.status" />
        <span class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{{ task.aspectRatio ?? "9:16" }}</span>
        <span v-if="task.hasTimedTranscript" class="surface-chip">时间轴字幕</span>
        <span v-else-if="task.hasTranscript" class="surface-chip">文本输入</span>
      </div>
      <h3 class="mt-3 line-clamp-2 text-[16px] font-semibold leading-6 text-slate-900">{{ task.title }}</h3>
      <p class="mt-1 truncate text-sm text-slate-600" :title="task.sourceFileName || '文本生成任务'">{{ task.sourceFileName || "文本生成任务" }}</p>
      <div class="mt-3 neo-progress-track" aria-hidden="true">
        <div class="neo-progress-fill" :style="{ width: `${task.progress}%` }"></div>
      </div>
      <div class="mt-3 neo-row-stats">
        <div>
          <p>进度</p>
          <strong>{{ task.progress }}%</strong>
        </div>
        <div>
          <p>时长</p>
          <strong>{{ durationLabel }}</strong>
        </div>
        <div>
          <p>重试</p>
          <strong>{{ retryCount }}</strong>
        </div>
        <div>
          <p>评分</p>
          <strong>{{ effectRatingLabel }}</strong>
        </div>
        <div>
          <p>Seed</p>
          <strong>{{ seedLabel }}</strong>
        </div>
      </div>
    </div>

    <div class="grid gap-2 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-1">
      <div class="neo-info-card">
        <p class="neo-info-label">更新时间</p>
        <p class="neo-info-value">{{ updatedAtLabel }}</p>
      </div>
      <div class="neo-info-card">
        <p class="neo-info-label">状态说明</p>
        <p class="neo-info-value">{{ lifecycleLabel }}</p>
      </div>
      <div class="neo-info-card">
        <p class="neo-info-label">效果评分</p>
        <p class="neo-info-value">{{ effectRatingLabel }}</p>
      </div>
      <div class="neo-info-card">
        <p class="neo-info-label">任务 Seed</p>
        <p class="neo-info-value">{{ seedLabel }}</p>
      </div>
    </div>

    <div class="grid gap-2 sm:grid-cols-2 lg:w-[230px] lg:grid-cols-1">
      <button v-if="selectable" class="btn-secondary neo-button w-full" type="button" @click.stop="handleSelect">
        {{ selected ? "已展开" : "展开详情" }}
      </button>
      <RouterLink v-else :to="{ path: '/tasks', query: { selected: task.id } }" class="btn-secondary neo-button w-full">
        查看详情
      </RouterLink>
      <button
        v-if="canPause"
        class="btn-secondary neo-button w-full"
        :disabled="busy"
        type="button"
        @click="$emit('pause', task)"
      >
        暂停
      </button>
      <button
        v-if="canContinue"
        class="btn-primary neo-button neo-button-accent w-full"
        :disabled="busy"
        type="button"
        @click="$emit('continue', task)"
      >
        继续生成
      </button>
      <button
        v-if="canTerminate"
        class="btn-warning neo-button w-full"
        :disabled="busy"
        type="button"
        @click="$emit('terminate', task)"
      >
        终止
      </button>
      <button
        v-if="task.status === 'FAILED'"
        class="btn-warning neo-button w-full"
        :disabled="busy"
        type="button"
        @click="$emit('retry', task)"
      >
        失败重试
      </button>
      <button
        class="btn-danger neo-button w-full"
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
  selectable?: boolean;
  selected?: boolean;
}>();

const retryCount = computed(() => props.task.retryCount ?? 0);
const lifecycleGroup = computed(() => getTaskLifecycleGroup(props.task.status));
const durationLabel = computed(() => {
  if (typeof props.task.minDurationSeconds === "number" && typeof props.task.maxDurationSeconds === "number") {
    return formatTaskRange(props.task.minDurationSeconds, props.task.maxDurationSeconds);
  }
  return "待配置";
});
const effectRatingLabel = computed(() => {
  const rating = props.task.effectRating;
  return typeof rating === "number" && Number.isFinite(rating) && rating > 0 ? `${Math.trunc(rating)}/5` : "未评分";
});
const seedLabel = computed(() => {
  const seed = props.task.taskSeed;
  return typeof seed === "number" && Number.isFinite(seed) ? String(Math.trunc(seed)) : "未设置";
});
const updatedAtLabel = computed(() => new Date(props.task.updatedAt).toLocaleString());
const running = computed(() => lifecycleGroup.value === "running");
const canPause = computed(() => ["PENDING", "ANALYZING", "PLANNING"].includes(props.task.status));
const canContinue = computed(() => props.task.status === "PAUSED");
const canTerminate = computed(() => ["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(props.task.status));
const selectable = computed(() => Boolean(props.selectable));
const selected = computed(() => Boolean(props.selected));
const lifecycleLabel = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "已完成，可查看结果";
    case "failed":
      return "失败，建议重试或删除";
    case "paused":
      return "已暂停，可继续生成";
    case "running":
      return "正在处理，请稍后";
    default:
      return "等待开始";
  }
});
const statusRailClass = computed(() => {
  switch (lifecycleGroup.value) {
    case "completed":
      return "task-row__rail--completed";
    case "failed":
      return "task-row__rail--failed";
    case "paused":
      return "task-row__rail--paused";
    case "running":
      return "task-row__rail--running";
    default:
      return "task-row__rail--idle";
  }
});

const emit = defineEmits<{
  (event: "pause", task: TaskListItem): void;
  (event: "continue", task: TaskListItem): void;
  (event: "terminate", task: TaskListItem): void;
  (event: "retry", task: TaskListItem): void;
  (event: "delete", task: TaskListItem): void;
  (event: "select", task: TaskListItem): void;
}>();

function handleSelect() {
  if (!selectable.value) {
    return;
  }
  emit("select", props.task);
}
</script>

<style scoped>
.neo-row {
  background: #E0E5EC;
  box-shadow:
    16px 16px 32px rgba(138, 148, 164, 0.45),
    -16px -16px 32px rgba(255, 255, 255, 0.95);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.neo-row:hover {
  transform: translateY(-2px);
  box-shadow:
    16px 16px 36px rgba(138, 148, 164, 0.45),
    -16px -16px 36px rgba(255, 255, 255, 0.95);
}
.neo-row-selected {
  box-shadow:
    inset 10px 10px 20px rgba(157, 166, 184, 0.35),
    inset -10px -10px 20px rgba(255, 255, 255, 0.95);
}
.task-row__rail {
  opacity: 0.9;
  box-shadow:
    inset 1px 1px 2px rgba(255, 255, 255, 0.65),
    inset -1px -1px 2px rgba(94, 105, 122, 0.16);
}
.task-row__rail--completed {
  background: #7e9d8d;
}
.task-row__rail--failed {
  background: #b37d87;
}
.task-row__rail--paused {
  background: #b79b79;
}
.task-row__rail--running {
  background: #c9878e;
}
.task-row__rail--idle {
  background: #9aa5b5;
}
.neo-card-busy {
  opacity: 0.95;
}
.neo-row-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 20px;
  background: #E7EBF2;
  box-shadow:
    inset 6px 6px 12px rgba(147, 157, 174, 0.4),
    inset -6px -6px 12px rgba(255, 255, 255, 0.95);
}
.neo-row-stats p {
  font-size: 0.7rem;
  color: #5a6370;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.neo-row-stats strong {
  font-size: 1rem;
  color: #1f2933;
}
.neo-info-card {
  border-radius: 18px;
  padding: 0.9rem;
  background: #E7EBF2;
  box-shadow:
    inset 6px 6px 12px rgba(147, 157, 174, 0.35),
    inset -6px -6px 12px rgba(255, 255, 255, 0.9);
}
.neo-info-label {
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #5a6370;
  margin-bottom: 0.2rem;
}
.neo-info-value {
  font-size: 0.9rem;
  color: #1f2933;
  margin: 0;
}
.neo-progress-track {
  height: 12px;
  border-radius: 999px;
  background: #E7EBF2;
  box-shadow:
    inset 4px 4px 6px rgba(147, 157, 174, 0.4),
    inset -4px -4px 6px rgba(255, 255, 255, 0.9);
}
.neo-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255, 156, 156, 0.2), #efb9b9);
  transition: width 0.24s ease;
}
.neo-button {
  border-radius: 16px;
  background: #E7EBF2;
  color: #1f2a37;
  box-shadow:
    5px 5px 10px rgba(147, 157, 174, 0.25),
    -5px -5px 10px rgba(255, 255, 255, 0.9);
  transition: box-shadow 0.2s ease;
}
.neo-button:active {
  box-shadow:
    inset 4px 4px 8px rgba(147, 157, 174, 0.35),
    inset -4px -4px 8px rgba(255, 255, 255, 0.9);
}
.neo-button-accent {
  background: #ffd3d3;
  color: #371919;
  box-shadow:
    5px 5px 10px rgba(197, 163, 163, 0.35),
    -5px -5px 10px rgba(255, 255, 255, 0.9);
}
.neo-button-accent:active {
  box-shadow:
    inset 4px 4px 8px rgba(197, 163, 163, 0.4),
    inset -4px -4px 8px rgba(255, 255, 255, 0.95);
}
:deep(.surface-chip) {
  border: none;
  background: #E0E5EC;
  color: #5a6370;
  box-shadow:
    inset -2px -2px 6px rgba(255, 255, 255, 0.9),
    inset 2px 2px 6px rgba(147, 157, 174, 0.25);
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  padding: 0.4rem 0.7rem;
}
</style>
