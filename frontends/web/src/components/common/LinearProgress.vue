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

<style scoped>
.linear-progress {
  overflow: hidden;
  height: 8px;
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) inset;
}

.linear-progress__bar {
  height: 100%;
  border-radius: inherit;
  background: var(--bg-accent);
  transition: width 240ms ease;
}
</style>
