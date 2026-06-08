<template>
  <component :is="iconComponent" :size="size" :color="color" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { IconName, IconSize } from "./types";
import { iconComponentMap } from "./index";

const props = withDefaults(
  defineProps<{ name: IconName; size?: IconSize; color?: string }>(),
  { size: "lg" },
);

const iconComponent = computed(() => iconComponentMap[props.name]);
</script>
