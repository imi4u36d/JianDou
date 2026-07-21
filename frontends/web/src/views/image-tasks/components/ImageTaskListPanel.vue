<template>
  <aside ref="panelRef" class="image-task-list-panel">
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
      <p class="image-task-list-state__text">{{ filterActive ? "没有匹配图片" : "暂无图片" }}</p>
      <p v-if="filterActive" class="image-task-list-state__hint">调整筛选后再试</p>
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
import IconEmpty from "@/components/icons/IconEmpty.vue";
import IconLoading from "@/components/icons/IconLoading.vue";
import ImageTaskListItem from "./ImageTaskListItem.vue";
import { useImageTaskListViewport } from "../composables/useImageTaskListViewport";
import type { ImageTaskListItem as ImageTaskListItemType } from "@/types/image-task-list";

const props = defineProps<{
  filteredItems: ImageTaskListItemType[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  selectedId: string;
  filterActive: boolean;
}>();

const emit = defineEmits<{
  select: [item: ImageTaskListItemType];
  delete: [item: ImageTaskListItemType];
  loadMore: [];
  pageSizeChange: [size: number];
}>();

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
