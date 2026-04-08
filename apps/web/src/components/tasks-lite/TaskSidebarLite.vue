<template>
  <aside class="surface-panel sidebar-shell p-4 md:p-5">
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">任务管理</p>
      <h2 class="text-2xl font-semibold tracking-[-0.02em] text-slate-900">查询表单</h2>
    </div>

    <div class="mt-5 grid gap-3">
      <label class="grid gap-2 text-sm text-slate-700">
        查询任务
        <input
          :value="keyword"
          class="field-input"
          placeholder="搜索任务标题 / ID"
          type="search"
          @input="emit('update:keyword', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label class="grid gap-2 text-sm text-slate-700">
        状态筛选
        <select
          :value="status"
          class="field-select"
          @change="emit('update:status', ($event.target as HTMLSelectElement).value as TaskStatus | 'all')"
        >
          <option value="all">全部状态</option>
          <option value="PENDING">排队中</option>
          <option value="ANALYZING">分析中</option>
          <option value="PLANNING">规划中</option>
          <option value="RENDERING">渲染中</option>
          <option value="COMPLETED">已完成</option>
          <option value="FAILED">失败</option>
        </select>
      </label>
      <label class="grid gap-2 text-sm text-slate-700">
        平台筛选
        <select
          :value="platform"
          class="field-select"
          @change="emit('update:platform', ($event.target as HTMLSelectElement).value)"
        >
          <option value="all">全部平台</option>
          <option v-for="item in platformOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn-primary" type="button" @click="emit('refresh')">刷新任务</button>
    </div>

    <div class="metrics-grid mt-4">
      <div class="surface-tile p-3">
        <p class="text-xs text-slate-500">总任务</p>
        <p class="mt-1 text-xl font-semibold text-slate-900">{{ metrics.total }}</p>
      </div>
      <div class="surface-tile p-3">
        <p class="text-xs text-slate-500">进行中</p>
        <p class="mt-1 text-xl font-semibold text-slate-900">{{ metrics.running }}</p>
      </div>
      <div class="surface-tile p-3">
        <p class="text-xs text-slate-500">已完成</p>
        <p class="mt-1 text-xl font-semibold text-slate-900">{{ metrics.completed }}</p>
      </div>
      <div class="surface-tile p-3">
        <p class="text-xs text-slate-500">失败</p>
        <p class="mt-1 text-xl font-semibold text-slate-900">{{ metrics.failed }}</p>
      </div>
    </div>

    <div class="mt-4 rounded-2xl border border-slate-200/70 bg-white/70 p-4 text-sm text-slate-600">
      <p class="font-medium text-slate-800">当前结果</p>
      <p class="mt-2">{{ loading ? "正在刷新任务..." : `命中 ${resultCount} 条任务` }}</p>
      <p class="mt-1 text-xs text-slate-500">右侧默认展示全部任务卡片，点击卡片后在当前页展开详情。</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { TaskStatus } from "@/types";

interface TaskMetrics {
  total: number;
  running: number;
  completed: number;
  failed: number;
}

defineProps<{
  keyword: string;
  status: TaskStatus | "all";
  platform: string | "all";
  platformOptions: string[];
  loading: boolean;
  metrics: TaskMetrics;
  resultCount: number;
}>();

const emit = defineEmits<{
  (event: "update:keyword", value: string): void;
  (event: "update:status", value: TaskStatus | "all"): void;
  (event: "update:platform", value: string | "all"): void;
  (event: "refresh"): void;
}>();
</script>

<style scoped>
.sidebar-shell {
  height: min(100%, calc(100vh - 9rem));
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}
</style>
