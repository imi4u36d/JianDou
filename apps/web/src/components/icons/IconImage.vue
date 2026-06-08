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
    <rect x="4.5" y="5.5" width="15" height="13" rx="3" stroke="currentColor" stroke-width="1.8" />
    <path d="M8 14.5 10.8 11.7 13.3 14.2 15.3 12.2 18 14.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="10" cy="9.4" r="1.3" stroke="currentColor" stroke-width="1.8" />
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
