<template>
  <section class="missing-clips">
    <div class="missing-clips__head">
      <strong>待补齐镜头</strong><span>{{ hint }}</span>
    </div>
    <div class="missing-clips__list">
      <button v-for="slot in clips" :key="slot.clipIndex" type="button" @click="$emit('open', slot.clipIndex)">
        {{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { WorkflowClipSlot } from "@/types";

defineProps<{ clips: WorkflowClipSlot[]; hint: string }>();
defineEmits<{ open: [clipIndex: number] }>();
</script>

<style scoped>
.missing-clips {
  display: grid;
  gap: 10px;
}
.missing-clips__head {
  display: grid;
  gap: 4px;
}
.missing-clips__head span {
  color: var(--text-muted);
  font-size: 0.78rem;
}
.missing-clips__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.missing-clips__list button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 999px;
  background: #f8fafb;
  cursor: pointer;
}
</style>
