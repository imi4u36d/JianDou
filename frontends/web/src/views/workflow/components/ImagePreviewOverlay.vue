<template>
  <div
    v-if="open"
    ref="overlayElement"
    class="image-preview-overlay"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    @click.self="$emit('close')"
    @keydown.escape.prevent="$emit('close')"
    @keydown.left.prevent="$emit('switch-frame', -1)"
    @keydown.right.prevent="$emit('switch-frame', 1)"
  >
    <div class="image-preview-caption">
      <strong>{{ caption }}</strong
      ><span v-if="gallerySize > 1">按 ← / → 切换首尾帧</span>
    </div>
    <button type="button" class="image-preview-close" aria-label="关闭原图预览" @click="$emit('close')">
      <IconClose size="sm" />
    </button>
    <div v-if="loadFailed" class="image-preview-fallback">
      <IconEmpty size="lg" /><span>{{ caption }}</span>
    </div>
    <img v-else class="image-preview-full" :src="url" :alt="alt" @error="loadFailed = true" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { IconClose, IconEmpty } from "@/components/icons";

const props = defineProps<{ open: boolean; url: string; alt: string; caption: string; gallerySize: number }>();
defineEmits<{ close: []; "switch-frame": [direction: 1 | -1] }>();

const overlayElement = ref<HTMLElement | null>(null);
const loadFailed = ref(false);
watch(
  () => props.url,
  () => {
    loadFailed.value = false;
  },
);
defineExpose({ focus: () => void nextTick(() => overlayElement.value?.focus()) });
</script>

<style scoped src="./image-preview-overlay.css"></style>
