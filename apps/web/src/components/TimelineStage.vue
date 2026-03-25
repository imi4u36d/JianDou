<template>
  <div class="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-white">{{ label }}</span>
      <span class="text-xs text-slate-400">{{ active ? "处理中" : "待机" }}</span>
    </div>
    <div class="mt-3 h-2 rounded-full bg-white/10">
      <div class="h-2 rounded-full bg-orange-400 transition-all" :style="{ width: active ? '100%' : '0%' }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  active: boolean;
}>();
</script>

