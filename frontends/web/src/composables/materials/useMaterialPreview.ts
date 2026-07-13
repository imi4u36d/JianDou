import { computed, reactive, ref, type Ref } from "vue";
import { assetOriginalImageUrl, assetVideoPreviewUrl, storyboardPreviewHtml } from "@/features/materials/material-library-presenters";
import type { MaterialAssetLibraryItem } from "@/types";

interface MaterialPreviewOptions {
  displayedAssets: Readonly<Ref<MaterialAssetLibraryItem[]>>;
  activeFavoriteFolderId: Readonly<Ref<string>>;
  hasMoreAssets: Readonly<Ref<boolean>>;
  loadMoreAssets: () => Promise<unknown>;
}

export function useMaterialPreview(options: MaterialPreviewOptions) {
  const previewAsset = ref<MaterialAssetLibraryItem | null>(null);
  const previewImageLoadFailed = ref(false);
  const previewDialog = reactive({
    open: false,
    kind: "storyboard" as "storyboard" | "image" | "video",
    title: "",
    html: "",
    url: "",
  });

  const previewAssetIndex = computed(() => {
    if (!previewAsset.value) return -1;
    return options.displayedAssets.value.findIndex((item) => item.id === previewAsset.value?.id);
  });

  const canPreviewPrevious = computed(() => previewAssetIndex.value > 0);
  const canPreviewNext = computed(() => {
    const index = previewAssetIndex.value;
    return index >= 0 && (index < options.displayedAssets.value.length - 1 || (!options.activeFavoriteFolderId.value && options.hasMoreAssets.value));
  });

  function openAssetPreview(asset: MaterialAssetLibraryItem) {
    previewAsset.value = asset;
    previewImageLoadFailed.value = false;
    previewDialog.title = asset.title;
    if (asset.mediaType === "video") {
      previewDialog.kind = "video";
      previewDialog.html = "";
      previewDialog.url = assetVideoPreviewUrl(asset);
    } else if (asset.mediaType === "image") {
      previewDialog.kind = "image";
      previewDialog.html = "";
      previewDialog.url = assetOriginalImageUrl(asset);
    } else {
      previewDialog.kind = "storyboard";
      previewDialog.html = storyboardPreviewHtml(asset);
      previewDialog.url = "";
    }
    previewDialog.open = true;
  }

  function closePreviewDialog() {
    previewDialog.open = false;
    previewDialog.html = "";
    previewDialog.url = "";
    previewAsset.value = null;
    previewImageLoadFailed.value = false;
  }

  function syncPreviewAsset(asset: MaterialAssetLibraryItem) {
    if (previewAsset.value?.id === asset.id) openAssetPreview(asset);
  }

  async function navigatePreview(direction: -1 | 1) {
    if (!previewDialog.open || !previewAsset.value) return;
    const currentIndex = previewAssetIndex.value;
    if (currentIndex < 0) return;

    const nextIndex = currentIndex + direction;
    let nextAsset = options.displayedAssets.value[nextIndex];
    let loadAttempts = 0;
    while (!nextAsset && direction > 0 && !options.activeFavoriteFolderId.value && options.hasMoreAssets.value && loadAttempts < 5) {
      loadAttempts += 1;
      await options.loadMoreAssets();
      nextAsset = options.displayedAssets.value[nextIndex];
    }
    if (nextAsset) openAssetPreview(nextAsset);
  }

  return {
    previewAsset,
    previewImageLoadFailed,
    previewDialog,
    canPreviewPrevious,
    canPreviewNext,
    openAssetPreview,
    closePreviewDialog,
    syncPreviewAsset,
    navigatePreview,
  };
}
