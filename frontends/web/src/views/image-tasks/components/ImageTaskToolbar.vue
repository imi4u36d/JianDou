<template>
  <div class="image-task-toolbar">
    <label class="image-task-search-field" aria-label="搜索图片任务">
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
    </div>

    <label class="image-task-status-select">
      <span>状态筛选</span>
      <select v-model="statusFilter" aria-label="状态筛选">
        <option v-for="item in statusFilterOptions" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </label>

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
</template>

<script setup lang="ts">
import IconClose from "@/components/icons/IconClose.vue";
import IconLoading from "@/components/icons/IconLoading.vue";
import IconRefresh from "@/components/icons/IconRefresh.vue";
import IconSearch from "@/components/icons/IconSearch.vue";
import type { ImageTaskStatusFilter } from "@/types/image-task-list";

defineProps<{
  loading: boolean;
  loadingMore: boolean;
  refreshing: boolean;
}>();

defineEmits<{ refresh: [] }>();

const searchText = defineModel<string>("searchText", { required: true });
const statusFilter = defineModel<ImageTaskStatusFilter>("statusFilter", { required: true });

const statusFilterOptions: Array<{ label: string; value: ImageTaskStatusFilter }> = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "active" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" },
];
</script>

<style scoped src="./image-task-toolbar.css"></style>
