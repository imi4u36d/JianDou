<template>
  <svg :width="sizePx" :height="sizePx" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4 12v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <path d="M12 15V4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <path d="m7.5 8.5 4.5-4.5 4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconSizeMap, type IconSize } from "./types";

const props = withDefaults(defineProps<{ size?: IconSize }>(), { size: "md" });
const sizePx = computed(() => iconSizeMap[props.size]);
</script>
