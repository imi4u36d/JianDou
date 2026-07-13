import { onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import type { StageVersion, WorkflowCharacterSheet } from "@/types";
import { characterSheetAppearanceSummary, characterSheetTitle } from "./useCharacterSheetUtils";
import { useImagePreview } from "./useImagePreview";

interface WorkflowPreviewFrame {
  url: string;
  label: string;
  role: string;
}

interface WorkflowPreviewInteractionOptions {
  keyframePreviewFrames: (version: StageVersion) => WorkflowPreviewFrame[];
  stageVersionDisplayTitle: (version: StageVersion) => string;
}

export function useWorkflowPreviewInteractions(options: WorkflowPreviewInteractionOptions) {
  const imagePreview = useImagePreview();
  const imagePreviewLoadFailed = ref(false);
  const failedPreviewImageUrls = ref(new Set<string>());
  const characterSummaryPreviewState = reactive({ open: false, title: "", content: "" });

  function isPreviewImageFailed(url?: string | null) {
    return Boolean(url && failedPreviewImageUrls.value.has(url));
  }

  function isPreviewImageAvailable(url?: string | null) {
    return Boolean(url && !failedPreviewImageUrls.value.has(url));
  }

  function markPreviewImageFailed(url?: string | null) {
    if (url) failedPreviewImageUrls.value = new Set(failedPreviewImageUrls.value).add(url);
  }

  function openCharacterSummaryPreview(sheet: WorkflowCharacterSheet) {
    characterSummaryPreviewState.open = true;
    characterSummaryPreviewState.title = characterSheetTitle(sheet);
    characterSummaryPreviewState.content = characterSheetAppearanceSummary(sheet);
  }

  function closeCharacterSummaryPreview() {
    Object.assign(characterSummaryPreviewState, { open: false, title: "", content: "" });
  }

  function openKeyframeImagePreview(version: StageVersion, frame: WorkflowPreviewFrame) {
    if (!frame.url) return;
    const frames = options.keyframePreviewFrames(version).filter((item) => item.url);
    const title = options.stageVersionDisplayTitle(version);
    const gallery = frames.map((item) => ({
      url: item.url,
      alt: `${title}${item.label}`,
      caption: `${title} ${item.label}`,
    }));
    const currentIndex = Math.max(0, frames.findIndex((item) => item.role === frame.role));
    const currentItem = gallery[currentIndex];
    if (!currentItem) {
      imagePreview.openImagePreview(frame.url, `${title}${frame.label}`);
      return;
    }
    imagePreview.captureImagePreviewTrigger();
    imagePreview.imagePreviewState.open = true;
    imagePreview.imagePreviewState.gallery = gallery;
    imagePreview.applyImagePreviewItem(currentItem, currentIndex);
    imagePreview.focusImagePreviewOverlay();
  }

  function handleImagePreviewKeydown(event: KeyboardEvent) {
    if (characterSummaryPreviewState.open && event.key === "Escape") {
      event.preventDefault();
      closeCharacterSummaryPreview();
      return;
    }
    if (!imagePreview.imagePreviewState.open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      imagePreview.closeImagePreview();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      imagePreview.switchImagePreviewFrame(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      imagePreview.switchImagePreviewFrame(1);
    }
  }

  function positionVersionMenu(event: ToggleEvent) {
    if (event.newState !== "open") return;
    const popover = event.target as HTMLElement;
    const trigger = document.querySelector<HTMLElement>(`[popovertarget="${popover.id}"]`);
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const width = popover.offsetWidth || 164;
    const height = Math.max(popover.scrollHeight, popover.offsetHeight, 92);
    const left = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8));
    const preferredTop = rect.bottom + 4;
    const top = preferredTop + height > window.innerHeight - 8
      ? Math.max(8, rect.top - height - 4)
      : preferredTop;
    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
  }

  watch(() => imagePreview.imagePreviewState.url, () => { imagePreviewLoadFailed.value = false; });
  onMounted(() => window.addEventListener("keydown", handleImagePreviewKeydown));
  onBeforeUnmount(() => window.removeEventListener("keydown", handleImagePreviewKeydown));

  return {
    ...imagePreview,
    imagePreviewLoadFailed,
    characterSummaryPreviewState,
    isPreviewImageFailed,
    isPreviewImageAvailable,
    markPreviewImageFailed,
    openCharacterSummaryPreview,
    closeCharacterSummaryPreview,
    openKeyframeImagePreview,
    positionVersionMenu,
  };
}
