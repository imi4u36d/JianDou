<template>
  <section class="public-share-gallery" aria-label="用户分享">
    <div class="public-share-gallery__head">
      <h2>大家正在分享</h2>
      <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="loading" @click="loadAll">
        <IconRefresh size="xs" />
        刷新
      </button>
    </div>

    <div class="public-share-gallery__groups">
      <section class="public-share-row" aria-labelledby="public-share-images-title">
        <div class="public-share-row__head">
          <h3 id="public-share-images-title">图片</h3>
          <span>{{ imageShares.length }} 个作品</span>
        </div>
        <div class="public-share-row__rail">
          <button
            v-for="item in imageShares"
            :key="item.shareId"
            type="button"
            class="public-share-card public-share-card-image"
            :style="publicShareCardStyle(item)"
            @click="openPreview(item)"
          >
            <img v-if="publicSharePreviewUrl(item)" :src="publicSharePreviewUrl(item)" :alt="item.title" loading="lazy" />
            <span v-else class="public-share-card__placeholder">{{ item.mediaType === "video" ? "视频" : "图片" }}</span>
            <span class="public-share-card__meta">
              <strong>{{ item.title }}</strong>
              <small><IconHeart size="xs" :filled="item.likedByMe" /> {{ item.likeCount }}</small>
            </span>
          </button>
          <div v-if="!imageShares.length && !loading" class="public-share-empty">暂无图片分享</div>
          <div v-if="loading && !imageShares.length" class="public-share-empty">加载中</div>
        </div>
      </section>

      <section class="public-share-row" aria-labelledby="public-share-videos-title">
        <div class="public-share-row__head">
          <h3 id="public-share-videos-title">视频</h3>
          <span>{{ videoShares.length }} 个作品</span>
        </div>
        <div class="public-share-row__rail">
          <button
            v-for="item in videoShares"
            :key="item.shareId"
            type="button"
            class="public-share-card public-share-card-video"
            :style="publicShareCardStyle(item)"
            @click="openPreview(item)"
          >
            <img v-if="publicSharePreviewUrl(item)" :src="publicSharePreviewUrl(item)" :alt="item.title" loading="lazy" />
            <span v-else class="public-share-card__placeholder">视频</span>
            <span class="public-share-card__play" aria-hidden="true"><IconVideo size="sm" /></span>
            <span class="public-share-card__meta">
              <strong>{{ item.title }}</strong>
              <small><IconHeart size="xs" :filled="item.likedByMe" /> {{ item.likeCount }}</small>
            </span>
          </button>
          <div v-if="!videoShares.length && !loading" class="public-share-empty">暂无视频分享</div>
          <div v-if="loading && !videoShares.length" class="public-share-empty">加载中</div>
        </div>
      </section>
    </div>

    <AppPreviewDialog
      :open="Boolean(previewItem)"
      :kind="previewItem?.mediaType === 'video' ? 'video' : 'image'"
      :title="previewItem?.title ?? ''"
      :subtitle="previewItem?.authorName ?? ''"
      :show-download="false"
      @close="closePreview"
    >
      <template v-if="previewItem" #actions>
        <button type="button" class="jd-button jd-button--sm" :disabled="likeBusy" @click="toggleLike(previewItem)">
          <IconHeart size="xs" :filled="previewItem.likedByMe" />
          <span>{{ previewItem.likeCount }}</span>
        </button>
        <button type="button" class="jd-button jd-button--sm" @click="downloadPreview(previewItem)">
          <IconDownload size="xs" />
          <span>下载</span>
        </button>
      </template>

      <div v-if="previewItem" class="public-share-preview__media">
        <img v-if="previewItem.mediaType === 'image'" :src="publicShareMediaUrl(previewItem)" :alt="previewItem.title" />
        <video
          v-else
          :src="publicShareMediaUrl(previewItem)"
          :poster="publicSharePreviewUrl(previewItem) || undefined"
          controls
          playsinline
          preload="metadata"
        ></video>
      </div>
    </AppPreviewDialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchPublicShares, likePublicShare, unlikePublicShare } from "@/api/public-shares";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import { IconDownload, IconHeart, IconRefresh, IconVideo } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";
import { publicShareCardStyle, publicSharePreviewUrl } from "@/utils/public-shares";
import type { PublicShareItem } from "@/types";

const imageShares = ref<PublicShareItem[]>([]);
const videoShares = ref<PublicShareItem[]>([]);
const loading = ref(false);
const likeBusy = ref(false);
const previewItem = ref<PublicShareItem | null>(null);

function replaceShare(updated: PublicShareItem) {
  const list = updated.mediaType === "video" ? videoShares.value : imageShares.value;
  const index = list.findIndex((item) => item.shareId === updated.shareId);
  if (index >= 0) {
    list[index] = updated;
  }
  if (previewItem.value?.shareId === updated.shareId) {
    previewItem.value = updated;
  }
}

async function loadAll() {
  loading.value = true;
  try {
    const [images, videos] = await Promise.all([
      fetchPublicShares({ type: "image", limit: 24, sort: "popular" }),
      fetchPublicShares({ type: "video", limit: 24, sort: "popular" }),
    ]);
    imageShares.value = Array.isArray(images.items) ? images.items : [];
    videoShares.value = Array.isArray(videos.items) ? videos.items : [];
  } catch (error) {
    imageShares.value = [];
    videoShares.value = [];
    messageApi.error(error instanceof Error ? error.message : "分享内容加载失败");
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

function publicShareMediaUrl(item: PublicShareItem) {
  return item.publicUrl || item.fileUrl || "";
}

async function toggleLike(item: PublicShareItem) {
  if (likeBusy.value) return;
  likeBusy.value = true;
  try {
    const updated = item.likedByMe ? await unlikePublicShare(item.shareId) : await likePublicShare(item.shareId);
    replaceShare(updated);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "点赞失败");
  } finally {
    likeBusy.value = false;
  }
}

async function downloadPreview(item: PublicShareItem) {
  try {
    const result = await downloadMedia({ url: publicShareMediaUrl(item), title: item.title, mediaType: item.mediaType });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

onMounted(() => {
  void loadAll();
});
</script>

<style scoped>
.public-share-gallery {
  display: grid;
  gap: 16px;
  width: min(100%, 1180px);
  margin: 10px auto 0;
}

.public-share-gallery__head,
.public-share-row__head,
.public-share-card__meta,
.public-share-card__meta small {
  display: flex;
  align-items: center;
}

.public-share-gallery__head {
  justify-content: space-between;
  gap: 16px;
}

.public-share-gallery__head h2,
.public-share-row__head h3 {
  margin: 0;
  letter-spacing: 0;
}

.public-share-gallery__head h2 {
  font-size: 1rem;
  font-weight: 800;
}

.public-share-gallery__groups {
  display: grid;
  gap: 14px;
}

.public-share-row {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.public-share-row__head {
  justify-content: space-between;
  color: var(--text-muted);
}

.public-share-row__head h3 {
  color: var(--text-strong);
  font-size: 0.9rem;
}

.public-share-row__head span {
  font-size: 0.75rem;
  font-weight: 700;
}

.public-share-row__rail {
  display: flex;
  gap: 10px;
  min-width: 0;
  overflow-x: auto;
  padding: 2px 2px 10px;
  scroll-snap-type: x proximity;
}

.public-share-row__rail::-webkit-scrollbar {
  height: 8px;
}

.public-share-row__rail::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.1);
}

.public-share-card {
  position: relative;
  flex: 0 0 auto;
  height: 178px;
  min-width: 104px;
  max-width: 392px;
  overflow: hidden;
  padding: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #111827;
  color: #fff;
  cursor: pointer;
  scroll-snap-align: start;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.1);
}

.public-share-card img,
.public-share-card video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.public-share-card__placeholder {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.82rem;
  font-weight: 800;
}

.public-share-card__meta {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  justify-content: space-between;
  gap: 10px;
  padding: 28px 10px 9px;
  background: linear-gradient(180deg, transparent, rgba(0, 0, 0, 0.72));
}

.public-share-card__meta strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.78rem;
}

.public-share-card__meta small {
  gap: 4px;
  flex: 0 0 auto;
  font-size: 0.75rem;
  font-weight: 800;
}

.public-share-card__play {
  position: absolute;
  left: 10px;
  top: 10px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #111827;
}

.public-share-empty {
  flex: 0 0 220px;
  display: grid;
  place-items: center;
  height: 178px;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
  color: var(--text-muted);
  font-size: 0.85rem;
  font-weight: 700;
}

.public-share-preview__media {
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 0;
  background: transparent;
}

.public-share-preview__media img,
.public-share-preview__media video {
  display: block;
  width: 100%;
  max-height: calc(86vh - 76px);
  background: transparent;
  object-fit: contain;
}

.public-share-preview__media img {
  height: auto;
}

.public-share-preview__media video {
  background: #0f172a;
}

@media (max-width: 720px) {
  .public-share-card,
  .public-share-empty {
    height: 132px;
  }

}
</style>
