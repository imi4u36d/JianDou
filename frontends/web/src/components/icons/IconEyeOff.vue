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
    <path d="M4.5 4.5 19.5 19.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <path
      d="M9.6 6.9c.7-.1 1.5-.2 2.4-.2 3.8 0 6.7 1.8 8.6 5.3-.7 1.3-1.6 2.4-2.6 3.2"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path
      d="M14.1 16.9c-.7.3-1.4.4-2.1.4-3.8 0-6.7-1.8-8.6-5.3.8-1.5 1.8-2.7 3.1-3.5"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path d="M10.2 10.2a2.7 2.7 0 0 0 3.6 3.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconSizeMap, type IconSize } from "./types";

const props = withDefaults(
  defineProps<{ size?: IconSize }>(),
  { size: "lg", color: "currentColor" },
);

const sizeNum = computed(() => iconSizeMap[props.size]);
</script>
