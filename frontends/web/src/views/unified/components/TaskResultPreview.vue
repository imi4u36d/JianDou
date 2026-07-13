<template>
  <section class="detail-section detail-section-card detail-preview-section">
    <div class="detail-section__head">
      <h3>结果预览</h3>
      <span class="surface-chip">{{ progressPercent }}%</span>
    </div>
    <div
      class="task-result-preview"
      :class="{
        'task-result-preview-loading': previewLoading,
        'task-result-preview-with-references': referenceItems.length > 0,
      }"
    >
      <aside v-if="referenceItems.length" class="task-reference-panel" aria-label="参考图">
        <div class="task-reference-panel__head">
          <span>参考图</span><small>{{ referenceItems.length }} 张</small>
        </div>
        <div class="task-reference-stack">
          <article
            v-for="(item, index) in referenceItems"
            :key="`reference-${item.url}`"
            class="task-reference-card"
            :style="referenceCardStyle(index)"
          >
            <button
              type="button"
              class="task-reference-card__preview"
              :aria-label="`预览${item.title}`"
              @click="$emit('preview', item.title, item.url)"
            >
              <img :src="item.thumbnailUrl || item.url" :alt="item.title" loading="lazy" />
            </button>
            <button
              class="task-reference-card__download"
              type="button"
              :aria-label="`下载${item.title}`"
              @click.stop="$emit('download', item.url, item.title, 'image')"
            >
              <IconDownload size="xs" />
            </button>
          </article>
        </div>
      </aside>

      <div class="task-result-preview__main">
        <template v-for="media in mediaItems" :key="`${media.type}-${media.url}`">
          <div class="task-result-preview__actions">
            <button
              type="button"
              class="task-result-preview__action"
              @click="$emit('preview', media.title || '任务结果预览', media.url)"
            >
              <IconImage v-if="media.type === 'image'" size="xs" /><IconVideo v-else size="xs" />预览
            </button>
            <button
              class="task-result-preview__action"
              type="button"
              @click="$emit('download', media.url, media.title || '任务结果', media.type)"
            >
              <IconDownload size="xs" />下载
            </button>
            <button
              v-if="shareable"
              class="task-result-preview__action"
              type="button"
              :disabled="sharing"
              @click="$emit('share')"
            >
              <IconShare size="xs" />{{ shared ? "已分享" : "分享" }}
            </button>
          </div>
          <video
            v-if="media.type === 'video'"
            :src="media.url"
            :poster="media.posterUrl || undefined"
            controls
            playsinline
            preload="metadata"
            :aria-label="media.title"
            @loadstart="$emit('loading')"
            @loadedmetadata="$emit('ready')"
            @loadeddata="$emit('ready')"
            @canplay="$emit('ready')"
            @error="$emit('failed')"
          ></video>
          <button
            v-else
            type="button"
            class="task-result-preview__image-button"
            :aria-label="`预览${media.title || '任务结果'}`"
            @click="$emit('preview', media.title || '任务结果预览', media.url)"
          >
            <img class="task-result-preview__image-glow" :src="media.url" alt="" aria-hidden="true" loading="lazy" />
            <img
              class="task-result-preview__image"
              :src="media.url"
              :alt="media.title || '任务结果预览'"
              @load="$emit('ready')"
              @error="$emit('failed')"
            />
          </button>
        </template>
        <div
          v-if="!mediaItems.length && awaitingCompletedPreview"
          class="task-result-preview__pending"
          role="status"
          aria-live="polite"
        >
          <IconLoading size="md" /><span>加载预览中</span>
        </div>
        <div v-else-if="!mediaItems.length">{{ taskStatus === "COMPLETED" ? "暂无可预览结果" : "生成中" }}</div>
        <div v-if="previewLoading" class="task-result-preview__loading" role="status" aria-live="polite">
          <IconLoading size="md" /><span>加载预览中</span>
        </div>
        <div v-else-if="loadState === 'failed'" class="task-result-preview__loading task-result-preview__loading-error">
          <IconWarning size="sm" /><span>预览加载失败</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { IconDownload, IconImage, IconLoading, IconShare, IconVideo, IconWarning } from "@/components/icons";
import type { DownloadMediaKind } from "@/utils/download";

interface PreviewItem {
  url: string;
  title: string;
  thumbnailUrl?: string | null;
  posterUrl?: string | null;
  type: "image" | "video";
}
interface ReferenceItem {
  url: string;
  title: string;
  thumbnailUrl?: string | null;
}

defineProps<{
  progressPercent: number;
  previewLoading: boolean;
  loadState: "idle" | "loading" | "ready" | "failed";
  mediaItems: PreviewItem[];
  referenceItems: ReferenceItem[];
  awaitingCompletedPreview: boolean;
  taskStatus: string;
  shareable: boolean;
  sharing: boolean;
  shared: boolean;
}>();
defineEmits<{
  preview: [title: string, url: string];
  download: [url: string, title: string, mediaType: DownloadMediaKind];
  share: [];
  loading: [];
  ready: [];
  failed: [];
}>();

function referenceCardStyle(index: number) {
  const direction = index % 2 === 0 ? -1 : 1;
  return {
    zIndex: String(20 - index),
    transform: `translateX(${direction * Math.min(index, 3) * 5}px) rotate(${direction * Math.min(index + 1, 4) * 1.4}deg)`,
  };
}
</script>

<style scoped src="./task-result-preview.css"></style>
