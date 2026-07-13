import { computed, nextTick, reactive, ref } from "vue";

interface ImagePreviewItem {
  url: string;
  alt: string;
  caption: string;
}

export function useImagePreview() {
  const imagePreviewOverlayRef = ref<{ focus: () => void } | null>(null);
  const imagePreviewTriggerRef = ref<HTMLElement | null>(null);

  const imagePreviewState = reactive({
    open: false,
    url: "",
    alt: "",
    caption: "",
    gallery: [] as ImagePreviewItem[],
    currentIndex: 0,
  });

  const imagePreviewCaption = computed(() => imagePreviewState.caption || imagePreviewState.alt || "图片预览");

  function applyImagePreviewItem(item: ImagePreviewItem, index: number) {
    imagePreviewState.url = item.url;
    imagePreviewState.alt = item.alt;
    imagePreviewState.caption = item.caption;
    imagePreviewState.currentIndex = index;
  }

  function captureImagePreviewTrigger() {
    const active = document.activeElement;
    imagePreviewTriggerRef.value = active instanceof HTMLElement ? active : null;
  }

  function focusImagePreviewOverlay() {
    void nextTick(() => {
      imagePreviewOverlayRef.value?.focus();
    });
  }

  function openImagePreview(url: string, alt: string) {
    if (!url) return;
    captureImagePreviewTrigger();
    const item = { url, alt, caption: alt };
    imagePreviewState.open = true;
    imagePreviewState.gallery = [item];
    applyImagePreviewItem(item, 0);
    focusImagePreviewOverlay();
  }

  function closeImagePreview() {
    imagePreviewTriggerRef.value?.blur();
    imagePreviewTriggerRef.value = null;
    imagePreviewState.open = false;
    imagePreviewState.url = "";
    imagePreviewState.alt = "";
    imagePreviewState.caption = "";
    imagePreviewState.gallery = [];
    imagePreviewState.currentIndex = 0;
  }

  function switchImagePreviewFrame(direction: 1 | -1) {
    if (!imagePreviewState.open || imagePreviewState.gallery.length < 2) return;
    const nextIndex = (imagePreviewState.currentIndex + direction + imagePreviewState.gallery.length) % imagePreviewState.gallery.length;
    applyImagePreviewItem(imagePreviewState.gallery[nextIndex], nextIndex);
  }

  return {
    imagePreviewOverlayRef,
    imagePreviewTriggerRef,
    imagePreviewState,
    imagePreviewCaption,
    openImagePreview,
    closeImagePreview,
    switchImagePreviewFrame,
    captureImagePreviewTrigger,
    focusImagePreviewOverlay,
    applyImagePreviewItem,
  };
}
