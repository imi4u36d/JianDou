<template>
  <div class="linear-progress">
    <div class="linear-progress__bar" :style="{ width: `${clampedValue}%` }"></div>
  </div>
</template>

<script setup lang="ts">
/**
 * Linear组件。
 */
import { computed } from "vue";

const props = defineProps<{
  value: number;
}>();

const clampedValue = computed(() => Math.max(0, Math.min(100, Math.round(props.value))));

</script>
