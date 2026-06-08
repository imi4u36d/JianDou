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
    <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="1.8" />
    <path d="M3 9h18" stroke="currentColor" stroke-width="1.8" />
    <path d="M8 5v-2M16 5v-2M8 19v2M16 19v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
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
