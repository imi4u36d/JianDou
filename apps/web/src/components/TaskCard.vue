<template>
  <RouterLink :to="`/tasks/${task.id}`" class="rounded-[24px] border border-white/10 bg-white/5 p-5 shadow-panel transition hover:border-orange-300/40 hover:bg-white/10">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-medium text-white">{{ task.title }}</h3>
        <p class="mt-2 text-sm text-slate-300">{{ task.platform }} · {{ task.outputCount }} 条素材</p>
        <p class="mt-1 text-xs text-slate-400">更新时间：{{ new Date(task.updatedAt).toLocaleString() }}</p>
      </div>
      <StatusBadge :status="task.status" />
    </div>
    <div class="mt-4">
      <div class="mb-2 flex justify-between text-xs text-slate-300">
        <span>处理进度</span>
        <span>{{ task.progress }}%</span>
      </div>
      <div class="h-2 rounded-full bg-white/10">
        <div class="h-2 rounded-full bg-gradient-to-r from-orange-400 to-amber-300" :style="{ width: `${task.progress}%` }"></div>
      </div>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import type { TaskListItem } from "@/types";
import StatusBadge from "./StatusBadge.vue";

defineProps<{
  task: TaskListItem;
}>();
</script>
