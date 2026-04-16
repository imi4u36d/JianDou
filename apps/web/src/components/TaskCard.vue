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
      <span v-if="task.taskSeed !== null && task.taskSeed !== undefined" class="surface-chip">种子 {{ task.taskSeed }}</span>
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
        <p>种子</p>
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
/**
 * 任务组件。
 */
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

/**
 * 处理处理Select。
 */
function handleSelect() {
  if (!selectable.value) {
    return;
  }
  emit("select", props.task);
}

</script>

<style scoped>
.neo-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    rgba(14, 18, 26, 0.92);
  color: rgba(255, 255, 255, 0.88);
  box-shadow: var(--shadow-panel);
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.neo-card:hover {
  transform: translateY(-2px);
  border-color: rgba(145, 180, 255, 0.22);
  box-shadow: var(--shadow-glow);
}
.neo-card-selected {
  border-color: rgba(145, 180, 255, 0.4);
  box-shadow: var(--shadow-glow);
}
.task-card__rail {
  opacity: 0.9;
  box-shadow: 0 0 18px rgba(145, 180, 255, 0.24);
}
.task-card__rail--completed {
  background: #68e0b0;
}
.task-card__rail--failed {
  background: #ff8fa9;
}
.task-card__rail--paused {
  background: #ffce72;
}
.task-card__rail--running {
  background: #6ed5ff;
}
.task-card__rail--idle {
  background: rgba(255, 255, 255, 0.42);
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
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
.neo-stat-row {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.8rem;
}
.neo-stat-row strong {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
}
.neo-progress-track {
  height: 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}
.neo-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #b05cff 0%, #4edbff 100%);
  box-shadow: 0 0 22px rgba(78, 219, 255, 0.24);
  transition: width 0.25s ease;
}
.neo-button {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.86);
  box-shadow: var(--shadow-soft);
  transition: box-shadow 0.2s ease;
}
.neo-button:active {
  box-shadow: var(--shadow-glow);
}
.neo-button-accent {
  color: #081018;
  background: linear-gradient(90deg, #b05cff 0%, #4edbff 100%);
  box-shadow:
    0 14px 32px rgba(128, 99, 255, 0.28),
    0 0 38px rgba(78, 219, 255, 0.14);
}
.neo-button-accent:active {
  box-shadow: var(--shadow-glow);
}
:deep(.surface-chip) {
  border: 1px solid rgba(145, 180, 255, 0.18);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.68);
  box-shadow: none;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  padding: 0.4rem 0.7rem;
}

.neo-card :deep(.text-slate-900) {
  color: rgba(255, 255, 255, 0.94) !important;
}

.neo-card :deep(.text-slate-600),
.neo-card :deep(.text-slate-500) {
  color: rgba(255, 255, 255, 0.52) !important;
}
</style>
