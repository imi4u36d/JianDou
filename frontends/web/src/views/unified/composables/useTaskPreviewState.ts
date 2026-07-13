import { computed, reactive, ref, watch, type Ref } from "vue";
import type { TaskPreviewMedia } from "@/utils/task-preview";

const IMAGE_URL = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
const VIDEO_URL = /\.(m4v|mov|mp4|ogg|webm)(?:[?#].*)?$/i;

export function previewKindForUrl(url: string): "image" | "video" | "storyboard" {
  if (VIDEO_URL.test(url)) return "video";
  if (IMAGE_URL.test(url)) return "image";
  return "image";
}

export function useTaskPreviewState(selectedMedia: Ref<TaskPreviewMedia | null>) {
  const previewImageLoadFailed = ref(false);
  const taskPreviewLoadState = ref<"idle" | "loading" | "ready" | "failed">("idle");
  const taskPreviewMediaItems = computed(() => (selectedMedia.value ? [selectedMedia.value] : []));
  const taskPreviewMediaUrl = computed(() => selectedMedia.value?.url || "");
  const taskPreviewIsLoading = computed(
    () => Boolean(taskPreviewMediaUrl.value) && taskPreviewLoadState.value === "loading",
  );
  const previewDialog = reactive({
    open: false,
    kind: "image" as "storyboard" | "image" | "video",
    title: "",
    url: "",
  });

  function openTaskPreviewItem(title: string, url: string) {
    previewImageLoadFailed.value = false;
    Object.assign(previewDialog, { kind: previewKindForUrl(url), title, url, open: true });
  }

  function closeTaskPreviewDialog() {
    Object.assign(previewDialog, { open: false, title: "", url: "" });
    previewImageLoadFailed.value = false;
  }

  function setLoadState(state: "loading" | "ready" | "failed") {
    if (taskPreviewMediaUrl.value) taskPreviewLoadState.value = state;
  }

  watch(
    taskPreviewMediaUrl,
    (url) => {
      taskPreviewLoadState.value = url ? "loading" : "idle";
    },
    { immediate: true },
  );

  return {
    closeTaskPreviewDialog,
    markTaskPreviewFailed: () => setLoadState("failed"),
    markTaskPreviewLoading: () => setLoadState("loading"),
    markTaskPreviewReady: () => setLoadState("ready"),
    openTaskPreviewItem,
    previewDialog,
    previewImageLoadFailed,
    previewKindForUrl,
    taskPreviewIsLoading,
    taskPreviewLoadState,
    taskPreviewMediaItems,
  };
}
