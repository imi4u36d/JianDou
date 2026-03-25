<template>
  <span :class="badgeClass" class="inline-flex rounded-full px-3 py-1 text-xs font-medium">
    {{ label }}
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
      return "bg-emerald-500/20 text-emerald-200";
    case "FAILED":
      return "bg-rose-500/20 text-rose-200";
    case "RENDERING":
      return "bg-orange-500/20 text-orange-100";
    default:
      return "bg-slate-500/20 text-slate-200";
  }
});
</script>
