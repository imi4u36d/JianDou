<template>
  <button
    type="button"
    class="unified-list-item"
    :class="{ 'unified-list-item-active': active }"
    :aria-label="`查看${item.title}`"
    @click="$emit('select', item)"
  >
    <span class="unified-list-item__badge" :class="`unified-list-item__badge-${badgeClass}`" aria-hidden="true">
      <img v-if="item.thumbnailUrl" :src="item.thumbnailUrl" alt="" class="unified-list-item__thumb" />
      <AppIcon v-else :name="iconName" size="sm" />
    </span>
    <span class="unified-list-item__body">
      <span class="unified-list-item__title">{{ item.title }}</span>
      <span class="unified-list-item__meta">
        <span class="unified-list-item__kind">{{ kindLabel }}</span>
        <span class="unified-list-item__status" :class="`unified-list-item__status-${statusTone}`">{{ statusLabel }}</span>
        <time :datetime="item.updatedAt || item.createdAt || undefined">{{ compactTime }}</time>
      </span>
      <span class="unified-list-item__progress" aria-hidden="true"><i :style="{ width: `${item.progress}%` }"></i></span>
    </span>
    <span class="unified-list-item__side">
      <strong>{{ item.progress }}%</strong>
    </span>
  </button>
</template>

<script setup lang="ts">
/**
 * 统一列表行组件。
 */
import { computed } from "vue";
import { AppIcon, type IconName } from "@/components/icons";
import type { UnifiedListItem } from "@/types/unified-task";

const props = defineProps<{
  item: UnifiedListItem;
  active: boolean;
}>();

defineEmits<{
  select: [item: UnifiedListItem];
}>();

const iconName = computed<IconName>(() => {
  if (props.item.kind === "workflow") return "workflow";
  switch (props.item.taskType) {
    case "image_generation":
    case "image_to_image": return "image";
    case "character_sheet": return "character";
    case "video_generation": return "video";
    default: return "task";
  }
});

const kindLabel = computed(() => {
  if (props.item.kind === "workflow") return "工作流";
  switch (props.item.taskType) {
    case "image_generation": return "文生图";
    case "image_to_image": return "图生图";
    case "character_sheet": return "三视图";
    case "video_generation": return "视频";
    default: return "任务";
  }
});

const badgeClass = computed(() => {
  if (props.item.kind === "workflow") return "workflow";
  switch (props.item.taskType) {
    case "image_generation":
    case "image_to_image": return "image";
    case "character_sheet": return "character";
    case "video_generation": return "video";
    default: return "task";
  }
});

const statusLabel = computed(() => {
  const s = props.item.status;
  if (props.item.kind === "workflow") {
    switch (s.toLowerCase()) {
      case "draft": return "草稿";
      case "ready": return "进行中";
      case "completed": return "已完成";
      case "failed": return "失败";
      default: return s;
    }
  }
  switch (s) {
    case "PENDING": return "排队";
    case "PAUSED": return "已暂停";
    case "ANALYZING": return "分析中";
    case "PLANNING": return "编排中";
    case "RENDERING": return "生成中";
    case "COMPLETED": return "已完成";
    case "FAILED": return "失败";
    default: return s;
  }
});

const statusTone = computed(() => {
  const s = props.item.status;
  if (["RENDERING", "ANALYZING", "PLANNING", "READY"].includes(s)) return "active";
  if (["COMPLETED"].includes(s)) return "done";
  if (["FAILED"].includes(s)) return "failed";
  if (["PAUSED"].includes(s)) return "paused";
  return "idle";
});

const compactTime = computed(() => {
  const raw = props.item.updatedAt || props.item.createdAt;
  if (!raw) return "";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}天前`;
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit" }).format(date);
});
</script>

<style scoped>
.unified-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, border-color 0.15s;
}

.unified-list-item:hover {
  background: var(--bg-softer);
}

.unified-list-item-active {
  background: rgba(99, 102, 241, 0.06);
  border-color: var(--accent-indigo);
}

.unified-list-item__badge {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  flex-shrink: 0;
  overflow: hidden;
}

.unified-list-item__badge-video { background: rgba(99, 102, 241, 0.1); color: var(--accent-indigo); }
.unified-list-item__badge-image { background: rgba(99, 102, 241, 0.1); color: var(--accent-indigo); }
.unified-list-item__badge-character { background: rgba(22, 163, 74, 0.1); color: var(--accent-lime); }
.unified-list-item__badge-workflow { background: rgba(99, 102, 241, 0.08); color: var(--accent-indigo); }
.unified-list-item__badge-task { background: var(--bg-softer); color: var(--text-muted); }

.unified-list-item__thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.unified-list-item__body {
  display: grid;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.unified-list-item__title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unified-list-item__meta {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.unified-list-item__kind {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--bg-softer);
  font-weight: 600;
}

.unified-list-item__status-active { color: var(--accent-indigo); font-weight: 600; }
.unified-list-item__status-done { color: var(--accent-lime); }
.unified-list-item__status-failed { color: var(--accent-danger); }
.unified-list-item__status-paused { color: var(--accent-warning); }

.unified-list-item__progress {
  display: block;
  height: 3px;
  border-radius: 2px;
  background: var(--bg-softer);
  overflow: hidden;
}

.unified-list-item__progress i {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--accent-indigo);
  transition: width 0.3s;
}

.unified-list-item__side {
  flex-shrink: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 600;
}
</style>
