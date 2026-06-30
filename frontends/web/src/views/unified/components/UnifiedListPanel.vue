<template>
  <aside ref="panelRef" class="unified-list-panel" @scroll.passive="handleScroll">
    <label class="unified-search-field" aria-label="搜索">
      <IconSearch class="unified-search-field__icon" size="sm" aria-hidden="true" />
      <input v-model="searchText" type="search" placeholder="搜索任务" />
      <button
        v-if="searchText"
        class="unified-search-field__clear"
        type="button"
        aria-label="清除搜索"
        @click="searchText = ''"
      >
        <IconClose size="xs" />
      </button>
    </label>

    <div class="unified-filter-strip" aria-label="状态筛选">
      <button
        v-for="item in statusFilterOptions"
        :key="item.value"
        type="button"
        class="unified-filter-chip"
        :class="{ 'unified-filter-chip-active': statusFilter === item.value }"
        @click="statusFilter = item.value"
      >
        {{ item.label }}
      </button>
    </div>

    <div v-if="loading" class="unified-loading">加载中</div>

    <div v-else-if="filteredItems.length === 0" class="unified-empty">
      <h3>{{ isFilterActive ? "没有匹配项" : "暂无任务" }}</h3>
      <p v-if="isFilterActive">调整筛选后再试</p>
      <p v-else>图片任务会在这里显示</p>
    </div>

    <div v-else class="unified-list">
      <UnifiedListItem
        v-for="item in filteredItems"
        :key="item.id"
        :item="item"
        :active="item.id === selectedId"
        @select="$emit('select', $event)"
        @delete="$emit('delete', $event)"
      />
      <div v-if="loadingMore || hasMore" class="unified-list__footer">
        <span ref="loadMoreSentinelRef" class="unified-list__sentinel" aria-hidden="true"></span>
        <span v-if="loadingMore" class="unified-list__loading-more">加载中</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * 统一列表面板组件。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import IconSearch from "@/components/icons/IconSearch.vue";
import IconClose from "@/components/icons/IconClose.vue";
import UnifiedListItem from "./UnifiedListItem.vue";
import type { UnifiedListItem as UnifiedListItemType } from "@/types/unified-task";
import type { UnifiedStatusFilter } from "@/types/unified-task";

const props = defineProps<{
  filteredItems: UnifiedListItemType[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  selectedId: string;
}>();

const emit = defineEmits<{
  select: [item: UnifiedListItemType];
  delete: [item: UnifiedListItemType];
  loadMore: [];
  pageSizeChange: [size: number];
}>();

const searchText = defineModel<string>("searchText", { required: true });
const statusFilter = defineModel<UnifiedStatusFilter>("statusFilter", { required: true });

const isFilterActive = computed(() => searchText.value.trim().length > 0 || statusFilter.value !== "all");

const statusFilterOptions: Array<{ label: string; value: UnifiedStatusFilter }> = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "active" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" },
];

const panelRef = ref<HTMLElement | null>(null);
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
let intersectionObserver: IntersectionObserver | null = null;
let lastEmittedPageSize = 0;

function emitViewportPageSize() {
  const panel = panelRef.value;
  if (!panel) return;
  const styles = window.getComputedStyle(panel);
  const rowGap = Number.parseFloat(styles.rowGap || styles.gap || "12") || 12;
  const searchHeight = panel.querySelector<HTMLElement>(".unified-search-field")?.offsetHeight ?? 40;
  const filterHeight = panel.querySelector<HTMLElement>(".unified-filter-strip")?.offsetHeight ?? 34;
  const listItemHeight = panel.querySelector<HTMLElement>(".unified-list-item")?.offsetHeight ?? 62;
  const listGap = Number.parseFloat(window.getComputedStyle(panel.querySelector<HTMLElement>(".unified-list") ?? panel).rowGap || "4") || 4;
  const availableHeight = panel.clientHeight - searchHeight - filterHeight - rowGap * 2;
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
  const panel = panelRef.value;
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
.unified-list-panel {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
  overflow: auto;
  padding: 0 4px 0 0;
}

.unified-search-field {
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

.unified-search-field:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(255, 255, 255, 0.8);
}

.unified-search-field__icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-muted);
  transition: color 180ms ease;
}

.unified-search-field:focus-within .unified-search-field__icon {
  color: var(--accent-indigo);
}

.unified-search-field input {
  width: 100%;
  min-height: 36px;
  border: 0;
  outline: 0;
  box-shadow: none;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.86rem;
}

.unified-search-field input:focus-visible {
  box-shadow: none;
}

.unified-search-field input::placeholder {
  color: var(--text-muted);
}

.unified-search-field__clear {
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

.unified-search-field__clear:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.unified-filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.unified-filter-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.45);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset;
  color: var(--text-body);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease;
}

.unified-filter-chip:hover:not(.unified-filter-chip-active) {
  background: rgba(255, 255, 255, 0.62);
  border-color: rgba(255, 255, 255, 0.8);
}

.unified-filter-chip-active:hover {
  background: #5558e3;
  border-color: #5558e3;
}

.unified-filter-chip-active {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.25) inset,
    0 2px 8px rgba(99, 102, 241, 0.25);
  color: white;
}

.unified-loading,
.unified-empty {
  display: grid;
  place-items: center;
  min-height: 120px;
  color: var(--text-muted);
  font-size: 0.88rem;
  text-align: center;
}

.unified-empty h3 {
  margin: 0 0 4px;
  font-size: 0.95rem;
  color: var(--text-body);
}

.unified-empty p {
  margin: 0;
  font-size: 0.82rem;
}

.unified-list {
  display: grid;
  gap: 4px;
}

.unified-list__footer {
  display: flex;
  justify-content: center;
  min-height: 40px;
  padding: 8px 0 2px;
  position: relative;
}

.unified-list__sentinel {
  position: absolute;
  top: -120px;
  left: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.unified-list__load-more {
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

.unified-list__load-more:hover:not(:disabled),
.unified-list__load-more:focus-visible {
  border-color: rgba(79, 70, 229, 0.26);
  background: #fff;
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.unified-list__load-more:disabled {
  cursor: wait;
  opacity: 0.72;
}
</style>
