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
    <path
      class="icon__fill"
      d="M5.2 10.8 12 5.15l6.8 5.65V19a1.2 1.2 0 0 1-1.2 1.2h-3.45v-4.45a2.15 2.15 0 0 0-4.3 0v4.45H6.4A1.2 1.2 0 0 1 5.2 19v-8.2Z"
    />
    <path
      d="M4.3 10.7 12 4.25l7.7 6.45V19a2 2 0 0 1-2 2h-3.55a1 1 0 0 1-1-1v-4.25a1.15 1.15 0 0 0-2.3 0V20a1 1 0 0 1-1 1H6.3a2 2 0 0 1-2-2v-8.3Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
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
