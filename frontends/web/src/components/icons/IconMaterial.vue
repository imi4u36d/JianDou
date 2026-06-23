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
    <!-- Filled folder body (visible on active state) -->
    <path
      class="icon__fill"
      d="M4 9.95a2 2 0 0 1 2-2h5.7l1.85 2H18a2 2 0 0 1 2 2v5.45a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9.95Z"
    />
    <!-- Folder body outline with tab -->
    <path
      d="M4 9.95a2 2 0 0 1 2-2h5.7l1.85 2H18a2 2 0 0 1 2 2v5.45a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9.95Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linejoin="round"
    />
    <!-- Back tab edge -->
    <path
      d="M5 10.2V7.7a2 2 0 0 1 2-2h3.2l1.85 2H17a2 2 0 0 1 2 2v.25"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linejoin="round"
    />
    <!-- Image icon inside: frame -->
    <rect
      class="icon__detail"
      x="8.5"
      y="11.8"
      width="7"
      height="5"
      rx="1"
      fill="none"
      stroke="currentColor"
      stroke-width="1.25"
    />
    <!-- Sun dot -->
    <circle class="icon__detail" cx="10.5" cy="13.3" r="0.7" fill="currentColor" />
    <!-- Mountain landscape -->
    <path
      class="icon__detail"
      d="M8.5 16.2l2.5-2.5 1.3 1.3L14 13.3l1.5 1.7"
      fill="none"
      stroke="currentColor"
      stroke-width="1.25"
      stroke-linecap="round"
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

<style scoped>
.icon :deep(.icon__detail) {
  transition: stroke 180ms ease, fill 180ms ease;
}
</style>
