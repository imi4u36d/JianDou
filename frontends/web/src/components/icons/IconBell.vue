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
    <path d="M15 17H9a2 2 0 0 1-2-2v-3.2c0-1.5-.4-2.9-1.2-4.2A5.9 5.9 0 0 1 11 4h2a5.9 5.9 0 0 1 5.2 3.6c.5 1 .8 2.1.8 3.2V15a2 2 0 0 1-2 2Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M10 20a2.5 2.5 0 0 0 4 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
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
