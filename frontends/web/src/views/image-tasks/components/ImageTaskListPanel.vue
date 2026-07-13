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
import { computed } from "vue";
import IconSearch from "@/components/icons/IconSearch.vue";
import IconClose from "@/components/icons/IconClose.vue";
import IconEmpty from "@/components/icons/IconEmpty.vue";
import IconLoading from "@/components/icons/IconLoading.vue";
import IconRefresh from "@/components/icons/IconRefresh.vue";
import ImageTaskListItem from "./ImageTaskListItem.vue";
import { useImageTaskListViewport } from "../composables/useImageTaskListViewport";
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

const { panelRef, listRef, loadMoreSentinelRef, handleScroll } = useImageTaskListViewport({
  itemCount: () => props.filteredItems.length,
  hasMore: () => props.hasMore,
  loading: () => props.loading,
  loadingMore: () => props.loadingMore,
  emitLoadMore: () => emit("loadMore"),
  emitPageSizeChange: (size) => emit("pageSizeChange", size),
});
</script>

<style scoped src="./image-task-list-panel.css"></style>
