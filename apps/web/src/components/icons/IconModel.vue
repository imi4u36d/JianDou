<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    :width="sizeNum"
    :height="sizeNum"
    fill="none"
    aria-hidden="true"
    class="icon"
  >
    <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="1.8" />
    <path d="M9 9h6v6H9Z" stroke="currentColor" stroke-width="1.8" />
    <path d="M12 4v2M12 18v2M4 12h2M18 12h2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconSizeMap, type IconSize } from "./types";

const props = withDefaults(
  defineProps<{ size?: IconSize; color?: string }>(),
  { size: "lg" },
);

const sizeNum = computed(() => iconSizeMap[props.size]);
</script>
