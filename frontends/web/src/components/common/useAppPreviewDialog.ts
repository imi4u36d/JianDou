import { computed, nextTick, ref, watch } from "vue";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, type DownloadMediaKind } from "@/utils/download";

export interface AppPreviewDialogProps {
  open: boolean;
  kind: "storyboard" | "image" | "video";
  title: string;
  subtitle?: string;
  html?: string;
  url?: string;
  imageLoadFailed?: boolean;
  showDownload?: boolean;
  wide?: boolean;
  showNavigation?: boolean;
  canPrevious?: boolean;
  canNext?: boolean;
}

interface PreviewDialogEmit {
  (event: "close"): void;
  (event: "imageError"): void;
  (event: "previous"): void;
  (event: "next"): void;
}

export function useAppPreviewDialog(props: Readonly<AppPreviewDialogProps>, emit: PreviewDialogEmit) {
  const overlayRef = ref<HTMLElement | null>(null);
  const mediaLoadState = ref<"idle" | "loading" | "ready">("idle");
  const touchStart = ref<{ x: number; y: number } | null>(null);
  const hasPreviewMedia = computed(() =>
    props.open && Boolean(props.url) && (props.kind === "image" || props.kind === "video"),
  );
  const mediaLoading = computed(() => hasPreviewMedia.value && mediaLoadState.value === "loading");
  const downloadUrl = computed(() => props.showDownload ? String(props.url ?? "").trim() : "");
  const downloadMediaKind = computed<DownloadMediaKind>(() =>
    props.kind === "image" || props.kind === "video" ? props.kind : "file",
  );
  const widePanel = computed(() => props.wide ?? (props.kind === "image" || props.kind === "video"));

  function markMediaLoading() {
    if (hasPreviewMedia.value) mediaLoadState.value = "loading";
  }

  function markMediaReady() {
    if (hasPreviewMedia.value) mediaLoadState.value = "ready";
  }

  function handleImageError() {
    mediaLoadState.value = "ready";
    emit("imageError");
  }

  async function handleDownload() {
    try {
      const result = await downloadMedia({
        url: downloadUrl.value,
        title: props.title,
        mediaType: downloadMediaKind.value,
      });
      if (result.target === "album") messageApi.success("已保存到相册");
      else if (result.target === "share") messageApi.info("已打开系统分享，可保存到相册");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  function handlePrevious() {
    if (props.showNavigation && props.canPrevious) emit("previous");
  }

  function handleNext() {
    if (props.showNavigation && props.canNext) emit("next");
  }

  function handleTouchStart(event: TouchEvent) {
    const touch = event.touches[0];
    if (touch) touchStart.value = { x: touch.clientX, y: touch.clientY };
  }

  function handleTouchEnd(event: TouchEvent) {
    const start = touchStart.value;
    const touch = event.changedTouches[0];
    touchStart.value = null;
    if (!start || !touch || !props.showNavigation) return;
    const deltaX = touch.clientX - start.x;
    const deltaY = touch.clientY - start.y;
    if (Math.abs(deltaX) < 56 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;
    if (deltaX > 0) handlePrevious();
    else handleNext();
  }

  watch(
    () => [props.open, props.kind, props.url],
    () => { mediaLoadState.value = hasPreviewMedia.value ? "loading" : "idle"; },
    { immediate: true },
  );
  watch(() => props.open, async (open) => {
    if (!open) return;
    await nextTick();
    overlayRef.value?.focus({ preventScroll: true });
  });

  return {
    overlayRef,
    mediaLoading,
    downloadUrl,
    widePanel,
    markMediaLoading,
    markMediaReady,
    handleImageError,
    handleDownload,
    handlePrevious,
    handleNext,
    handleTouchStart,
    handleTouchEnd,
  };
}
