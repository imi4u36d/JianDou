<template>
  <div class="home-composer__toolbar">
    <div class="home-menu home-menu-hidden" aria-hidden="true">
      <button
        type="button"
        class="home-tool"
        :class="{ 'home-tool-active': activeMenu === 'model' }"
        @click="emit('toggleMenu', 'model')"
      >
        <span class="home-tool__icon"><IconModel /></span>
        {{ selectedPrimaryModelLabel }}
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'model'" class="home-popover home-popover-model">
          <section class="home-popover-section">
            <p class="home-popover__label">文本模型</p>
            <button
              v-for="model in textModelOptions"
              :key="model.value"
              type="button"
              class="home-popover__item"
              :class="{ 'home-popover__item-active': textAnalysisModel === model.value }"
              @click="emit('selectTextModel', model.value)"
            >
              <span class="home-popover__icon"><IconText size="sm" /></span>
              <span
                ><strong>{{ model.label }}</strong></span
              >
              <span v-if="textAnalysisModel === model.value" class="home-popover__check" aria-hidden="true">
                <IconCheck size="sm" />
              </span>
            </button>
          </section>
          <section class="home-popover-section">
            <p class="home-popover__label">图片模型</p>
            <button
              v-for="model in imageModelOptions"
              :key="model.value"
              type="button"
              class="home-popover__item"
              :class="{ 'home-popover__item-active': imageModel === model.value }"
              @click="emit('selectImageModel', model.value)"
            >
              <span class="home-popover__icon"><IconImage size="sm" /></span>
              <span
                ><strong>{{ model.label }}</strong></span
              >
              <span v-if="imageModel === model.value" class="home-popover__check" aria-hidden="true">
                <IconCheck size="sm" />
              </span>
            </button>
          </section>
        </div>
      </transition>
    </div>

    <div class="home-menu">
      <button
        type="button"
        class="home-tool home-tool-plain"
        :class="{ 'home-tool-active': activeMenu === 'mode' }"
        @click="emit('toggleMenu', 'mode')"
      >
        <span class="home-tool__icon">
          <IconVideo v-if="selectedMode.kind === 'video'" />
          <IconImage v-else />
        </span>
        {{ selectedMode.label }}
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'mode'" class="home-popover home-popover-mode">
          <p class="home-popover__label">类型</p>
          <button
            v-for="mode in modeOptions"
            :key="mode.value"
            type="button"
            class="home-popover__item"
            :class="{ 'home-popover__item-active': selectedModeValue === mode.value }"
            @click="emit('selectMode', mode.value)"
          >
            <span class="home-popover__icon">
              <IconVideo v-if="mode.kind === 'video'" size="sm" />
              <IconImage v-else size="sm" />
            </span>
            <span
              ><strong>{{ mode.label }}</strong></span
            >
            <span v-if="selectedModeValue === mode.value" class="home-popover__check" aria-hidden="true">
              <IconCheck size="sm" />
            </span>
          </button>
        </div>
      </transition>
    </div>

    <div class="home-menu">
      <button
        type="button"
        class="home-tool home-tool-plain"
        :class="{ 'home-tool-active': activeMenu === 'ratio' }"
        @click="emit('toggleMenu', 'ratio')"
      >
        <span class="home-tool__shape"></span>
        {{ ratioToolLabel }}
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'ratio'" class="home-popover home-popover-ratio">
          <section class="home-popover-section">
            <p class="home-popover__label">比例</p>
            <div class="home-ratio-list home-ratio-list-immersive">
              <button
                v-for="ratio in ratioOptions"
                :key="ratio.value"
                type="button"
                :class="{ 'home-ratio-active': aspectRatio === ratio.value }"
                @click="emit('selectRatio', ratio.value)"
              >
                <span class="home-ratio__shape" :style="{ aspectRatio: ratio.shape }"></span>
                <span>{{ ratio.shortLabel }}</span>
              </button>
            </div>
          </section>
        </div>
      </transition>
    </div>

    <Transition name="home-template-chip-pop">
      <span
        v-if="selectedPromptTemplate"
        :key="`${selectedPromptTemplate.id}-${templateChipNonce}`"
        class="home-template-chip"
        tabindex="0"
        :aria-label="`已使用${selectedPromptTemplate.title}`"
      >
        <span class="home-template-chip__shine" aria-hidden="true"></span>
        <IconCheck size="xs" />
        <span>已使用{{ selectedPromptTemplate.title }}</span>
        <span class="home-template-chip__tooltip" role="tooltip">{{ selectedPromptTemplate.prompt }}</span>
      </span>
    </Transition>

    <div class="home-menu home-menu-hidden" aria-hidden="true">
      <button
        type="button"
        class="home-tool"
        :class="{ 'home-tool-active': activeMenu === 'count' }"
        @click="emit('toggleMenu', 'count')"
      >
        <span class="home-tool__icon"><IconFrame /></span>
        {{ `${imageOutputCount} / 张` }}
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'count'" class="home-popover home-popover-compact">
          <p class="home-popover__label">张数</p>
          <div class="home-segment-grid">
            <button
              v-for="count in imageOutputCountOptions"
              :key="count"
              type="button"
              :class="{ 'home-segment-active': imageOutputCount === count }"
              @click="emit('selectOutputCount', count)"
            >
              {{ count }} 张
            </button>
          </div>
        </div>
      </transition>
    </div>

    <div v-if="selectedMode.kind === 'image'" class="home-menu">
      <button
        type="button"
        class="home-tool home-tool-mention"
        :class="{ 'home-tool-active': activeMenu === 'mention' }"
        @click="emit('toggleMenu', 'mention')"
      >
        <span class="home-tool__icon">@</span>
        引用
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'mention'" class="home-popover home-popover-mention">
          <p class="home-popover__label">引用</p>
          <button
            v-if="!referenceImages.length"
            type="button"
            class="home-popover__item home-popover__item-empty"
            :disabled="uploadingReference"
            @click="emit('openReference')"
          >
            <span class="home-popover__icon"><IconImage size="sm" /></span>
            <span><strong>上传一张图片来作为参考图</strong></span>
          </button>
          <button
            v-for="item in referenceImages"
            :key="item.id"
            type="button"
            class="home-popover__item home-popover__item-reference"
            @click="emit('insertMention', item.label)"
          >
            <span class="home-popover__image"><img :src="item.fileUrl" :alt="item.label" /></span>
            <span
              ><strong>{{ item.label }}</strong></span
            >
          </button>
        </div>
      </transition>
    </div>

    <div class="home-menu home-menu-hidden" aria-hidden="true">
      <button
        type="button"
        class="home-tool"
        :class="{ 'home-tool-active': activeMenu === 'seed' }"
        @click="emit('toggleMenu', 'seed')"
      >
        <span class="home-tool__icon"><IconTag /></span>
        {{ seedMode === "auto" ? "自动" : "手动" }}
      </button>
      <transition name="home-popover-float">
        <div v-if="activeMenu === 'seed'" class="home-popover home-popover-seed">
          <p class="home-popover__label">种子</p>
          <div class="home-segment-grid">
            <button
              type="button"
              :class="{ 'home-segment-active': seedMode === 'auto' }"
              @click="emit('selectSeedMode', 'auto')"
            >
              自动
            </button>
            <button
              type="button"
              :class="{ 'home-segment-active': seedMode === 'manual' }"
              @click="emit('selectSeedMode', 'manual')"
            >
              手动
            </button>
          </div>
          <label v-if="seedMode === 'manual'" class="home-field">
            <span>种子值</span>
            <input
              :value="seedInput"
              inputmode="numeric"
              placeholder="非负整数"
              @input="emit('updateSeedInput', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <div v-else class="home-seed-row">
            <span>{{ autoSeed }}</span>
            <button type="button" @click="emit('refreshAutoSeed')">换</button>
          </div>
          <small>{{ seedCapabilityHint }}</small>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GenerationTextAnalysisModelInfo } from "@/types";
import type { ModeOption, RatioOptionValue } from "@/composables/home/useGenerationForm";
import type { ReferenceImageItem } from "@/composables/home/useReferenceImages";
import type { AppliedPromptTemplate } from "@/features/home/home-submission";
import { IconCheck, IconFrame, IconImage, IconModel, IconTag, IconText, IconVideo } from "@/components/icons";

export type HomeComposerMenuKey = "" | "model" | "mode" | "ratio" | "count" | "mention" | "seed";

interface RatioOption {
  value: RatioOptionValue;
  shortLabel: string;
  shape: string;
}

defineProps<{
  activeMenu: HomeComposerMenuKey;
  selectedMode: ModeOption;
  selectedModeValue: ModeOption["value"];
  modeOptions: ModeOption[];
  selectedPrimaryModelLabel: string;
  textModelOptions: GenerationTextAnalysisModelInfo[];
  imageModelOptions: GenerationTextAnalysisModelInfo[];
  textAnalysisModel?: string | null;
  imageModel?: string | null;
  ratioToolLabel: string;
  aspectRatio: RatioOptionValue;
  ratioOptions: RatioOption[];
  selectedPromptTemplate: AppliedPromptTemplate | null;
  templateChipNonce: number;
  imageOutputCount: number;
  imageOutputCountOptions: number[];
  referenceImages: ReferenceImageItem[];
  uploadingReference: boolean;
  seedMode: "auto" | "manual";
  seedInput: string;
  autoSeed: number;
  seedCapabilityHint: string;
}>();

const emit = defineEmits<{
  toggleMenu: [menu: Exclude<HomeComposerMenuKey, "">];
  selectMode: [mode: ModeOption["value"]];
  selectRatio: [ratio: RatioOptionValue];
  selectTextModel: [model: string];
  selectImageModel: [model: string];
  selectOutputCount: [count: number];
  openReference: [];
  insertMention: [label: string];
  selectSeedMode: [mode: "auto" | "manual"];
  updateSeedInput: [value: string];
  refreshAutoSeed: [];
}>();
</script>

<style scoped src="./home-composer-toolbar.css"></style>
