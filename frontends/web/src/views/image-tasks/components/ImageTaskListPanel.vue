<template>
  <aside ref="panelRef" class="image-task-list-panel">
    <label class="image-task-search-field" aria-label="搜索">
      <IconSearch class="image-task-search-field__icon" size="sm" aria-hidden="true" />
      <input v-model="searchText" type="search" placeholder="搜索任务" />
      <button
        v-if="searchText"
        class="image-task-search-field__clear"
        type="button"
        aria-label="清除搜索"
        @click="searchText = ''"
      >
        <IconClose size="xs" />
      </button>
    </label>

    <div class="image-task-filter-strip" aria-label="状态筛选">
      <button
        v-for="item in statusFilterOptions"
        :key="item.value"
        type="button"
        class="image-task-filter-chip"
        :class="{ 'image-task-filter-chip-active': statusFilter === item.value }"
        @click="statusFilter = item.value"
      >
        {{ item.label }}
      </button>
      <button
        class="image-task-filter-refresh"
        type="button"
        :disabled="loading || loadingMore || refreshing"
        aria-label="刷新图片任务"
        title="刷新图片任务"
        @click="$emit('refresh')"
      >
        <IconLoading v-if="refreshing" size="xs" />
        <IconRefresh v-else size="xs" />
      </button>
    </div>

    <div v-if="loading" class="image-task-list-state">
      <div class="image-task-list-state__icon">
        <IconLoading size="2xl" />
      </div>
      <p class="image-task-list-state__text">加载中</p>
    </div>

    <div v-else-if="filteredItems.length === 0" class="image-task-list-state">
      <div class="image-task-list-state__icon">
        <IconEmpty size="2xl" />
      </div>
      <p class="image-task-list-state__text">{{ isFilterActive ? "没有匹配图片" : "暂无图片" }}</p>
      <p v-if="isFilterActive" class="image-task-list-state__hint">调整筛选后再试</p>
    </div>

    <div v-else ref="listRef" class="image-task-list" @scroll.passive="handleScroll">
      <ImageTaskListItem
        v-for="item in filteredItems"
        :key="item.id"
        :item="item"
        :active="item.id === selectedId"
        @select="$emit('select', $event)"
        @delete="$emit('delete', $event)"
      />
      <div v-if="loadingMore || hasMore" class="image-task-list__footer">
        <span ref="loadMoreSentinelRef" class="image-task-list__sentinel" aria-hidden="true"></span>
        <span v-if="loadingMore" class="image-task-list__loading-more">加载中</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * 图片任务列表面板组件。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import IconSearch from "@/components/icons/IconSearch.vue";
import IconClose from "@/components/icons/IconClose.vue";
import IconEmpty from "@/components/icons/IconEmpty.vue";
import IconLoading from "@/components/icons/IconLoading.vue";
import IconRefresh from "@/components/icons/IconRefresh.vue";
import ImageTaskListItem from "./ImageTaskListItem.vue";
import type { ImageTaskListItem as ImageTaskListItemType } from "@/types/image-task-list";
import type { ImageTaskStatusFilter } from "@/types/image-task-list";

const props = defineProps<{
  filteredItems: ImageTaskListItemType[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  selectedId: string;
  refreshing?: boolean;
}>();

const emit = defineEmits<{
  select: [item: ImageTaskListItemType];
  delete: [item: ImageTaskListItemType];
  loadMore: [];
  pageSizeChange: [size: number];
  refresh: [];
}>();

const searchText = defineModel<string>("searchText", { required: true });
const statusFilter = defineModel<ImageTaskStatusFilter>("statusFilter", { required: true });

const isFilterActive = computed(() => searchText.value.trim().length > 0 || statusFilter.value !== "all");

const statusFilterOptions: Array<{ label: string; value: ImageTaskStatusFilter }> = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "active" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" },
];

const panelRef = ref<HTMLElement | null>(null);
const listRef = ref<HTMLElement | null>(null);
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
let intersectionObserver: IntersectionObserver | null = null;
let lastEmittedPageSize = 0;

function emitViewportPageSize() {
  const panel = panelRef.value;
  if (!panel) return;
  const list = listRef.value;
  const styles = window.getComputedStyle(panel);
  const rowGap = Number.parseFloat(styles.rowGap || styles.gap || "12") || 12;
  const searchHeight = panel.querySelector<HTMLElement>(".image-task-search-field")?.offsetHeight ?? 40;
  const filterHeight = panel.querySelector<HTMLElement>(".image-task-filter-strip")?.offsetHeight ?? 34;
  const listItemHeight = panel.querySelector<HTMLElement>(".image-task-list-item")?.offsetHeight ?? 76;
  const listGap = Number.parseFloat(window.getComputedStyle(list ?? panel).rowGap || "8") || 8;
  const availableHeight = list?.clientHeight ?? (panel.clientHeight - searchHeight - filterHeight - rowGap * 2);
  const rowHeight = listItemHeight + listGap;
  const nextPageSize = Math.max(4, Math.floor(availableHeight / rowHeight));
  if (Number.isFinite(nextPageSize) && nextPageSize !== lastEmittedPageSize) {
    lastEmittedPageSize = nextPageSize;
    emit("pageSizeChange", nextPageSize);
  }
}

function handleScroll(event: Event) {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) return;
  const distanceToBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
  if (distanceToBottom <= 96) {
    emit("loadMore");
  }
}

function observeLoadMoreSentinel() {
  intersectionObserver?.disconnect();
  intersectionObserver = null;
  const panel = listRef.value;
  const sentinel = loadMoreSentinelRef.value;
  if (!panel || !sentinel || typeof IntersectionObserver === "undefined") {
    return;
  }
  intersectionObserver = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      if (entry?.isIntersecting && props.hasMore && !props.loading && !props.loadingMore) {
        emit("loadMore");
      }
    },
    {
      root: panel,
      rootMargin: "120px 0px",
      threshold: 0,
    },
  );
  intersectionObserver.observe(sentinel);
}

onMounted(async () => {
  await nextTick();
  emitViewportPageSize();
  observeLoadMoreSentinel();
  if (panelRef.value && typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      emitViewportPageSize();
      observeLoadMoreSentinel();
    });
    resizeObserver.observe(panelRef.value);
  }
});

watch(
  () => [props.filteredItems.length, props.hasMore, props.loading, props.loadingMore],
  async () => {
    await nextTick();
    emitViewportPageSize();
    observeLoadMoreSentinel();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  intersectionObserver?.disconnect();
  intersectionObserver = null;
});

</script>

<style scoped>
.image-task-list-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow: hidden;
  padding: 0 4px 0 0;
}

.image-task-search-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.55);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.image-task-search-field:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(255, 255, 255, 0.8);
}

.image-task-search-field__icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-muted);
  transition: color 180ms ease;
}

.image-task-search-field:focus-within .image-task-search-field__icon {
  color: var(--accent-indigo);
}

.image-task-search-field input {
  width: 100%;
  min-height: 36px;
  border: 0;
  outline: 0;
  box-shadow: none;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.86rem;
}

.image-task-search-field input:focus-visible {
  box-shadow: none;
}

.image-task-search-field input::placeholder {
  color: var(--text-muted);
}

.image-task-search-field__clear {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.image-task-search-field__clear:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.image-task-filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 2px 0;
}

.image-task-filter-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-body);
  font-size: 0.78rem;
  font-weight: 780;
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.image-task-filter-chip:hover,
.image-task-filter-chip:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.26);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.image-task-filter-chip-active {
  border-color: rgba(99, 102, 241, 0.2);
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.96), rgba(224, 231, 255, 0.92));
  color: var(--accent-blue);
  box-shadow: 0 10px 22px rgba(99, 102, 241, 0.08);
}

.image-task-filter-refresh {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin-left: auto;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-body);
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.image-task-filter-refresh:hover:not(:disabled),
.image-task-filter-refresh:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.26);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.image-task-filter-refresh:disabled {
  cursor: wait;
  opacity: 0.68;
}

.image-task-list-state {
  display: grid;
  gap: 12px;
  padding: 40px 20px;
  text-align: center;
  color: var(--text-body);
}

.image-task-list-state__icon {
  display: grid;
  place-items: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #eef2ff;
  color: var(--accent-cyan);
  margin: 0 auto 4px;
}

.image-task-list-state__text {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-strong);
}

.image-task-list-state__hint {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.image-task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.image-task-list::-webkit-scrollbar {
  display: none;
}

.image-task-list__footer {
  display: grid;
  place-items: center;
  min-height: 34px;
  position: relative;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.image-task-list__sentinel {
  position: absolute;
  top: -120px;
  left: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.image-task-list__load-more {
  min-height: 32px;
  padding: 0 14px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.72);
  color: var(--accent-indigo);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
}

.image-task-list__load-more:hover:not(:disabled),
.image-task-list__load-more:focus-visible {
  border-color: rgba(79, 70, 229, 0.26);
  background: #fff;
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.image-task-list__load-more:disabled {
  cursor: wait;
  opacity: 0.72;
}
</style>
