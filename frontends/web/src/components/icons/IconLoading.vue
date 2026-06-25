<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    :width="sizeNum"
    :height="sizeNum"
    fill="none"
    aria-hidden="true"
    class="icon icon--spin"
  >
    <path d="M12 2v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <path d="M12 18v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.3" />
    <path d="M4.93 4.93l2.83 2.83" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.9" />
    <path d="M16.24 16.24l2.83 2.83" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.3" />
    <path d="M2 12h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.7" />
    <path d="M18 12h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.3" />
    <path d="M4.93 19.07l2.83-2.83" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.5" />
    <path d="M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" opacity="0.3" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconSizeMap, type IconSize } from "./types";

const props = withDefaults(
  defineProps<{ size?: IconSize; color?: string }>(),
  { size: "lg", color: "currentColor" },
);

const sizeNum = computed(() => iconSizeMap[props.size]);
</script>

<style scoped>
.icon--spin {
  animation: icon-spin 0.8s linear infinite;
}

@keyframes icon-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
