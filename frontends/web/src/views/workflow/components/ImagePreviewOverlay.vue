<script setup lang="ts">
import { IconClose } from "@/components/icons";

interface ImagePreviewItem {
  url: string;
  alt: string;
  caption: string;
}

defineProps<{
  open: boolean;
  url: string;
  alt: string;
  caption: string;
  gallery: ImagePreviewItem[];
  currentIndex: number;
  overlayRef: HTMLElement | null;
}>();

const emit = defineEmits<{
  close: [];
  switchFrame: [direction: 1 | -1];
}>();
</script>

<template>
  <div
    v-if="open"
    ref="overlayRef"
    class="image-preview-overlay"
    tabindex="-1"
    role="dialog"
    aria-label="图片预览"
    @keydown.escape.prevent="emit('close')"
    @keydown.left.prevent="emit('switchFrame', -1)"
    @keydown.right.prevent="emit('switchFrame', 1)"
  >
    <button type="button" class="image-preview-close" aria-label="关闭原图预览" @click="emit('close')">
      <IconClose size="sm" />
    </button>
    <img class="image-preview-full" :src="url" :alt="alt" />
  </div>
</template>
