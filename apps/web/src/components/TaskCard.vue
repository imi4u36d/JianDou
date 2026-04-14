<template>
  <article
    class="group relative min-w-0 overflow-hidden rounded-[30px] bg-transparent p-4 neo-card"
    :class="[
      selectable ? 'cursor-pointer' : '',
      selected ? 'neo-card-selected' : '',
      busy ? 'neo-card-busy' : ''
    ]"
    @click="handleSelect"
  >
    <div class="pointer-events-none absolute left-4 top-4 h-[calc(100%-2rem)] w-1.5 rounded-full task-card__rail" :class="statusRailClass"></div>
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
      <span v-if="task.effectRating" class="surface-chip">评分 {{ effectRatingLabel }}</span>
      <span v-if="task.taskSeed !== null && task.taskSeed !== undefined" class="surface-chip">Seed {{ task.taskSeed }}</span>
    </div>

    <div class="mt-4 neo-stat-grid">
      <div class="neo-stat-row">
        <p>进度</p>
        <strong>{{ task.progress }}%</strong>
      </div>
      <div class="neo-stat-row">
        <p>时长</p>
        <strong>{{ durationLabel }}</strong>
      </div>
      <div class="neo-stat-row">
        <p>重试</p>
        <strong>{{ retryCount }}</strong>
      </div>
      <div class="neo-stat-row">
        <p>评分</p>
        <strong>{{ effectRatingLabel }}</strong>
      </div>
      <div class="neo-stat-row">
        <p>Seed</p>
        <strong>{{ seedLabel }}</strong>
      </div>
    </div>

    <div class="mt-4 neo-progress-track" aria-hidden="true">
      <div class="neo-progress-fill" :style="{ width: `${task.progress}%` }"></div>
    </div>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
      <span>更新时间 {{ updatedAtLabel }}</span>
      <span>{{ lifecycleLabel }}</span>
    </div>

    <div class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <button v-if="selectable" class="btn-secondary neo-button" type="button" @click.stop="handleSelect">
        {{ selected ? "已展开" : "展开详情" }}
      </button>
      <RouterLink v-else :to="{ path: '/tasks', query: { selected: task.id } }" class="btn-secondary neo-button">
        查看详情
      </RouterLink>
      <button
        v-if="canPause"
        class="btn-secondary neo-button"
        :disabled="busy"
        type="button"
        @click.stop="$emit('pause', task)"
      >
        暂停
      </button>
      <button
        v-if="canContinue"
        class="btn-primary neo-button neo-button-accent"
        :disabled="busy"
        type="button"
        @click.stop="$emit('continue', task)"
      >
        继续生成
      </button>
      <button
        v-if="canTerminate"
        class="btn-warning neo-button"
        :disabled="busy"
        type="button"
        @click.stop="$emit('terminate', task)"
      >
        终止
      </button>
      <button
        v-if="showRetryAction && task.status === 'FAILED'"
        class="btn-warning neo-button"
        :disabled="busy"
        type="button"
        @click.stop="$emit('retry', task)"
      >
        失败重试
      </button>
      <button
        v-if="showDeleteAction"
        class="btn-danger neo-button"
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
      return "task-card__rail--completed";
    case "failed":
      return "task-card__rail--failed";
    case "paused":
      return "task-card__rail--paused";
    case "running":
      return "task-card__rail--running";
    default:
      return "task-card__rail--idle";
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

<style scoped>
.neo-card {
  background: #E0E5EC;
  color: #1f2a37;
  box-shadow:
    18px 18px 30px rgba(138, 148, 164, 0.45),
    -18px -18px 30px rgba(255, 255, 255, 0.95);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.neo-card:hover {
  transform: translateY(-2px);
  box-shadow:
    18px 18px 40px rgba(138, 148, 164, 0.45),
    -18px -18px 40px rgba(255, 255, 255, 0.95);
}
.neo-card-selected {
  box-shadow:
    inset 10px 10px 20px rgba(157, 166, 184, 0.35),
    inset -10px -10px 20px rgba(255, 255, 255, 0.95);
}
.task-card__rail {
  opacity: 0.9;
  box-shadow:
    inset 1px 1px 2px rgba(255, 255, 255, 0.65),
    inset -1px -1px 2px rgba(94, 105, 122, 0.16);
}
.task-card__rail--completed {
  background: #7e9d8d;
}
.task-card__rail--failed {
  background: #b37d87;
}
.task-card__rail--paused {
  background: #b79b79;
}
.task-card__rail--running {
  background: #c9878e;
}
.task-card__rail--idle {
  background: #9aa5b5;
}
.neo-card-busy {
  opacity: 0.9;
}
.neo-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 24px;
  background: #E7EBF2;
  box-shadow:
    inset 6px 6px 12px rgba(147, 157, 174, 0.4),
    inset -6px -6px 12px rgba(255, 255, 255, 0.95);
}
.neo-stat-row {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  color: #5a6370;
  font-size: 0.8rem;
}
.neo-stat-row strong {
  font-size: 1rem;
  color: #1f2933;
}
.neo-progress-track {
  height: 14px;
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
  box-shadow:
    inset 4px 4px 8px rgba(255, 255, 255, 0.75),
    inset -4px -4px 8px rgba(255, 255, 255, 0.15);
  transition: width 0.25s ease;
}
.neo-button {
  border-radius: 16px;
  background: #E7EBF2;
  color: #1f2a37;
  box-shadow:
    6px 6px 12px rgba(147, 157, 174, 0.25),
    -6px -6px 12px rgba(255, 255, 255, 0.9);
  transition: box-shadow 0.2s ease;
}
.neo-button:active {
  box-shadow:
    inset 5px 5px 10px rgba(147, 157, 174, 0.35),
    inset -5px -5px 10px rgba(255, 255, 255, 0.9);
}
.neo-button-accent {
  color: #3f1a1a;
  background: #ffd3d3;
  box-shadow:
    6px 6px 12px rgba(197, 163, 163, 0.35),
    -6px -6px 12px rgba(255, 255, 255, 0.9);
}
.neo-button-accent:active {
  box-shadow:
    inset 5px 5px 10px rgba(197, 163, 163, 0.4),
    inset -5px -5px 10px rgba(255, 255, 255, 0.95);
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
