<template>
  <span class="status-pill" :data-tone="tone">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  tone?: "neutral" | "info" | "warning" | "success" | "danger";
}>();
</script>
