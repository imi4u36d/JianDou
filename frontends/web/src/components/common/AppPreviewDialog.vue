<template>
  <Teleport to="body">
    <Transition name="app-preview-dialog-fade">
      <div
        v-if="open"
        ref="overlayRef"
        class="app-preview-dialog-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="app-preview-dialog-title"
        tabindex="-1"
        @click.self="emit('close')"
        @keydown.esc.stop.prevent="emit('close')"
        @keydown.left.stop.prevent="handlePrevious"
        @keydown.right.stop.prevent="handleNext"
        @touchstart.passive="handleTouchStart"
        @touchend.passive="handleTouchEnd"
      >
        <div class="app-preview-dialog" :class="{ 'app-preview-dialog-wide': widePanel }">
          <div class="app-preview-dialog__head">
            <div class="app-preview-dialog__title">
              <h3 id="app-preview-dialog-title">{{ title }}</h3>
              <p v-if="subtitle">{{ subtitle }}</p>
            </div>
            <div class="app-preview-dialog__actions">
              <button
                v-if="downloadUrl"
                type="button"
                class="jd-button jd-button--sm"
                aria-label="下载预览内容"
                @click="handleDownload"
              >
                <IconDownload size="xs" />
                <span>下载</span>
              </button>
              <slot name="actions"></slot>
              <button type="button" class="app-preview-dialog__close" aria-label="关闭预览" @click="emit('close')">
                <IconClose size="sm" />
              </button>
            </div>
          </div>

          <div
            class="app-preview-dialog__content"
            :class="{ 'app-preview-dialog__content-with-details': $slots.details }"
          >
            <div class="app-preview-dialog__body">
              <slot>
                <div v-if="kind === 'image' && !imageLoadFailed" class="app-preview-dialog__media">
                  <img
                    class="app-preview-dialog__image"
                    :src="url"
                    :alt="title"
                    @load="markMediaReady"
                    @error="handleImageError"
                  />
                  <div v-if="mediaLoading" class="app-preview-dialog__loading" role="status" aria-live="polite">
                    <IconLoading size="md" />
                    <span>加载预览中</span>
                  </div>
                </div>
                <div v-else-if="kind === 'image'" class="app-preview-dialog__fallback">
                  <IconImage size="lg" />
                  <span>{{ title }}</span>
                </div>
                <div v-else-if="kind === 'video' && url" class="app-preview-dialog__media">
                  <video
                    class="app-preview-dialog__video"
                    :src="url"
                    controls
                    playsinline
                    preload="metadata"
                    @loadstart="markMediaLoading"
                    @loadedmetadata="markMediaReady"
                    @loadeddata="markMediaReady"
                    @canplay="markMediaReady"
                  ></video>
                  <div v-if="mediaLoading" class="app-preview-dialog__loading" role="status" aria-live="polite">
                    <IconLoading size="md" />
                    <span>加载预览中</span>
                  </div>
                </div>
                <div v-else-if="kind === 'video'" class="app-preview-dialog__fallback">
                  <IconVideo size="lg" />
                  <span>暂无可播放视频</span>
                </div>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-else class="app-preview-dialog__markdown" v-html="html"></div>
              </slot>
            </div>
            <aside v-if="$slots.details" class="app-preview-dialog__details" aria-label="预览详情">
              <slot name="details"></slot>
            </aside>
          </div>

          <button
            v-if="showNavigation"
            type="button"
            class="app-preview-dialog__nav app-preview-dialog__nav-prev"
            :disabled="!canPrevious"
            aria-label="预览上一个素材"
            title="上一个"
            @click="handlePrevious"
          >
            <IconChevronDown size="sm" />
          </button>
          <button
            v-if="showNavigation"
            type="button"
            class="app-preview-dialog__nav app-preview-dialog__nav-next"
            :disabled="!canNext"
            aria-label="预览下一个素材"
            title="下一个"
            @click="handleNext"
          >
            <IconChevronDown size="sm" />
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { IconChevronDown, IconClose, IconDownload, IconImage, IconLoading, IconVideo } from "@/components/icons";
import { useAppPreviewDialog, type AppPreviewDialogProps } from "./useAppPreviewDialog";

const props = withDefaults(defineProps<AppPreviewDialogProps>(), {
  subtitle: "",
  html: "",
  url: "",
  imageLoadFailed: false,
  showDownload: true,
  showNavigation: false,
  canPrevious: false,
  canNext: false,
});

const emit = defineEmits<{
  close: [];
  imageError: [];
  previous: [];
  next: [];
}>();
const {
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
} = useAppPreviewDialog(props, emit);
</script>

<style scoped src="./app-preview-dialog.css"></style>
