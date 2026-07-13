<template>
  <section class="workflow-stage-board character-board">
    <div class="stage-board__head">
      <h3>角色三视图</h3>
      <div class="stage-board__meta">
        <span class="surface-chip">{{ sheets.length }} 个角色</span>
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="!missingCount || busyActionKey === 'character-missing'"
          @click="$emit('generate-missing')"
        >
          <IconLoading v-if="busyActionKey === 'character-missing'" size="xs" />
          <span>{{ busyActionKey === "character-missing" ? "补齐中" : "补齐" }}</span>
        </button>
      </div>
    </div>

    <div v-if="!sheets.length" class="workflow-empty">暂无角色三视图</div>
    <div v-else class="character-list">
      <article v-for="sheet in sheets" :key="characterSheetKey(sheet)" class="character-card">
        <strong>{{ characterSheetTitle(sheet) }}</strong>
        <button
          type="button"
          class="character-card__summary"
          :aria-label="`查看${characterSheetTitle(sheet)}完整角色定义`"
          @click="$emit('summary', sheet)"
        >
          <span>角色定义</span>
          <p>{{ characterSheetAppearanceSummary(sheet) }}</p>
        </button>

        <div v-if="characterSheetVersions(sheet).length > 1" class="version-tabs">
          <article
            v-for="version in characterSheetVersions(sheet)"
            :key="version.id"
            class="version-tab"
            :class="{ 'version-tab-active': previewVersion(sheet)?.id === version.id }"
          >
            <button type="button" @click="$emit('preview-version', characterSheetKey(sheet), version.id)">
              <span class="version-badge">V{{ version.versionNo }}</span>
              <strong>{{ stageVersionDisplayTitle(version) }}</strong>
              <span v-if="version.selected" class="surface-chip">当前</span>
            </button>
          </article>
        </div>

        <div v-if="previewVersion(sheet)" class="character-card__frames">
          <button
            v-for="frame in characterSheetPreviewFrames(previewVersion(sheet)!)"
            :key="`${characterSheetKey(sheet)}-${frame.role}`"
            type="button"
            class="character-frame"
            :aria-label="`查看${characterSheetTitle(sheet)}${frame.label}`"
            @click="$emit('preview-image', frame.url, `${characterSheetTitle(sheet)} ${frame.label}`)"
          >
            <img
              v-if="isImageAvailable(frame.url)"
              :src="frame.url"
              :alt="`${characterSheetTitle(sheet)} ${frame.label}`"
              @error="markImageFailed(frame.url)"
            />
            <span v-else class="image-fallback" aria-hidden="true"><IconEmpty size="sm" /></span>
            <span class="character-frame__label">{{ frame.label }}</span>
          </button>
        </div>

        <div class="character-card__actions">
          <button
            class="jd-button jd-button--secondary jd-button--sm"
            type="button"
            :disabled="characterSheetClipIndex(sheet) === null"
            @click="openCharacterAssetPicker(sheet)"
          >
            <IconSearch size="xs" /><span>素材</span>
          </button>
          <button
            class="jd-button jd-button--ghost jd-button--sm"
            type="button"
            :disabled="
              characterSheetIndex(sheet) === null ||
              busyActionKey === 'character-missing' ||
              busyActionKey === `character-sheet-${characterSheetClipIndex(sheet)}`
            "
            @click="$emit('generate', sheet)"
          >
            <IconRefresh v-if="previewVersion(sheet)" size="xs" />
            <IconPlus v-else size="xs" />
            <span>{{ previewVersion(sheet) ? "重生" : "生成" }}</span>
          </button>
        </div>

        <section v-if="isCharacterAssetPickerOpen(sheet)" class="asset-picker">
          <div class="asset-picker__head">
            <h4>{{ characterSheetTitle(sheet) }}素材</h4>
            <button class="icon-action" type="button" aria-label="收起素材选择" @click="closeCharacterAssetPicker">
              <IconClose size="xs" />
            </button>
          </div>
          <div class="asset-picker__filters">
            <label
              ><span>关键词</span
              ><input
                v-model="characterAssetPicker.keyword"
                class="field-input"
                type="search"
                placeholder="角色或标题"
                @keyup.enter="loadCharacterAssetCandidates(sheet)"
            /></label>
            <label
              ><span>模型</span
              ><input
                v-model="characterAssetPicker.model"
                class="field-input"
                type="search"
                placeholder="模型"
                @keyup.enter="loadCharacterAssetCandidates(sheet)"
            /></label>
            <button
              class="jd-button jd-button--secondary jd-button--sm"
              type="button"
              :disabled="characterAssetPicker.loading"
              @click="loadCharacterAssetCandidates(sheet)"
            >
              <IconLoading v-if="characterAssetPicker.loading" size="xs" /><IconSearch v-else size="xs" /><span>{{
                characterAssetPicker.loading ? "搜索中" : "搜索"
              }}</span>
            </button>
          </div>
          <p v-if="characterAssetPicker.error" class="workflow-error">{{ characterAssetPicker.error }}</p>
          <div v-else-if="characterAssetPicker.loading" class="workflow-empty">加载中</div>
          <div v-else-if="!characterAssetPicker.assets.length" class="workflow-empty">没有匹配素材</div>
          <div v-else class="asset-grid">
            <article v-for="asset in characterAssetPicker.assets" :key="asset.id" class="asset-card">
              <button
                type="button"
                class="asset-card__preview"
                :aria-label="`查看${asset.title}素材预览`"
                @click="$emit('preview-image', materialAssetPreviewUrl(asset), asset.title)"
              >
                <img
                  v-if="isImageAvailable(materialAssetPreviewUrl(asset))"
                  :src="materialAssetPreviewUrl(asset)"
                  :alt="asset.title"
                  @error="markImageFailed(materialAssetPreviewUrl(asset))"
                />
                <span v-else class="image-fallback" aria-hidden="true"><IconEmpty size="sm" /></span>
              </button>
              <strong>{{ asset.title }}</strong>
              <span class="surface-chip surface-chip-quiet">{{ materialAssetModelLabel(asset) }}</span>
              <button
                class="jd-button jd-button--primary jd-button--sm"
                type="button"
                :disabled="busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}`"
                @click="$emit('select-asset', sheet, asset.id)"
              >
                <IconLoading
                  v-if="busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}`"
                  size="xs"
                />
                <span>{{
                  busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}` ? "选择中" : "选择"
                }}</span>
              </button>
            </article>
          </div>
        </section>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useCharacterAssetPicker } from "@/composables/workflow/useCharacterAssetPicker";
import {
  characterSheetAppearanceSummary,
  characterSheetClipIndex,
  characterSheetIndex,
  characterSheetKey,
  characterSheetPreviewFrames,
  characterSheetTitle,
  characterSheetVersions,
} from "@/composables/workflow/useCharacterSheetUtils";
import { stageVersionDisplayTitle } from "@/features/workflows/stage-workflow-presenters";
import type { StageVersion, WorkflowCharacterSheet } from "@/types";
import { IconClose, IconEmpty, IconLoading, IconPlus, IconRefresh, IconSearch } from "@/components/icons";

const props = defineProps<{
  sheets: WorkflowCharacterSheet[];
  missingCount: number;
  previewVersionIds: Record<string, string>;
  busyActionKey: string;
}>();
defineEmits<{
  "generate-missing": [];
  "preview-version": [sheetKey: string, versionId: string];
  "preview-image": [url: string, caption: string];
  summary: [sheet: WorkflowCharacterSheet];
  generate: [sheet: WorkflowCharacterSheet];
  "select-asset": [sheet: WorkflowCharacterSheet, assetId: string];
}>();

const {
  characterAssetPicker,
  materialAssetPreviewUrl,
  materialAssetModelLabel,
  isCharacterAssetPickerOpen,
  openCharacterAssetPicker,
  closeCharacterAssetPicker,
  loadCharacterAssetCandidates,
} = useCharacterAssetPicker();
const failedImageUrls = ref(new Set<string>());

function previewVersion(sheet: WorkflowCharacterSheet): StageVersion | null {
  const versions = characterSheetVersions(sheet);
  const previewId = props.previewVersionIds[characterSheetKey(sheet)] || "";
  return (
    versions.find((version) => version.id === previewId) ??
    versions.find((version) => version.selected) ??
    versions[0] ??
    null
  );
}

function isImageAvailable(url?: string | null) {
  return Boolean(url && !failedImageUrls.value.has(url));
}

function markImageFailed(url?: string | null) {
  if (url) failedImageUrls.value.add(url);
}
</script>

<style scoped src="./workflow-character-board.css"></style>
