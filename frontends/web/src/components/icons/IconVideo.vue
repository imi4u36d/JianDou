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
    <rect x="4.5" y="5.5" width="10" height="13" rx="3" stroke="currentColor" stroke-width="1.8" />
    <path d="m14.5 10 4.5-2.8v9.6L14.5 14" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
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
