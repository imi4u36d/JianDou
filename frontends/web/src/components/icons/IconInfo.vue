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
    <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
    <path d="M12 16v-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <circle cx="12" cy="8" r="0.5" fill="currentColor" stroke="currentColor" stroke-width="1" />
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
