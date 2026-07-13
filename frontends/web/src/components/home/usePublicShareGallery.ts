import { onMounted, ref } from "vue";
import { fetchPublicShares, likePublicShare, unlikePublicShare } from "@/api/public-shares";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";
import type { PublicShareItem } from "@/types";

interface PublicShareGalleryDependencies {
  fetch?: typeof fetchPublicShares;
  like?: typeof likePublicShare;
  unlike?: typeof unlikePublicShare;
  download?: typeof downloadMedia;
  message?: Pick<typeof messageApi, "success" | "info" | "error">;
  loadOnMount?: boolean;
}

export function publicShareMediaUrl(item: PublicShareItem) {
  return item.publicUrl || item.fileUrl || "";
}

export function usePublicShareGallery(dependencies: PublicShareGalleryDependencies = {}) {
  const fetchShares = dependencies.fetch ?? fetchPublicShares;
  const likeShare = dependencies.like ?? likePublicShare;
  const unlikeShare = dependencies.unlike ?? unlikePublicShare;
  const download = dependencies.download ?? downloadMedia;
  const message = dependencies.message ?? messageApi;
  const imageShares = ref<PublicShareItem[]>([]);
  const videoShares = ref<PublicShareItem[]>([]);
  const loading = ref(false);
  const likeBusy = ref(false);
  const previewItem = ref<PublicShareItem | null>(null);

  function replaceShare(updated: PublicShareItem) {
    const list = updated.mediaType === "video" ? videoShares.value : imageShares.value;
    const index = list.findIndex((item) => item.shareId === updated.shareId);
    if (index >= 0) list[index] = updated;
    if (previewItem.value?.shareId === updated.shareId) previewItem.value = updated;
  }

  async function loadAll() {
    loading.value = true;
    try {
      const [images, videos] = await Promise.all([
        fetchShares({ type: "image", limit: 24, sort: "popular" }),
        fetchShares({ type: "video", limit: 24, sort: "popular" }),
      ]);
      imageShares.value = Array.isArray(images.items) ? images.items : [];
      videoShares.value = Array.isArray(videos.items) ? videos.items : [];
    } catch (error) {
      imageShares.value = [];
      videoShares.value = [];
      message.error(error instanceof Error ? error.message : "分享内容加载失败");
    } finally {
      loading.value = false;
    }
  }

  function openPreview(item: PublicShareItem) {
    previewItem.value = item;
  }

  function closePreview() {
    previewItem.value = null;
  }

  async function toggleLike(item: PublicShareItem) {
    if (likeBusy.value) return;
    likeBusy.value = true;
    try {
      replaceShare(item.likedByMe ? await unlikeShare(item.shareId) : await likeShare(item.shareId));
    } catch (error) {
      message.error(error instanceof Error ? error.message : "点赞失败");
    } finally {
      likeBusy.value = false;
    }
  }

  async function downloadPreview(item: PublicShareItem) {
    try {
      const result = await download({
        url: publicShareMediaUrl(item),
        title: item.title,
        mediaType: item.mediaType,
      });
      if (result.target === "album") message.success("已保存到相册");
      else if (result.target === "share") message.info("已打开系统分享，可保存到相册");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  if (dependencies.loadOnMount !== false) onMounted(loadAll);

  return {
    imageShares,
    videoShares,
    loading,
    likeBusy,
    previewItem,
    loadAll,
    openPreview,
    closePreview,
    toggleLike,
    downloadPreview,
  };
}
