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
          <p>种子</p>
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
        <p class="neo-info-label">任务种子</p>
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
.neo-row {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    rgba(14, 18, 26, 0.92);
  box-shadow: var(--shadow-panel);
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.neo-row:hover {
  transform: translateY(-2px);
  border-color: rgba(145, 180, 255, 0.22);
  box-shadow: var(--shadow-glow);
}
.neo-row-selected {
  border-color: rgba(145, 180, 255, 0.4);
  box-shadow: var(--shadow-glow);
}
.task-row__rail {
  opacity: 0.9;
  box-shadow: 0 0 18px rgba(145, 180, 255, 0.24);
}
.task-row__rail--completed {
  background: #68e0b0;
}
.task-row__rail--failed {
  background: #ff8fa9;
}
.task-row__rail--paused {
  background: #ffce72;
}
.task-row__rail--running {
  background: #6ed5ff;
}
.task-row__rail--idle {
  background: rgba(255, 255, 255, 0.42);
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
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
.neo-row-stats p {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.48);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.neo-row-stats strong {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
}
.neo-info-card {
  border-radius: 18px;
  padding: 0.9rem;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
.neo-info-label {
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.48);
  margin-bottom: 0.2rem;
}
.neo-info-value {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
}
.neo-progress-track {
  height: 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}
.neo-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #b05cff 0%, #4edbff 100%);
  box-shadow: 0 0 22px rgba(78, 219, 255, 0.24);
  transition: width 0.24s ease;
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
  background: linear-gradient(90deg, #b05cff 0%, #4edbff 100%);
  color: #081018;
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

.neo-row :deep(.text-slate-900) {
  color: rgba(255, 255, 255, 0.94) !important;
}

.neo-row :deep(.text-slate-600),
.neo-row :deep(.text-slate-500) {
  color: rgba(255, 255, 255, 0.52) !important;
}
</style>
