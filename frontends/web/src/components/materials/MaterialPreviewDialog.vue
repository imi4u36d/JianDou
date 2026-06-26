<template>
  <AppPreviewDialog
    :open="open"
    :kind="kind"
    :title="title"
    :html="html"
    :url="url"
    :image-load-failed="imageLoadFailed"
    :show-download="showDownload"
    :wide="wide"
    @close="emit('close')"
    @image-error="emit('imageError')"
  >
    <template v-if="$slots.actions" #actions>
      <slot name="actions"></slot>
    </template>
    <template v-if="$slots.default" #default>
      <slot></slot>
    </template>
  </AppPreviewDialog>
</template>

<script setup lang="ts">
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";

withDefaults(defineProps<{
  open: boolean;
  kind: "storyboard" | "image" | "video";
  title: string;
  html?: string;
  url?: string;
  imageLoadFailed?: boolean;
  showDownload?: boolean;
  wide?: boolean;
}>(), {
  html: "",
  url: "",
  imageLoadFailed: false,
  showDownload: true,
});

const emit = defineEmits<{
  close: [];
  imageError: [];
}>();
</script>
