<template>
  <div :class="containerClass" class="rounded-2xl border p-4 transition duration-200">
    <div class="flex items-start justify-between gap-3">
      <div>
        <span class="text-sm font-semibold text-slate-900">{{ label }}</span>
        <p class="mt-1 text-xs leading-5 text-slate-600">{{ description }}</p>
      </div>
      <span :class="stateClass" class="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]">
        {{ stateLabel }}
      </span>
    </div>
    <div class="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-200">
      <div :class="barClass" class="h-full rounded-full transition-all duration-300" :style="{ width: barWidth }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 时间线组件。
 */
import { computed } from "vue";

const props = defineProps<{
  label: string;
  description?: string;
  state: "done" | "current" | "pending";
}>();

const stateLabel = computed(() => {
  switch (props.state) {
    case "done":
      return "完成";
    case "current":
      return "进行中";
    default:
      return "待机";
  }
});

const barWidth = computed(() => {
  switch (props.state) {
    case "done":
      return "100%";
    case "current":
      return "66%";
    default:
      return "0%";
  }
});

const containerClass = computed(() => {
  switch (props.state) {
    case "done":
      return "border-emerald-300 bg-emerald-50/50";
    case "current":
      return "border-cyan-300 bg-cyan-50/50";
    default:
      return "border-slate-200 bg-slate-50/70";
  }
});

const stateClass = computed(() => {
  switch (props.state) {
    case "done":
      return "bg-emerald-100 text-emerald-800";
    case "current":
      return "bg-cyan-100 text-cyan-800";
    default:
      return "bg-slate-200 text-slate-700";
  }
});

const barClass = computed(() => {
  switch (props.state) {
    case "done":
      return "bg-gradient-to-r from-emerald-500 to-emerald-400";
    case "current":
      return "bg-gradient-to-r from-cyan-500 to-sky-500";
    default:
      return "bg-slate-300";
  }
});

</script>
