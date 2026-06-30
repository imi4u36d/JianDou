<template>
  <article
    class="image-task-list-item"
    :class="{ 'image-task-list-item-active': active }"
  >
    <button
      type="button"
      class="image-task-list-item__select"
      :aria-label="`查看${item.title}`"
      @click="$emit('select', item)"
    >
      <span class="image-task-list-item__thumb" aria-hidden="true">
        <img
          v-if="item.thumbnailUrl"
          :src="item.thumbnailUrl"
          :alt="item.title"
          loading="lazy"
          decoding="async"
        />
        <IconImage v-else size="sm" />
      </span>
      <span class="image-task-list-item__body">
        <span
          class="image-task-list-item__title"
          :title="item.title"
        >
          <span class="image-task-list-item__title-text">{{ item.title }}</span>
        </span>
        <span class="image-task-list-item__meta-row">
          <span class="image-task-list-item__status" :class="`image-task-list-item__status-${statusTone}`">{{ statusLabel }}</span>
          <span class="image-task-list-item__meta-tag" :title="`运行耗时：${elapsedLabel}`">{{ elapsedLabel }}</span>
        </span>
      </span>
    </button>
    <span class="image-task-list-item__side">
      <button
        type="button"
        class="image-task-list-item__delete"
        aria-label="删除任务"
        title="删除"
        @click.stop="$emit('delete', item)"
      >
        <IconDelete size="xs" />
      </button>
    </span>
  </article>
</template>

<script setup lang="ts">
/**
 * 图片任务列表卡片组件。
 */
import { computed, onUnmounted, ref, watch } from "vue";
import IconDelete from "@/components/icons/IconDelete.vue";
import IconImage from "@/components/icons/IconImage.vue";
import type { ImageTaskListItem } from "@/types/image-task-list";

const props = defineProps<{
  item: ImageTaskListItem;
  active: boolean;
}>();

defineEmits<{
  select: [item: ImageTaskListItem];
  delete: [item: ImageTaskListItem];
}>();

const statusLabel = computed(() => {
  const s = props.item.status;
  switch (s.toLowerCase()) {
    case "pending":
    case "analyzing":
    case "planning":
    case "rendering":
      return `${Math.max(0, Math.min(99, Math.round(props.item.progress)))}%`;
    case "paused": return "已暂停";
    case "completed": return "已完成";
    case "failed": return "失败";
    default: return s;
  }
});

const statusTone = computed(() => {
  const s = props.item.status;
  if (["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(s)) return "active";
  if (["COMPLETED"].includes(s)) return "done";
  if (["FAILED"].includes(s)) return "failed";
  if (["PAUSED"].includes(s)) return "paused";
  return "idle";
});

const activeStatuses = new Set(["PENDING", "ANALYZING", "PLANNING", "RENDERING"]);
const nowTick = ref(Date.now());
let elapsedTimer: number | null = null;

function timeValue(raw?: string | null): number | null {
  if (!raw) return null;
  const date = new Date(raw);
  const value = date.getTime();
  return Number.isNaN(value) ? null : value;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  if (totalSeconds < 60) return `${totalSeconds}秒`;
  const totalMinutes = Math.floor(totalSeconds / 60);
  if (totalMinutes < 60) return `${totalMinutes}分钟`;
  const totalHours = Math.floor(totalMinutes / 60);
  if (totalHours < 24) return `${totalHours}小时`;
  const totalDays = Math.floor(totalHours / 24);
  return `${totalDays}天`;
}

const shouldTickElapsed = computed(() => Boolean(props.item.startedAt && activeStatuses.has(props.item.status)));

const elapsedLabel = computed(() => {
  const start = timeValue(props.item.startedAt);
  if (start == null) return "0秒";
  const finish = timeValue(props.item.finishedAt);
  const end = finish ?? (shouldTickElapsed.value ? nowTick.value : timeValue(props.item.updatedAt) ?? nowTick.value);
  return formatElapsed(end - start);
});

watch(shouldTickElapsed, (shouldTick) => {
  if (elapsedTimer !== null) {
    window.clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
  if (shouldTick) {
    nowTick.value = Date.now();
    elapsedTimer = window.setInterval(() => {
      nowTick.value = Date.now();
    }, 1000);
  }
}, { immediate: true });

onUnmounted(() => {
  if (elapsedTimer !== null) {
    window.clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
});
</script>

<style scoped>
.image-task-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24px;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 76px;
  padding: 0 12px 0 0;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 5px 14px rgba(15, 23, 42, 0.05);
  transition:
    background 150ms ease,
    border-color 150ms ease,
    box-shadow 150ms ease;
}

.image-task-list-item:hover,
.image-task-list-item:focus-within {
  background: rgba(255, 255, 255, 0.86);
  border-color: rgba(99, 102, 241, 0.18);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 8px 20px rgba(15, 23, 42, 0.07);
}

.image-task-list-item-active {
  background: rgba(255, 255, 255, 0.92);
  border-color: var(--accent-indigo);
  box-shadow:
    0 0 0 1px rgba(99, 102, 241, 0.14),
    0 10px 24px rgba(99, 102, 241, 0.12);
}

.image-task-list-item-active:hover,
.image-task-list-item-active:focus-within {
  background: rgba(255, 255, 255, 0.94);
  border-color: var(--accent-indigo);
}

.image-task-list-item__select {
  appearance: none;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  min-height: 74px;
  padding: 12px 0 11px 12px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.image-task-list-item__select:focus {
  outline: 0;
}

.image-task-list-item__select:focus-visible {
  border-radius: calc(var(--radius-md) - 2px);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) inset;
}

.image-task-list-item__body {
  display: grid;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.image-task-list-item__thumb {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  border-radius: 7px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.06);
  color: var(--text-muted);
}

.image-task-list-item__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.image-task-list-item__meta-row {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.image-task-list-item__title {
  display: block;
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-task-list-item__title-text {
  display: inline-block;
  min-width: 100%;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  will-change: transform;
}

.image-task-list-item__meta-tag,
.image-task-list-item__status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  font-size: 0.72rem;
  line-height: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-task-list-item__meta-tag {
  width: 72px;
}

.image-task-list-item__status {
  min-width: 46px;
}

.image-task-list-item__status-active { color: var(--accent-indigo); font-weight: 600; }
.image-task-list-item__status-done { color: var(--accent-lime); }
.image-task-list-item__status-failed { color: var(--accent-danger); }
.image-task-list-item__status-paused { color: var(--accent-warning); }

.image-task-list-item__side {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  flex-shrink: 0;
}

.image-task-list-item__delete {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition:
    background 150ms ease,
    color 150ms ease;
}

.image-task-list-item__delete:hover {
  background: rgba(239, 68, 68, 0.08);
  color: var(--accent-danger);
}
</style>
