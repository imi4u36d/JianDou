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
    <!-- Filled clipboard body (visible on active state) -->
    <path
      class="icon__fill"
      d="M6 5.5h12a1.5 1.5 0 0 1 1.5 1.5v12.5A1.5 1.5 0 0 1 18 21H6a1.5 1.5 0 0 1-1.5-1.5V7A1.5 1.5 0 0 1 6 5.5Z"
    />
    <!-- Clipboard body outline -->
    <path
      d="M6 5.5h12a1.5 1.5 0 0 1 1.5 1.5v12.5A1.5 1.5 0 0 1 18 21H6a1.5 1.5 0 0 1-1.5-1.5V7A1.5 1.5 0 0 1 6 5.5Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linejoin="round"
    />
    <!-- Clipboard clip tab -->
    <path
      d="M9 5.5V4.5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <!-- Check 1 --><path class="icon__detail" d="M7.5 10.5l1.2 1.2 2.3-2.4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    <!-- Line 1 --><path class="icon__detail" d="M13 10h3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    <!-- Check 2 --><path class="icon__detail" d="M7.5 14l1.2 1.2 2.3-2.4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    <!-- Line 2 --><path class="icon__detail" d="M13 13.5h3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    <!-- Check 3 --><path class="icon__detail" d="M7.5 17.5l1.2 1.2 2.3-2.4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    <!-- Line 3 --><path class="icon__detail" d="M13 17h2.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
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
  transition: stroke 180ms ease;
}
</style>
