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
            <img
              class="task-result-preview__image"
              :src="media.url"
              :alt="media.title || '任务结果预览'"
              @load="handleImageReady(media, $event)"
              @error="$emit('failed')"
            />
            <span v-if="imageMetadataByUrl[media.url]" class="task-result-preview__image-meta">
              {{ imageMetadataByUrl[media.url] }}
            </span>
          </button>
        </template>
        <div
          v-if="!mediaItems.length && awaitingCompletedPreview"
          class="task-result-preview__empty task-result-preview__pending"
          role="status"
          aria-live="polite"
        >
          <span class="task-result-preview__empty-icon" aria-hidden="true"><IconLoading size="md" /></span>
          <strong>加载预览中</strong>
          <span>结果生成完成后会自动显示在这里。</span>
        </div>
        <div v-else-if="!mediaItems.length" class="task-result-preview__empty">
          <span class="task-result-preview__empty-icon" aria-hidden="true">
            <IconImage v-if="taskStatus === 'COMPLETED'" size="md" />
            <IconLoading v-else size="md" />
          </span>
          <strong>{{ taskStatus === "COMPLETED" ? "暂无可预览结果" : "正在生成结果" }}</strong>
          <span>
            {{ taskStatus === "COMPLETED" ? "当前任务没有可展示的图片结果。" : "任务处理完成后，结果会显示在这里。" }}
          </span>
        </div>
        <div v-if="previewLoading" class="task-result-preview__loading" role="status" aria-live="polite">
          <span class="task-result-preview__empty-icon" aria-hidden="true"><IconLoading size="md" /></span>
          <strong>加载预览中</strong>
          <span>正在获取预览资源，请稍候。</span>
        </div>
        <div v-else-if="loadState === 'failed'" class="task-result-preview__loading task-result-preview__loading-error">
          <span class="task-result-preview__empty-icon" aria-hidden="true"><IconWarning size="sm" /></span>
          <strong>预览加载失败</strong>
          <span>资源暂时无法显示，请稍后刷新重试。</span>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { reactive } from "vue";
import { IconDownload, IconImage, IconLoading, IconVideo, IconWarning } from "@/components/icons";
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
}>();
const emit = defineEmits<{
  preview: [title: string, url: string];
  download: [url: string, title: string, mediaType: DownloadMediaKind];
  loading: [];
  ready: [];
  failed: [];
}>();
const imageMetadataByUrl = reactive<Record<string, string>>({});
function greatestCommonDivisor(left: number, right: number): number {
  let a = Math.abs(Math.trunc(left));
  let b = Math.abs(Math.trunc(right));
  while (b) {
    [a, b] = [b, a % b];
  }
  return a || 1;
}
function handleImageReady(media: PreviewItem, event: Event) {
  const image = event.currentTarget as HTMLImageElement;
  const width = image.naturalWidth;
  const height = image.naturalHeight;
  if (width > 0 && height > 0) {
    const divisor = greatestCommonDivisor(width, height);
    imageMetadataByUrl[media.url] = `分辨率 ${width} × ${height} px · 比例 ${width / divisor}:${height / divisor}`;
  }
  emit("ready");
}
function referenceCardStyle(index: number) {
  const direction = index % 2 === 0 ? -1 : 1;
  return {
    zIndex: String(20 - index),
    transform: `translateX(${direction * Math.min(index, 3) * 5}px) rotate(${direction * Math.min(index + 1, 4) * 1.4}deg)`,
  };
}
</script>
<style scoped src="./task-result-preview.css"></style>
