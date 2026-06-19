<template>
  <span class="status-pill" :data-tone="tone">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
/**
 * 状态Pill组件。
 */
defineProps<{
  label: string;
  tone?: "neutral" | "info" | "warning" | "success" | "danger";
}>();

</script>
