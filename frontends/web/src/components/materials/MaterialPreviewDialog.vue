<template>
  <Teleport to="body">
    <div v-if="open" class="material-preview-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
      <div
        class="material-preview-dialog"
        :class="{
          'material-preview-dialog-video': kind === 'image' || kind === 'video',
        }"
      >
        <div class="material-preview-dialog__head">
          <div>
            <h3>{{ title }}</h3>
          </div>
          <button type="button" class="material-preview-dialog__close" aria-label="关闭预览" @click="emit('close')">
            <IconClose size="sm" />
          </button>
        </div>
        <img
          v-if="kind === 'image' && !imageLoadFailed"
          class="material-preview-dialog__image"
          :src="url"
          :alt="title"
          @error="emit('imageError')"
        />
        <div v-else-if="kind === 'image'" class="material-preview-dialog__fallback">
          <IconImage size="lg" />
          <span>{{ title }}</span>
        </div>
        <video
          v-else-if="kind === 'video' && url"
          class="material-preview-dialog__video"
          :src="url"
          controls
          playsinline
          preload="metadata"
        ></video>
        <div v-else-if="kind === 'video'" class="material-preview-dialog__video-empty">
          <IconVideo size="lg" />
          <span>暂无可播放视频</span>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-else class="material-preview-dialog__markdown" v-html="html"></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { IconClose, IconImage, IconVideo } from "@/components/icons";

defineProps<{
  open: boolean;
  kind: "storyboard" | "image" | "video";
  title: string;
  html?: string;
  url?: string;
  imageLoadFailed?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  imageError: [];
}>();
</script>

<style scoped>
.material-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-preview-dialog {
  display: flex;
  flex-direction: column;
  width: min(980px, calc(100vw - 48px));
  max-height: min(86vh, 960px);
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 72px rgba(15, 23, 42, 0.16);
}

.material-preview-dialog-video {
  width: min(1120px, calc(100vw - 48px));
}

.material-preview-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.material-preview-dialog__head h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.35;
}

.material-preview-dialog__close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
}

.material-preview-dialog__close:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.material-preview-dialog__image,
.material-preview-dialog__video {
  display: block;
  width: 100%;
  max-height: calc(86vh - 72px);
  background: #0f172a;
}

.material-preview-dialog__image {
  object-fit: contain;
  background: #f8fafc;
}

.material-preview-dialog__video {
  object-fit: contain;
}

.material-preview-dialog__fallback,
.material-preview-dialog__video-empty {
  display: grid;
  place-items: center;
  gap: 10px;
  min-height: 420px;
  color: var(--text-muted);
  background: #eef2ff;
}

.material-preview-dialog__markdown {
  max-height: calc(86vh - 72px);
  padding: 22px;
  overflow: auto;
  color: var(--text-body);
  line-height: 1.68;
}

.material-preview-dialog__markdown :deep(h1),
.material-preview-dialog__markdown :deep(h2),
.material-preview-dialog__markdown :deep(h3) {
  margin: 0 0 12px;
  color: var(--text-strong);
}

.material-preview-dialog__markdown :deep(p) {
  margin: 0 0 12px;
}

.material-preview-dialog__markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.material-preview-dialog__markdown :deep(th),
.material-preview-dialog__markdown :deep(td) {
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  vertical-align: top;
}

@media (max-width: 720px) {
  .material-preview-overlay {
    padding: 12px;
  }

  .material-preview-dialog,
  .material-preview-dialog-video {
    width: calc(100vw - 24px);
    border-radius: 18px;
  }

  .material-preview-dialog__head {
    padding: 12px 14px;
  }

  .material-preview-dialog__fallback,
  .material-preview-dialog__video-empty {
    min-height: 260px;
  }
}
</style>
