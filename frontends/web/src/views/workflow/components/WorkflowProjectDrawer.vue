<template>
  <aside ref="drawerRef" class="workflow-project-drawer">
    <label class="workflow-search-box">
      <IconSearch class="workflow-search-box__icon" size="sm" aria-hidden="true" />
      <input
        :value="search"
        type="search"
        placeholder="搜索视频"
        @input="emit('update:search', ($event.target as HTMLInputElement).value)"
      />
      <button
        v-if="search"
        class="workflow-search-box__clear"
        type="button"
        aria-label="清除搜索"
        @click="emit('update:search', '')"
      >
        <IconClose size="xs" />
      </button>
    </label>

    <div class="workflow-filter-strip" aria-label="视频筛选">
      <button
        v-for="item in filterOptions"
        :key="item.value"
        type="button"
        class="workflow-filter-chip"
        :class="{ 'workflow-filter-chip-active': filter === item.value }"
        @click="emit('update:filter', item.value)"
      >
        {{ item.label }}
      </button>
      <button
        class="workflow-filter-refresh"
        type="button"
        :disabled="loading || loadingMore || refreshing"
        aria-label="刷新视频任务"
        title="刷新视频任务"
        @click="emit('refresh')"
      >
        <IconLoading v-if="refreshing" size="xs" />
        <IconRefresh v-else size="xs" />
      </button>
    </div>

    <div v-if="loading" class="workflow-empty-state">
      <div class="workflow-empty-state__icon"><IconLoading size="2xl" /></div>
      <p class="workflow-empty-state__text">加载中</p>
    </div>

    <div v-else-if="!filteredWorkflows.length" class="workflow-empty-state">
      <div class="workflow-empty-state__icon"><IconEmpty size="2xl" /></div>
      <p class="workflow-empty-state__text">
        {{ workflows.length ? "没有匹配视频" : "暂无视频" }}
      </p>
      <p v-if="workflows.length" class="workflow-empty-state__hint">调整筛选后再试</p>
    </div>

    <div v-else ref="listRef" class="workflow-project-list" @scroll.passive="handleScroll">
      <article
        v-for="item in filteredWorkflows"
        :key="item.id"
        class="workflow-nav-item"
        :class="{ 'workflow-nav-item-active': item.id === selectedWorkflowId }"
      >
        <button
          type="button"
          class="workflow-nav-item__main"
          :aria-label="`打开视频 ${item.title}`"
          @click="emit('open', item.id, workflowSummaryCanvasStage(item))"
        >
          <span class="workflow-nav-item__thumb" aria-hidden="true"><IconVideo size="sm" /></span>
          <span class="workflow-nav-item__body">
            <span class="workflow-nav-item__title-row">
              <span class="workflow-nav-item__title" :title="item.title">{{ item.title }}</span>
              <span
                class="workflow-nav-item__status"
                :class="`workflow-nav-item__status-${workflowNavStatusTone(item)}`"
              >
                {{ workflowNavStatusLabel(item) }}
              </span>
            </span>
            <span class="workflow-nav-item__meta">
              <span>{{ workflowStageLabel(item.currentStage) }}</span>
              <span>{{ item.aspectRatio || "未设置" }}</span>
              <time :datetime="item.updatedAt || item.createdAt || undefined">
                {{ workflowNavUpdatedLabel(item.updatedAt || item.createdAt) }}
              </time>
            </span>
            <span class="workflow-nav-item__progress" aria-hidden="true">
              <i :style="{ width: `${completionPercentage(item)}%` }"></i>
            </span>
          </span>
        </button>
        <span class="workflow-nav-item__side">
          <button
            type="button"
            class="workflow-nav-item__delete"
            aria-label="删除任务"
            title="删除"
            :disabled="busyActionKey === `delete-workflow-${item.id}`"
            @click.stop="emit('delete', item)"
          >
            <IconLoading v-if="busyActionKey === `delete-workflow-${item.id}`" size="xs" />
            <IconDelete v-else size="xs" />
          </button>
        </span>
      </article>
      <div v-if="loadingMore || hasMore" class="workflow-project-list__footer">
        <span ref="sentinelRef" class="workflow-project-list__sentinel" aria-hidden="true"></span>
        <span v-if="loadingMore" class="workflow-project-list__loading">加载中</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { WorkflowSummary } from "@/types";
import { workflowStageLabel, workflowSummaryCanvasStage } from "@/features/workflows/summary";
import {
  workflowNavStatusLabel,
  workflowNavStatusTone,
  workflowNavUpdatedLabel,
} from "@/features/workflows/stage-workflow-presenters";
import { IconClose, IconDelete, IconEmpty, IconLoading, IconRefresh, IconSearch, IconVideo } from "@/components/icons";

type WorkflowFilter = "all" | "active" | "ready" | "done";

const props = defineProps<{
  search: string;
  filter: WorkflowFilter;
  workflows: WorkflowSummary[];
  filteredWorkflows: WorkflowSummary[];
  selectedWorkflowId: string;
  loading: boolean;
  loadingMore: boolean;
  refreshing: boolean;
  hasMore: boolean;
  busyActionKey: string;
  completionPercentage: (workflow: WorkflowSummary) => number;
}>();

const emit = defineEmits<{
  "update:search": [value: string];
  "update:filter": [value: WorkflowFilter];
  refresh: [];
  open: [workflowId: string, preferredStage: string];
  delete: [workflow: WorkflowSummary];
  "load-more": [];
  "page-size": [value: number];
}>();

const filterOptions = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "active" },
  { label: "可继续", value: "ready" },
  { label: "已完成", value: "done" },
] as const;

const drawerRef = ref<HTMLElement | null>(null);
const listRef = ref<HTMLElement | null>(null);
const sentinelRef = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
let intersectionObserver: IntersectionObserver | null = null;
let lastPageSize = 0;

function emitViewportPageSize() {
  const list = listRef.value;
  const drawer = drawerRef.value;
  if (!list && !drawer) return;
  const item = list?.querySelector<HTMLElement>(".workflow-nav-item");
  const searchHeight = drawer?.querySelector<HTMLElement>(".workflow-search-box")?.offsetHeight ?? 40;
  const filterHeight = drawer?.querySelector<HTMLElement>(".workflow-filter-strip")?.offsetHeight ?? 40;
  const styles = window.getComputedStyle(list ?? drawer!);
  const gap = Number.parseFloat(styles.rowGap || styles.gap || "10") || 10;
  const itemHeight = item?.offsetHeight || 86;
  const availableHeight =
    list?.clientHeight ??
    Math.max(0, (drawer?.clientHeight ?? window.innerHeight) - searchHeight - filterHeight - gap * 3);
  const nextPageSize = Math.max(4, Math.floor(availableHeight / (itemHeight + gap)));
  if (Number.isFinite(nextPageSize) && nextPageSize !== lastPageSize) {
    lastPageSize = nextPageSize;
    emit("page-size", nextPageSize);
  }
}

function handleScroll(event: Event) {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) return;
  if (target.scrollHeight - target.scrollTop - target.clientHeight <= 96) emit("load-more");
}

function observeLoadMoreSentinel() {
  intersectionObserver?.disconnect();
  intersectionObserver = null;
  if (!listRef.value || !sentinelRef.value || typeof IntersectionObserver === "undefined") return;
  intersectionObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry?.isIntersecting && props.hasMore && !props.loading && !props.loadingMore) emit("load-more");
    },
    { root: listRef.value, rootMargin: "120px 0px", threshold: 0 },
  );
  intersectionObserver.observe(sentinelRef.value);
}

watch(
  () => [props.filteredWorkflows.length, props.hasMore, props.loading, props.loadingMore],
  async () => {
    await nextTick();
    emitViewportPageSize();
    observeLoadMoreSentinel();
  },
  { flush: "post" },
);

onMounted(async () => {
  await nextTick();
  emitViewportPageSize();
  observeLoadMoreSentinel();
  const resizeTarget = drawerRef.value ?? listRef.value;
  if (resizeTarget && typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      emitViewportPageSize();
      observeLoadMoreSentinel();
    });
    resizeObserver.observe(resizeTarget);
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  intersectionObserver?.disconnect();
});
</script>

<style scoped src="./workflow-project-drawer.css"></style>
