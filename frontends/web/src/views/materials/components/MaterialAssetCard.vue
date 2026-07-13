<template>
  <article
    class="material-card"
    :class="{ 'material-card-selected': selected, 'material-card-batchable': batchMode }"
    :aria-selected="batchMode ? selected : undefined"
    @click="handleCardClick"
  >
    <label v-if="batchMode" class="material-card__check" @click.stop>
      <input type="checkbox" :checked="selected" @change="emit('toggleSelection', asset.id)" />
      <span></span>
    </label>

    <div class="material-card__preview" :class="assetPreviewClass(asset)" :style="assetPreviewStyle(asset)">
      <button
        v-if="asset.mediaType === 'video' && assetVideoPosterUrl(asset)"
        class="material-preview-trigger material-preview-trigger-video"
        type="button"
        @click.stop="handlePreview"
      >
        <span
          v-if="!isPreviewImageFailed(assetVideoPosterUrl(asset))"
          class="material-preview-backdrop"
          :style="assetPreviewBackdropStyle(assetVideoPosterUrl(asset))"
          aria-hidden="true"
        ></span>
        <img
          v-if="!isPreviewImageFailed(assetVideoPosterUrl(asset))"
          :src="assetVideoPosterUrl(asset)"
          :alt="asset.title"
          loading="lazy"
          decoding="async"
          fetchpriority="low"
          @error="markPreviewImageFailed(assetVideoPosterUrl(asset))"
        />
        <span v-else class="material-preview-fallback"><IconImage size="sm" /></span>
        <span class="material-video-play" aria-hidden="true"><IconVideo size="xs" /></span>
      </button>
      <button
        v-else-if="asset.mediaType === 'video'"
        class="material-preview-trigger material-preview-trigger-placeholder"
        type="button"
        @click.stop="handlePreview"
      >
        <span><IconVideo size="sm" /></span>
      </button>
      <button
        v-else-if="asset.mediaType === 'image' && assetListImageUrl(asset)"
        class="material-preview-trigger material-preview-trigger-image"
        type="button"
        @click.stop="handlePreview"
      >
        <span
          v-if="!isPreviewImageFailed(assetListImageUrl(asset))"
          class="material-preview-backdrop"
          :style="assetPreviewBackdropStyle(assetListImageUrl(asset))"
          aria-hidden="true"
        ></span>
        <img
          v-if="!isPreviewImageFailed(assetListImageUrl(asset))"
          :src="assetListImageUrl(asset)"
          :alt="asset.title"
          loading="lazy"
          decoding="async"
          fetchpriority="low"
          @error="markPreviewImageFailed(assetListImageUrl(asset))"
        />
        <span v-else class="material-preview-fallback"><IconImage size="sm" /></span>
      </button>
      <button
        v-else-if="asset.mediaType === 'image'"
        class="material-preview-trigger material-preview-trigger-placeholder"
        type="button"
        @click.stop="handlePreview"
      >
        <span><IconImage size="sm" /></span>
      </button>
      <button
        v-else
        class="material-preview-trigger material-preview-trigger-text"
        type="button"
        @click.stop="handlePreview"
      >
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="material-card__text" v-html="storyboardPreviewHtml(asset)"></div>
      </button>
    </div>

    <button
      type="button"
      class="material-card__favorite"
      :class="{ 'material-card__favorite-active': favorite }"
      :aria-label="favorite ? '已收藏，管理收藏夹' : '收藏素材'"
      :title="favorite ? '已收藏' : '收藏'"
      @click.stop="handleFavorite"
    >
      <IconHeart size="sm" :filled="favorite" />
    </button>

    <div class="material-card__body">
      <strong class="material-card__title">{{ asset.title }}</strong>
      <div class="material-card__meta-row">
        <span>{{ assetOverlayMeta(asset) }}</span>
        <div class="material-more-menu">
          <button
            type="button"
            class="material-more-menu__trigger"
            aria-label="更多操作"
            :popovertarget="`material-menu-${asset.id}`"
            @click.stop
          >
            <IconMore size="sm" />
          </button>
          <div
            :id="`material-menu-${asset.id}`"
            popover
            class="material-more-menu__panel"
            @beforetoggle="positionMenu"
          >
            <button
              type="button"
              :disabled="busyActionKey === `upload-${asset.id}` || Boolean(asset.remoteUrl)"
              @click="handleMenuAction($event, () => emit('upload', asset.id))"
            >
              <IconLoading v-if="busyActionKey === `upload-${asset.id}`" size="xs" />
              <IconUpload v-else size="xs" />
              <span>{{ busyActionKey === `upload-${asset.id}` ? "上传中" : asset.remoteUrl ? "已上传" : "上传" }}</span>
            </button>
            <button
              type="button"
              :disabled="busyActionKey === `reuse-${asset.id}`"
              @click="handleMenuAction($event, () => emit('reuse', asset.id))"
            >
              <IconLoading v-if="busyActionKey === `reuse-${asset.id}`" size="xs" />
              <IconPlus v-else size="xs" />
              <span>{{ busyActionKey === `reuse-${asset.id}` ? "复用中" : "复用" }}</span>
            </button>
            <button
              type="button"
              :disabled="busyActionKey === `rename-${asset.id}`"
              @click="handleMenuAction($event, () => emit('rename', asset))"
            >
              <IconEdit size="xs" />
              <span>修改名称</span>
            </button>
            <RouterLink v-if="asset.workflowId" :to="`/video-tasks/${asset.workflowId}`">
              <IconWorkflow size="xs" />
              <span>视频</span>
            </RouterLink>
            <button type="button" @click="handleMenuAction($event, () => emit('download', asset))">
              <IconDownload size="xs" />
              <span>下载</span>
            </button>
            <button
              v-if="isAssetShareable(asset)"
              type="button"
              :disabled="sharing"
              @click="handleMenuAction($event, () => emit('share', asset))"
            >
              <IconShare size="xs" />
              <span>{{ shared ? "已分享" : "分享" }}</span>
            </button>
            <button
              type="button"
              class="material-menu-danger"
              :disabled="busyActionKey === `delete-${asset.id}`"
              @click="handleMenuAction($event, () => emit('delete', asset))"
            >
              <IconLoading v-if="busyActionKey === `delete-${asset.id}`" size="xs" />
              <IconDelete v-else size="xs" />
              <span>{{ busyActionKey === `delete-${asset.id}` ? "删除中" : "删除" }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { RouterLink } from "vue-router";
import type { MaterialAssetLibraryItem } from "@/types";
import {
  assetListImageUrl,
  assetOverlayMeta,
  assetPreviewBackdropStyle,
  assetPreviewClass,
  assetPreviewStyle,
  assetVideoPosterUrl,
  isAssetShareable,
  storyboardPreviewHtml,
} from "@/features/materials/material-library-presenters";
import {
  IconDelete,
  IconDownload,
  IconEdit,
  IconHeart,
  IconImage,
  IconLoading,
  IconMore,
  IconPlus,
  IconShare,
  IconUpload,
  IconVideo,
  IconWorkflow,
} from "@/components/icons";

const props = defineProps<{
  asset: MaterialAssetLibraryItem;
  batchMode: boolean;
  selected: boolean;
  favorite: boolean;
  busyActionKey: string;
  sharing: boolean;
  shared: boolean;
}>();

const emit = defineEmits<{
  toggleSelection: [assetId: string];
  preview: [asset: MaterialAssetLibraryItem];
  favorite: [asset: MaterialAssetLibraryItem];
  upload: [assetId: string];
  reuse: [assetId: string];
  rename: [asset: MaterialAssetLibraryItem];
  download: [asset: MaterialAssetLibraryItem];
  share: [asset: MaterialAssetLibraryItem];
  delete: [asset: MaterialAssetLibraryItem];
}>();

const failedPreviewUrls = ref(new Set<string>());

function isPreviewImageFailed(url?: string | null) {
  return Boolean(url && failedPreviewUrls.value.has(url));
}

function markPreviewImageFailed(url?: string | null) {
  if (!url) return;
  const next = new Set(failedPreviewUrls.value);
  next.add(url);
  failedPreviewUrls.value = next;
}

function handleCardClick() {
  if (props.batchMode) emit("toggleSelection", props.asset.id);
}

function handlePreview() {
  if (props.batchMode) {
    emit("toggleSelection", props.asset.id);
    return;
  }
  emit("preview", props.asset);
}

function handleFavorite() {
  if (props.batchMode) {
    emit("toggleSelection", props.asset.id);
    return;
  }
  emit("favorite", props.asset);
}

function positionMenu(event: ToggleEvent) {
  if (event.newState !== "open") return;
  const popover = event.target as HTMLElement;
  const trigger = popover.parentElement?.querySelector<HTMLElement>(".material-more-menu__trigger");
  if (!trigger) return;
  const rect = trigger.getBoundingClientRect();
  const width = 170;
  const height = Math.max(popover.scrollHeight, popover.offsetHeight, 126);
  const left = Math.min(Math.max(rect.right - width, 8), window.innerWidth - width - 8);
  const top = rect.bottom + 4 + height <= window.innerHeight - 8 ? rect.bottom + 4 : Math.max(8, rect.top - height - 4);
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

function closeMenu(event: Event) {
  const target = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  const popover = target?.closest<HTMLElement>(".material-more-menu__panel");
  if (popover && "hidePopover" in popover) {
    popover.hidePopover();
  }
}

function handleMenuAction(event: Event, action: () => void) {
  closeMenu(event);
  action();
}
</script>

<style scoped src="./material-asset-card.css"></style>
