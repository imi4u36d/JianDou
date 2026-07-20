<template>
  <section class="public-share-gallery" aria-label="用户分享">
    <div class="public-share-gallery__head">
      <h2>作品</h2>
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
            <img
              v-if="publicSharePreviewUrl(item)"
              :src="publicSharePreviewUrl(item)"
              :alt="item.title"
              loading="lazy"
            />
            <span v-else class="public-share-card__placeholder">{{
              item.mediaType === "video" ? "视频" : "图片"
            }}</span>
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
            <img
              v-if="publicSharePreviewUrl(item)"
              :src="publicSharePreviewUrl(item)"
              :alt="item.title"
              loading="lazy"
            />
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
        <img
          v-if="previewItem.mediaType === 'image'"
          :src="publicShareMediaUrl(previewItem)"
          :alt="previewItem.title"
        />
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
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import { IconDownload, IconHeart, IconRefresh, IconVideo } from "@/components/icons";
import { publicShareCardStyle, publicSharePreviewUrl } from "@/utils/public-shares";
import { publicShareMediaUrl, usePublicShareGallery } from "./usePublicShareGallery";

const {
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
} = usePublicShareGallery();
</script>

<style scoped src="./public-share-gallery.css"></style>
