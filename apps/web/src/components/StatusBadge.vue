<template>
  <span :class="badgeClass" class="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-[0.18em]">
    <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
    <span>{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { TaskStatus } from "@/types";
import { formatTaskStatus } from "@/utils/task";

const props = defineProps<{
  status: TaskStatus;
}>();

const label = computed(() => formatTaskStatus(props.status));

const badgeClass = computed(() => {
  switch (props.status) {
    case "COMPLETED":
      return "border-emerald-300 bg-emerald-50 text-emerald-800";
    case "FAILED":
      return "border-rose-300 bg-rose-50 text-rose-800";
    case "RENDERING":
      return "border-amber-300 bg-amber-50 text-amber-800";
    case "PLANNING":
      return "border-cyan-300 bg-cyan-50 text-cyan-800";
    case "ANALYZING":
      return "border-sky-300 bg-sky-50 text-sky-800";
    case "PAUSED":
      return "border-amber-300 bg-amber-50 text-amber-800";
    default:
      return "border-slate-300 bg-slate-100 text-slate-700";
  }
});
</script>
