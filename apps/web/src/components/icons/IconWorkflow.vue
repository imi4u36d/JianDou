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
      d="M12 2.9c1.2 4.05 3.12 5.96 7.2 7.1-4.08 1.14-6 3.05-7.2 7.1-1.2-4.05-3.12-5.96-7.2-7.1 4.08-1.14 6-3.05 7.2-7.1Z"
    />
    <path
      class="icon__fill"
      d="M18.15 15.15c.55 1.78 1.42 2.65 3.1 3.15-1.68.5-2.55 1.37-3.1 3.15-.55-1.78-1.42-2.65-3.1-3.15 1.68-.5 2.55-1.37 3.1-3.15Z"
    />
    <path
      d="M12 2.9c1.2 4.05 3.12 5.96 7.2 7.1-4.08 1.14-6 3.05-7.2 7.1-1.2-4.05-3.12-5.96-7.2-7.1 4.08-1.14 6-3.05 7.2-7.1Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
    <path
      d="M18.15 15.15c.55 1.78 1.42 2.65 3.1 3.15-1.68.5-2.55 1.37-3.1 3.15-.55-1.78-1.42-2.65-3.1-3.15 1.68-.5 2.55-1.37 3.1-3.15Z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.55"
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
