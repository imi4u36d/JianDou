<template>
  <svg :width="sizePx" :height="sizePx" viewBox="0 0 24 24" :fill="filled ? 'currentColor' : 'none'" aria-hidden="true">
    <path
      d="M20.3 5.9c-1.7-2-4.7-2.2-6.7-.4L12 7l-1.6-1.5c-2-1.8-5-1.6-6.7.4-1.8 2.1-1.5 5.2.6 7.1l6.5 5.9a1.8 1.8 0 0 0 2.4 0l6.5-5.9c2.1-1.9 2.4-5 .6-7.1Z"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconSizeMap, type IconSize } from "./types";

const props = withDefaults(defineProps<{ size?: IconSize; filled?: boolean }>(), { size: "md", filled: false });
const sizePx = computed(() => iconSizeMap[props.size]);
</script>
