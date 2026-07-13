<template>
  <div v-if="open" class="dialog-overlay" role="dialog" aria-modal="true" tabindex="-1" @click.self="$emit('close')">
    <div class="dialog-card">
      <div class="dialog-head">
        <h4>{{ title }}</h4>
        <button type="button" aria-label="关闭角色定义弹窗" @click="$emit('close')"><IconClose size="sm" /></button>
      </div>
      <p>{{ content }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { IconClose } from "@/components/icons";
defineProps<{ open: boolean; title: string; content: string }>();
defineEmits<{ close: [] }>();
</script>

<style scoped src="./character-summary-dialog.css"></style>
