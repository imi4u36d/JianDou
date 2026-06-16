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
      d="M7 4.8h10a2 2 0 0 1 2 2v11.6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6.8a2 2 0 0 1 2-2Z"
    />
    <path
      d="M7 4.8h10a2 2 0 0 1 2 2v11.6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6.8a2 2 0 0 1 2-2Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
    <path d="M8.5 9h7" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" />
    <path d="M8.5 12.4h7" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" />
    <path d="M8.5 15.8h4.6" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" />
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
