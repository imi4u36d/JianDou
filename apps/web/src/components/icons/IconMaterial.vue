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
      d="M4 9.95a2 2 0 0 1 2-2h5.7l1.85 2H18a2 2 0 0 1 2 2v5.45a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9.95Z"
    />
    <path
      d="M4 9.95a2 2 0 0 1 2-2h5.7l1.85 2H18a2 2 0 0 1 2 2v5.45a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9.95Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
    <path
      d="M5 10.2V7.7a2 2 0 0 1 2-2h3.2l1.85 2H17a2 2 0 0 1 2 2v.25"
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
