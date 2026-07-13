<template>
  <section class="character-asset-picker">
    <div class="character-asset-picker__head">
      <h4>{{ title }}素材</h4>
      <button class="workflow-icon-action" type="button" aria-label="关闭素材选择器" @click="$emit('close')">
        <IconClose size="xs" />
      </button>
    </div>
    <div class="character-asset-picker__filters">
      <input
        class="field-input"
        type="search"
        placeholder="关键词"
        :value="picker.keyword"
        @input="$emit('update:keyword', ($event.target as HTMLInputElement).value)"
        @keyup.enter="$emit('search')"
      />
      <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="picker.loading" @click="$emit('search')">
        <IconLoading v-if="picker.loading" size="xs" />
        <IconSearch v-else size="xs" />
        <span>{{ picker.loading ? "搜索中" : "搜索" }}</span>
      </button>
    </div>
    <div v-if="picker.error" class="workflow-error">{{ picker.error }}</div>
    <div v-else-if="!picker.assets.length" class="workflow-empty">没有匹配素材</div>
    <div v-else class="character-asset-grid">
      <article v-for="asset in picker.assets" :key="asset.id" class="character-asset-card">
        <button type="button" class="character-asset-card__preview" @click="$emit('preview', materialAssetPreviewUrl(asset), asset.title)">
          <img
            v-if="isPreviewImageAvailable(materialAssetPreviewUrl(asset))"
            :src="materialAssetPreviewUrl(asset)"
            :alt="asset.title"
            @error="$emit('imageError', materialAssetPreviewUrl(asset))"
          />
          <span v-else class="workflow-image-fallback"><IconEmpty size="sm" /></span>
        </button>
        <div class="character-asset-card__body">
          <strong>{{ asset.title }}</strong>
          <span class="surface-chip surface-chip-quiet">{{ materialAssetModelLabel(asset) }}</span>
        </div>
        <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="busy" @click="$emit('select', asset.id)">
          <span>{{ busy ? "选择中" : "选择" }}</span>
        </button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { IconClose, IconEmpty, IconLoading, IconSearch } from "@/components/icons";
import {
  materialAssetModelLabel,
  materialAssetPreviewUrl,
} from "@/composables/workflow/useCharacterAssetPicker";
import type { MaterialAssetLibraryItem } from "@/types";

defineProps<{
  title: string;
  busy: boolean;
  picker: {
    keyword: string;
    loading: boolean;
    error: string;
    assets: MaterialAssetLibraryItem[];
  };
  isPreviewImageAvailable: (url?: string | null) => boolean;
}>();

defineEmits<{
  close: [];
  search: [];
  "update:keyword": [value: string];
  preview: [url: string, title: string];
  imageError: [url: string];
  select: [assetId: string];
}>();
</script>

<style scoped src="./workflow-character-asset-picker.css"></style>
