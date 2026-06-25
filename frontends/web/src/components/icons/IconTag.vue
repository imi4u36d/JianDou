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
    <path d="M12.59 2.59a2 2 0 0 1 2.82 0L21 8.17a2 2 0 0 1 0 2.83l-8.59 8.59a2 2 0 0 1-2.82 0L3 13a2 2 0 0 1 0-2.83Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
    <circle cx="7.5" cy="7.5" r="1.5" fill="currentColor" />
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
