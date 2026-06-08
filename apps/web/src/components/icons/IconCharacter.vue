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
    <path d="M7.2 7.6a2.8 2.8 0 1 1 5.6 0a2.8 2.8 0 0 1-5.6 0Z" stroke="currentColor" stroke-width="1.8" />
    <path d="M4.8 17.2c.8-2.4 2.7-3.6 5.2-3.6s4.4 1.2 5.2 3.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <path d="M17.6 6.7v10.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <path d="M17.6 6.7c1 0 1.8.8 1.8 1.8s-.8 1.8-1.8 1.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
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
