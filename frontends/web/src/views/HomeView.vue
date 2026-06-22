<template>
  <main class="home-page">
    <section class="home-hero">
      <h1>
        今天先做一个
        <button type="button" class="hero-mode-button" @click="toggleMenu('mode')">
          {{ selectedMode.label }}
        </button>
        项目
      </h1>

      <form class="home-composer" @submit.prevent="submitComposer">
        <button
          type="button"
          class="home-composer__upload"
          :class="{
            'home-composer__upload-has-reference': selectedMode.kind === 'image' && referenceImages.length > 0,
            'home-composer__upload-has-multiple': selectedMode.kind === 'image' && referenceImages.length > 1,
            'home-composer__upload-expanded': selectedMode.kind === 'image' && referenceImages.length > 0 && referenceExpanded,
          }"
          :disabled="uploadingReference"
          @pointerenter="handleReferenceUploadPointerEnter"
          @pointerleave="handleReferenceUploadPointerLeave"
          @click="handleReferenceEntryClick"
        >
          <template v-if="selectedMode.kind === 'image' && referenceImages.length">
            <span class="home-composer__upload-scene" :style="referenceUploadSceneStyle()" aria-hidden="true">
              <span class="home-composer__upload-preview">
                <span
                  v-for="(item, index) in referenceImages"
                  :key="item.id"
                  class="home-composer__upload-preview-image"
                  :style="referencePreviewImageStyle(index)"
                  @click.stop
                >
                  <img :src="item.fileUrl" :alt="item.label" />
                  <button
                    type="button"
                    class="home-composer__upload-preview-image-remove"
                    :aria-label="`移除${item.label}`"
                    @click.stop="removeReferenceImage(item.id)"
                  >
                    <IconClose size="xs" />
                  </button>
                </span>
              </span>
              <span class="home-composer__upload-add-card" :style="referenceAddCardStyle()">
                <IconPlus size="sm" />
              </span>
              <span class="home-reference-add"><IconPlus size="xs" /></span>
            </span>
          </template>
          <IconPlus v-else size="md" />
        </button>
        <input
          ref="textFileInput"
          type="file"
          :accept="selectedMode.kind === 'image' ? 'image/*' : '.txt,text/plain'"
          class="home-hidden-input"
          :multiple="selectedMode.kind === 'image'"
          @change="handleReferenceFileChange"
        />

        <div class="home-composer__body">
          <label class="home-composer__prompt">
            <div v-if="showPromptPlaceholder" class="home-composer__placeholder" aria-hidden="true">
              <span>输入想法、剧本或参考图，</span>
              <span class="home-composer__placeholder-tag">@</span>
              <span> 添加主体</span>
            </div>
            <div
              ref="promptEditor"
              class="home-composer__editor"
              contenteditable="true"
              role="textbox"
              :aria-label="promptLabel"
              aria-multiline="true"
              spellcheck="false"
              @focus="handlePromptEditorFocus"
              @blur="handlePromptEditorBlur"
              @compositionstart="handlePromptEditorCompositionStart"
              @compositionend="handlePromptEditorCompositionEnd"
              @beforeinput="handlePromptEditorBeforeInput"
              @input="handlePromptEditorInput"
              @keydown="handlePromptEditorKeydown"
              @paste="handlePromptEditorPaste"
            ></div>
          </label>
        </div>

        <div class="home-composer__footer">
          <div class="home-composer__toolbar">
            <div class="home-menu">
              <button type="button" class="home-tool home-tool-accent" :class="{ 'home-tool-active': activeMenu === 'mode' }" @click="toggleMenu('mode')">
                <span class="home-tool__icon"><IconVideo v-if="selectedMode.iconName === 'video'" /><IconImage v-else-if="selectedMode.iconName === 'image'" /><IconCharacter v-else /></span>
                {{ selectedMode.label }}
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'mode'" class="home-popover home-popover-mode">
                  <p class="home-popover__label">创作类型</p>
                  <button
                    v-for="option in modeOptions"
                    :key="option.value"
                    type="button"
                    class="home-popover__item"
                    :class="{ 'home-popover__item-active': selectedModeValue === option.value }"
                    @click="selectMode(option.value)"
                  >
                    <span class="home-popover__icon"><IconVideo v-if="option.iconName === 'video'" /><IconImage v-else-if="option.iconName === 'image'" /><IconCharacter v-else /></span>
                    <span>
                      <strong>{{ option.label }}</strong>
                    </span>
                    <span v-if="selectedModeValue === option.value" class="home-popover__check" aria-hidden="true">
                      <IconCheck size="sm" />
                    </span>
                  </button>
                </div>
              </transition>
            </div>

            <div class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'model' }" @click="toggleMenu('model')">
                <span class="home-tool__icon"><IconModel /></span>
                {{ selectedPrimaryModelLabel }}
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'model'" class="home-popover home-popover-model">
                  <template v-if="selectedMode.kind === 'video'">
                    <section class="home-popover-section">
                      <p class="home-popover__label">文本模型</p>
                      <button
                        v-for="model in textModelOptions"
                        :key="model.value"
                        type="button"
                        class="home-popover__item"
                        :class="{ 'home-popover__item-active': form.textAnalysisModel === model.value }"
                        @click="form.textAnalysisModel = model.value"
                      >
                        <span class="home-popover__icon"><IconText size="sm" /></span>
                        <span>
                          <strong>{{ model.label }}</strong>
                        </span>
                        <span v-if="form.textAnalysisModel === model.value" class="home-popover__check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none">
                            <path d="M4.5 10.5 8.2 14.2 15.5 5.8" />
                          </svg>
                        </span>
                      </button>
                    </section>
                    <section class="home-popover-section">
                      <p class="home-popover__label">关键帧模型</p>
                      <button
                        v-for="model in imageModelOptions"
                        :key="model.value"
                        type="button"
                        class="home-popover__item"
                        :class="{ 'home-popover__item-active': form.imageModel === model.value }"
                        @click="form.imageModel = model.value"
                      >
                        <span class="home-popover__icon"><IconFrame size="sm" /></span>
                        <span>
                          <strong>{{ model.label }}</strong>
                        </span>
                        <span v-if="form.imageModel === model.value" class="home-popover__check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none">
                            <path d="M4.5 10.5 8.2 14.2 15.5 5.8" />
                          </svg>
                        </span>
                      </button>
                    </section>
                    <section class="home-popover-section">
                      <p class="home-popover__label">视频模型</p>
                      <button
                        v-for="model in videoModelOptions"
                        :key="model.value"
                        type="button"
                        class="home-popover__item"
                        :class="{ 'home-popover__item-active': form.videoModel === model.value }"
                        @click="form.videoModel = model.value"
                      >
                        <span class="home-popover__icon"><IconVideo size="sm" /></span>
                        <span>
                          <strong>{{ model.label }}</strong>
                        </span>
                        <span v-if="form.videoModel === model.value" class="home-popover__check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none">
                            <path d="M4.5 10.5 8.2 14.2 15.5 5.8" />
                          </svg>
                        </span>
                      </button>
                    </section>
                  </template>
                  <template v-else>
                    <section class="home-popover-section">
                      <p class="home-popover__label">文本模型</p>
                      <button
                        v-for="model in textModelOptions"
                        :key="model.value"
                        type="button"
                        class="home-popover__item"
                        :class="{ 'home-popover__item-active': form.textAnalysisModel === model.value }"
                        @click="form.textAnalysisModel = model.value"
                      >
                        <span class="home-popover__icon"><IconText size="sm" /></span>
                        <span>
                          <strong>{{ model.label }}</strong>
                        </span>
                        <span v-if="form.textAnalysisModel === model.value" class="home-popover__check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none">
                            <path d="M4.5 10.5 8.2 14.2 15.5 5.8" />
                          </svg>
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
                        :class="{ 'home-popover__item-active': form.imageModel === model.value }"
                        @click="form.imageModel = model.value"
                      >
                        <span class="home-popover__icon"><IconImage size="sm" /></span>
                        <span>
                          <strong>{{ model.label }}</strong>
                        </span>
                        <span v-if="form.imageModel === model.value" class="home-popover__check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none">
                            <path d="M4.5 10.5 8.2 14.2 15.5 5.8" />
                          </svg>
                        </span>
                      </button>
                    </section>
                  </template>
                </div>
              </transition>
            </div>

            <div class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'ratio' }" @click="toggleMenu('ratio')">
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
                        :class="{ 'home-ratio-active': form.aspectRatio === ratio.value }"
                        @click="selectRatio(ratio.value)"
                      >
                        <span class="home-ratio__shape" :style="{ aspectRatio: ratio.shape }"></span>
                        <span>{{ ratio.shortLabel }}</span>
                      </button>
                    </div>
                  </section>
                  <template v-if="selectedMode.kind === 'image'">
                    <section class="home-popover-section">
                      <p class="home-popover__label">分辨率</p>
                      <div class="home-resolution-list">
                        <button
                          v-for="size in imageSizeOptions"
                          :key="size.value"
                          type="button"
                          :class="{ 'home-resolution-active': form.imageSize === size.value }"
                          @click="form.imageSize = size.value"
                        >
                          {{ formatImageSizeOptionLabel(size) }}
                        </button>
                      </div>
                    </section>
                    <section v-if="selectedImageSizeDimensions" class="home-popover-section">
                      <p class="home-popover__label">尺寸</p>
                      <div class="home-dimension-row">
                        <strong data-label="W">{{ selectedImageSizeDimensions.width }}</strong>
                        <span class="home-dimension-link">⌁</span>
                        <strong data-label="H">{{ selectedImageSizeDimensions.height }}</strong>
                        <span>PX</span>
                      </div>
                    </section>
                  </template>
                  <template v-else>
                    <section class="home-popover-section">
                      <p class="home-popover__label">视频尺寸</p>
                      <div class="home-resolution-list">
                        <button
                          v-for="size in videoSizeOptions"
                          :key="size.value"
                          type="button"
                          :class="{ 'home-resolution-active': form.videoSize === size.value }"
                          @click="form.videoSize = size.value"
                        >
                          {{ formatVideoSizeLabel(size.label || size.value) }}
                        </button>
                      </div>
                    </section>
                    <section v-if="selectedVideoSizeDimensions" class="home-popover-section">
                      <p class="home-popover__label">尺寸</p>
                      <div class="home-dimension-row">
                        <strong data-label="W">{{ selectedVideoSizeDimensions.width }}</strong>
                        <span class="home-dimension-link">⌁</span>
                        <strong data-label="H">{{ selectedVideoSizeDimensions.height }}</strong>
                        <span>PX</span>
                      </div>
                    </section>
                  </template>
                </div>
              </transition>
            </div>

            <div v-if="selectedMode.kind === 'video'" class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'duration' }" @click="toggleMenu('duration')">
                <span class="home-tool__icon"><IconDuration /></span>
                {{ durationLabel }}
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'duration'" class="home-popover home-popover-compact">
                  <p class="home-popover__label">时长</p>
                  <div class="home-segment-grid">
                    <button type="button" :class="{ 'home-segment-active': durationMode === 'auto' }" @click="durationMode = 'auto'">自动</button>
                    <button
                      v-for="duration in durationOptions"
                      :key="duration.value"
                      type="button"
                      :class="{ 'home-segment-active': durationMode === 'manual' && selectedDurationSeconds === duration.value }"
                      @click="selectDuration(duration.value)"
                    >
                      {{ duration.value }}s
                    </button>
                  </div>
                </div>
              </transition>
            </div>

            <div v-if="selectedModeValue !== 'character_sheet'" class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'count' }" @click="toggleMenu('count')">
                <span class="home-tool__icon"><IconFrame /></span>
                {{ selectedMode.kind === "image" ? `${imageOutputCount} / 张` : outputCountLabel }}
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'count'" class="home-popover home-popover-compact">
                  <p class="home-popover__label">{{ selectedMode.kind === "image" ? "张数" : "分镜" }}</p>
                  <div class="home-segment-grid">
                    <template v-if="selectedMode.kind === 'image'">
                      <button
                        v-for="count in imageOutputCountOptions"
                        :key="count"
                        type="button"
                        :class="{ 'home-segment-active': imageOutputCount === count }"
                        @click="imageOutputCount = count"
                      >
                        {{ count }} 张
                      </button>
                    </template>
                    <template v-else>
                      <button type="button" :class="{ 'home-segment-active': form.outputCount === 'auto' }" @click="form.outputCount = 'auto'">自动</button>
                      <button
                        v-for="count in videoOutputCountOptions"
                        :key="count"
                        type="button"
                        :class="{ 'home-segment-active': form.outputCount === count }"
                        @click="form.outputCount = count"
                      >
                        {{ count }}
                      </button>
                    </template>
                  </div>
                </div>
              </transition>
            </div>

            <div class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'mention' }" @click="toggleMenu('mention')">
                <span class="home-tool__icon">@</span>
                引用
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'mention'" class="home-popover home-popover-mention">
                  <p class="home-popover__label">引用</p>
                  <button type="button" class="home-popover__item" @click="insertMention('创建主体')">
                    <span class="home-popover__icon"><IconPlus size="sm" /></span>
                    <span>
                      <strong>创建主体</strong>
                    </span>
                  </button>
                  <template v-if="selectedMode.kind === 'image'">
                    <button
                      v-for="item in referenceImages"
                      :key="item.id"
                      type="button"
                      class="home-popover__item"
                      @click="insertMention(item.label)"
                    >
                      <span class="home-popover__image">
                        <img :src="item.fileUrl" :alt="item.label" />
                      </span>
                      <span>
                        <strong>{{ item.label }}</strong>
                      </span>
                    </button>
                  </template>
                </div>
              </transition>
            </div>

            <div class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'seed' }" @click="toggleMenu('seed')">
                <span class="home-tool__icon"><IconTag /></span>
                {{ seedMode === "auto" ? "自动" : "手动" }}
              </button>
              <transition name="home-popover-float">
                <div v-if="activeMenu === 'seed'" class="home-popover home-popover-seed">
                  <p class="home-popover__label">种子</p>
                  <div class="home-segment-grid">
                    <button type="button" :class="{ 'home-segment-active': seedMode === 'auto' }" @click="seedMode = 'auto'">自动</button>
                    <button type="button" :class="{ 'home-segment-active': seedMode === 'manual' }" @click="seedMode = 'manual'">手动</button>
                  </div>
                  <label v-if="seedMode === 'manual'" class="home-field">
                    <span>种子值</span>
                    <input v-model="seedInput" inputmode="numeric" placeholder="非负整数" />
                  </label>
                  <div v-else class="home-seed-row">
                    <span>{{ autoSeed }}</span>
                    <button type="button" @click="refreshAutoSeed">换</button>
                  </div>
                  <small>{{ seedCapabilityHint }}</small>
                </div>
              </transition>
            </div>
          </div>

          <div class="home-composer__meta">
            <span v-if="creditLabel" class="home-credit-pill" :class="{ 'home-credit-pill-exempt': credits?.exempt }">
              {{ creditLabel }}
            </span>
            <RouterLink v-if="createdTaskId" :to="{ name: 'tasks', query: { selected: createdTaskId } }">查看</RouterLink>
          </div>
        </div>

        <button class="home-composer__submit" type="submit" :disabled="submitting || loadingOptions || !isFormReady" :title="submitLabel">
          <svg v-if="!submitting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 19V5" />
            <path d="m5 12 7-7 7 7" />
          </svg>
          <IconLoading v-else size="sm" />
        </button>
      </form>

    </section>

    <Transition name="home-toast-slide">
      <div v-if="taskToastTaskId" class="home-task-toast" role="status">
        <span>已提交</span>
        <RouterLink :to="{ name: 'tasks', query: { selected: taskToastTaskId } }">查看</RouterLink>
        <button type="button" aria-label="关闭任务提示" @click="dismissTaskToast">
          <IconClose size="xs" />
        </button>
      </div>
    </Transition>

    <section v-if="activeTasks.length" class="home-active-tasks" aria-label="进行中的任务">
      <RouterLink
        v-for="task in activeTasks"
        :key="task.id"
        class="home-active-task-card"
        :to="{ name: 'tasks', query: { selected: task.id } }"
      >
        <div class="home-active-task-card__top">
          <span class="home-active-task-card__type">{{ task.aspectRatio || "生成任务" }}</span>
          <span class="home-active-task-card__status">{{ formatTaskStatus(task.status) }}</span>
        </div>
        <h2>{{ task.title }}</h2>
        <p>{{ activeTaskStageLabel(task) }}</p>
        <div class="home-active-task-card__progress" aria-hidden="true">
          <span :style="{ width: `${activeTaskProgress(task)}%` }"></span>
        </div>
        <div class="home-active-task-card__meta">
          <span>{{ activeTaskProgress(task) }}%</span>
          <span>{{ formatActiveTaskTime(task.updatedAt || task.createdAt) }}</span>
        </div>
      </RouterLink>
    </section>

  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { requireAuth } from "@/auth/modal";
import { useAuthSessionState } from "@/auth/session";
import { createGenerationTask } from "@/features/home";
import { formatApiErrorMessage } from "@/utils/api-error";
import { formatVideoSizeLabel } from "@/utils/presentation";
import { formatTaskStatus } from "@/utils/task";
import { shouldStopBeforeVideoGeneration } from "@/workbench/developer-settings";
import type { CreateGenerationTaskRequest } from "@/types";

import { usePromptEditor } from "@/composables/home/usePromptEditor";
import { useReferenceImages, type ReferenceImageItem } from "@/composables/home/useReferenceImages";
import { useGenerationForm, type ModeValue, type RatioOptionValue } from "@/composables/home/useGenerationForm";
import { useActiveTasks } from "@/composables/home/useActiveTasks";
import { IconCheck, IconClose, IconVideo, IconImage, IconCharacter, IconModel, IconDuration, IconFrame, IconTag, IconPlus, IconText } from "@/components/icons";

type MenuKey = "" | "mode" | "model" | "ratio" | "duration" | "count" | "mention" | "seed";

// ---------------------------------------------------------------------------
// Local state (not extracted to composables)
// ---------------------------------------------------------------------------

const authState = useAuthSessionState();
const activeMenu = ref<MenuKey>("");
const statusText = ref("加载参数");
const submitting = ref(false);
const createdTaskId = ref("");
const taskToastTaskId = ref("");
let taskToastTimer: number | null = null;

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------

// usePromptEditor needs referenceImages (returned by useReferenceImages).
// useReferenceImages needs renderPromptEditor / focusPromptEditorToEnd (returned by usePromptEditor).
// Break the circular dependency with a bridge ref that is synced after both are initialized.
const referenceImagesBridge = ref<ReferenceImageItem[]>([]);

const {
  promptEditor,
  promptText,
  composingPrompt,
  syncingPromptFromEditor,
  promptEditorFocused,
  showPromptPlaceholder,
  renderPromptEditor,
  focusPromptEditorToEnd,
  handlePromptEditorInput,
  handlePromptEditorFocus,
  handlePromptEditorBlur,
  handlePromptEditorCompositionStart,
  handlePromptEditorCompositionEnd,
  handlePromptEditorBeforeInput,
  handlePromptEditorKeydown,
  handlePromptEditorPaste,
} = usePromptEditor(referenceImagesBridge);

const {
  form,
  selectedModeValue,
  selectedMode,
  seedMode,
  seedInput,
  autoSeed,
  durationMode,
  selectedDurationSeconds,
  imageOutputCount,
  options,
  loadingOptions,
  credits,
  promptLabel,
  textModelOptions,
  imageModelOptions,
  videoModelOptions,
  selectedImageModelOption,
  selectedVideoModelOption,
  selectedPrimaryModelLabel,
  creditLabel,
  ratioOptions,
  availableImageRatios,
  imageSizeOptions,
  videoSizeOptions,
  durationOptions,
  durationLabel,
  outputCountLabel,
  selectedImageSizeOption,
  selectedImageSizeDimensions,
  selectedVideoSizeOption,
  selectedVideoSizeDimensions,
  selectedMaterialAssetType,
  ratioToolLabel,
  parsedManualSeed,
  seedCapabilityHint,
  isSeedReady,
  isFormReady,
  modeOptions,
  videoOutputCountOptions,
  imageOutputCountOptions,
  modelOptionDescription,
  refreshAutoSeed,
  formatImageSizeOptionLabel,
  resolvedImageAspectRatioForSubmit,
  loadOptions,
  loadCredits,
  videoAspectRatio,
} = useGenerationForm({ promptText });

const {
  referenceImages,
  uploadingReference,
  referenceExpanded,
  textFileInput,
  handleReferenceEntryClick,
  handleReferenceUploadPointerEnter,
  handleReferenceUploadPointerLeave,
  referenceUploadSceneStyle,
  referencePreviewImageStyle,
  referenceAddCardStyle,
  handleReferenceFileChange,
  removeReferenceImage,
  insertMention,
} = useReferenceImages({
  selectedMode: selectedMode as any,
  statusText,
  promptText,
  form,
  activeMenu,
  renderPromptEditor,
  focusPromptEditorToEnd,
});

const {
  activeTasks,
  activeTaskStageLabel,
  activeTaskProgress,
  formatActiveTaskTime,
  loadActiveTasks,
} = useActiveTasks();

// Sync referenceImages from useReferenceImages -> bridge ref used by usePromptEditor
watch(referenceImages, (val) => {
  referenceImagesBridge.value = val;
}, { immediate: true });

// ---------------------------------------------------------------------------
// submitLabel (overrides composable version to include submitting state)
// ---------------------------------------------------------------------------

const submitLabel = computed(() => {
  if (submitting.value) {
    return "创建中";
  }
  return selectedMode.value.kind === "video" ? "生成视频" : selectedMode.value.value === "character_sheet" ? "生成三视图" : "生成图片";
});

// ---------------------------------------------------------------------------
// Menu toggle logic (not extracted)
// ---------------------------------------------------------------------------

function toggleMenu(menu: Exclude<MenuKey, "">) {
  activeMenu.value = activeMenu.value === menu ? "" : menu;
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!activeMenu.value) {
    return;
  }
  const target = event.target instanceof Element ? event.target : null;
  if (target?.closest(".home-menu, .hero-mode-button")) {
    return;
  }
  activeMenu.value = "";
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    activeMenu.value = "";
  }
}

function selectMode(value: ModeValue) {
  selectedModeValue.value = value;
  activeMenu.value = "";
  if (value === "character_sheet" && availableImageRatios.value.includes("1:1")) {
    form.value.aspectRatio = "1:1";
  } else if (value === "video" && form.value.aspectRatio !== "16:9" && form.value.aspectRatio !== "9:16") {
    form.value.aspectRatio = "16:9";
  }
  statusText.value = value === "video"
    ? "视频生成会创建工作台视频任务。"
    : value === "character_sheet"
      ? "角色三视图会生成到素材库，可在阶段工作流中选择。"
      : "图片生成会使用素材中心自由模式。";
}

function selectRatio(value: RatioOptionValue) {
  form.value.aspectRatio = value;
}

function selectDuration(value: number) {
  durationMode.value = "manual";
  selectedDurationSeconds.value = value;
}

// ---------------------------------------------------------------------------
// Form submission logic (not extracted)
// ---------------------------------------------------------------------------

async function submitComposer() {
  if (!isFormReady.value) {
    statusText.value = "请先输入内容并补全参数。";
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后开始生成",
    message: "生成结果会保存到你的任务和素材库中，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    statusText.value = "登录后即可继续生成。";
    return;
  }
  submitting.value = true;
  createdTaskId.value = "";
  try {
    if (selectedMode.value.kind === "image") {
      await submitImageGeneration();
    } else {
      await submitVideoGeneration();
    }
  } catch (error) {
    statusText.value = formatApiErrorMessage(error, "创建失败");
  } finally {
    submitting.value = false;
  }
}

async function submitImageGeneration() {
  const isCharacterSheet = selectedMaterialAssetType.value === "character_sheet";
  const taskType = isCharacterSheet
    ? "character_sheet"
    : referenceImages.value.length
      ? "image_to_image"
      : "image_generation";
  const task = await createGenerationTask({
    title: promptText.value.trim().slice(0, 32) || (isCharacterSheet ? "角色三视图" : "图片生成"),
    taskType,
    assetType: selectedMaterialAssetType.value,
    creativePrompt: promptText.value.trim(),
    aspectRatio: resolvedImageAspectRatioForSubmit(),
    imageSize: form.value.imageSize || null,
    textAnalysisModel: form.value.textAnalysisModel || null,
    imageModel: form.value.imageModel || null,
    videoModel: null,
    videoSize: null,
    outputCount: 1,
    seed: selectedImageModelOption.value?.supportsSeed
      ? (seedMode.value === "manual" ? parsedManualSeed.value : autoSeed.value)
      : null,
    referenceImageUrls: referenceImages.value.map((item) => item.fileUrl),
    referenceAssetIds: [],
    transcriptText: "",
    stopBeforeVideoGeneration: false,
  });
  createdTaskId.value = task.id;
  showTaskToast(task.id);
  statusText.value = "已提交";
  void loadActiveTasks();
}

async function submitVideoGeneration() {
  const duration = durationMode.value === "manual" && selectedDurationSeconds.value ? selectedDurationSeconds.value : null;
  const payload: CreateGenerationTaskRequest = {
    title: promptText.value.trim().slice(0, 32) || "工作台视频生成",
    creativePrompt: "",
    aspectRatio: videoAspectRatio(form.value.aspectRatio),
    textAnalysisModel: form.value.textAnalysisModel || null,
    imageModel: form.value.imageModel || null,
    videoModel: form.value.videoModel || null,
    videoSize: form.value.videoSize || null,
    outputCount: form.value.outputCount ?? "auto",
    seed: seedMode.value === "manual" ? parsedManualSeed.value : autoSeed.value,
    videoDurationSeconds: "auto",
    minDurationSeconds: duration,
    maxDurationSeconds: duration,
    transcriptText: promptText.value.trim(),
    stopBeforeVideoGeneration: shouldStopBeforeVideoGeneration(),
  };
  const task = await createGenerationTask(payload);
  createdTaskId.value = task.id;
  showTaskToast(task.id);
  statusText.value = "已提交";
  void loadActiveTasks();
}

// ---------------------------------------------------------------------------
// Toast logic (not extracted)
// ---------------------------------------------------------------------------

function showTaskToast(taskId: string) {
  taskToastTaskId.value = taskId;
  if (taskToastTimer !== null) {
    window.clearTimeout(taskToastTimer);
  }
  taskToastTimer = window.setTimeout(() => {
    taskToastTaskId.value = "";
    taskToastTimer = null;
  }, 5000);
}

function dismissTaskToast() {
  taskToastTaskId.value = "";
  if (taskToastTimer !== null) {
    window.clearTimeout(taskToastTimer);
    taskToastTimer = null;
  }
}

// ---------------------------------------------------------------------------
// Lifecycle & watches
// ---------------------------------------------------------------------------

onMounted(() => {
  loadOptions()
    .then(() => { statusText.value = ""; })
    .catch((error) => { statusText.value = error instanceof Error ? error.message : "加载模型配置失败"; });
  loadCredits();
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleDocumentKeydown);
  renderPromptEditor(promptText.value);
});

watch(promptText, (value) => {
  if (composingPrompt.value || syncingPromptFromEditor.value) {
    return;
  }
  const editor = promptEditor.value;
  if (document.activeElement === editor) {
    return;
  }
  renderPromptEditor(value);
});

watch(referenceImages, () => {
  if (composingPrompt.value) {
    return;
  }
  renderPromptEditor(promptText.value);
}, { deep: true });

watch(() => authState.isAuthenticated.value, () => {
  loadCredits();
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleDocumentKeydown);
  dismissTaskToast();
});
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  min-height: 100%;
  padding: 32px 28px 48px;
  overflow-y: auto;
  background: var(--bg-base);
}
.home-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  width: 100%;
  max-width: 720px;
}
.home-hero h1 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 10px;
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.hero-mode-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border: 0;
  border-radius: 6px;
  background: var(--bg-accent-soft);
  color: var(--accent-indigo);
  font-size: inherit;
  font-weight: inherit;
  cursor: pointer;
  transition: background 120ms ease;
}
.hero-mode-button:hover {
  background: rgba(79, 70, 229, 0.12);
}
.home-composer {
  position: relative;
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-lg);
  padding: 20px 24px 16px;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
.home-composer:focus-within {
  border-color: var(--accent-indigo);
  box-shadow: var(--shadow-xl), 0 0 0 3px rgba(79, 70, 229, 0.1);
}
.home-composer__upload {
  position: absolute;
  left: 20px;
  top: 20px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border: 1.5px dashed var(--border-strong);
  border-radius: 10px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 120ms ease;
}
.home-composer__upload:hover {
  border-color: var(--accent-indigo);
  color: var(--accent-indigo);
  background: var(--bg-accent-soft);
}
.home-composer__upload-has-reference {
  border: 0;
  width: auto;
  height: auto;
  background: transparent;
  position: static;
}
.home-composer__body {
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 96px;
}
.home-composer__prompt {
  position: relative;
  display: block;
  min-height: 96px;
  outline: none;
}
.home-composer__placeholder {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  max-width: calc(100% - 120px);
  color: var(--text-muted);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.7;
  pointer-events: none;
}
.home-composer__placeholder-tag {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-muted);
  color: var(--accent-indigo);
  font-size: 14px;
  font-weight: 800;
}
.home-composer__editor {
  min-height: 96px;
  width: 100%;
  padding: 0 18px 0 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  caret-color: var(--text-primary);
}
.home-composer__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  margin-top: 10px;
}
.home-composer__toolbar {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 8px 0 0;
  border-top: 1px solid var(--border-subtle);
}
.home-tool {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 120ms ease;
}
.home-tool:hover { background: var(--bg-muted); color: var(--text-primary); }
.home-tool-accent { background: var(--bg-accent-soft); color: var(--accent-indigo); border-color: rgba(79,70,229,0.15); }
.home-tool-active { background: var(--bg-accent-soft); color: var(--accent-indigo); border-color: rgba(79,70,229,0.2); }
.home-tool__icon { display: inline-grid; place-items: center; width: 15px; height: 15px; }
.home-tool__icon :deep(svg) { width: 100%; height: 100%; }
.home-tool__shape { width: 14px; height: 14px; border: 2px solid currentColor; border-radius: 3px; }
.home-menu { position: relative; z-index: 1; }
.home-menu:has(.home-popover) { z-index: 40; }
.home-popover-float-enter-active, .home-popover-float-leave-active { transition: opacity 120ms ease, transform 160ms ease; }
.home-popover-float-enter-from, .home-popover-float-leave-to { opacity: 0; transform: translateY(4px) scale(0.98); }
.home-popover {
  position: absolute;
  left: 0;
  top: calc(100% + 6px);
  z-index: 12;
  display: grid;
  gap: 6px;
  width: min(300px, calc(100vw - 48px));
  max-height: min(440px, calc(100vh - 120px));
  overflow-y: auto;
  padding: 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-xl);
}
.home-popover-ratio { width: min(400px, calc(100vw - 48px)); }
.home-popover-model { width: min(280px, calc(100vw - 48px)); }
.home-popover-compact, .home-popover-seed { width: 220px; }
.home-popover-section { display: grid; gap: 6px; }
.home-popover-section + .home-popover-section { padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.home-popover__label { margin: 0 4px; color: var(--text-muted); font-size: 11px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.home-popover__item {
  display: grid; grid-template-columns: 28px minmax(0,1fr) 16px; align-items: center; gap: 8px;
  width: 100%; min-height: 38px; border: 1px solid transparent; padding: 0 8px; border-radius: 6px;
  background: transparent; color: var(--text-primary); text-align: left; cursor: pointer; transition: background 120ms ease;
}
.home-popover__item-active { border-color: rgba(79,70,229,0.2); background: var(--bg-accent-soft); color: var(--accent-indigo); }
.home-popover__item:hover { background: var(--bg-muted); }
.home-popover__icon { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 6px; background: var(--bg-muted); color: var(--text-secondary); }
.home-popover__item-active .home-popover__icon { background: rgba(79,70,229,0.12); color: var(--accent-indigo); }
.home-popover__item strong { display: block; min-width: 0; font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.home-popover__item small { display: block; margin-top: 1px; color: var(--text-muted); font-size: 11px; }
.home-popover__check { display: grid; place-items: center; width: 16px; height: 16px; color: var(--accent-indigo); }
.home-popover__check svg { stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.home-popover__empty { margin: 0; padding: 10px 12px; border-radius: 6px; background: var(--bg-muted); color: var(--text-muted); font-size: 12px; font-weight: 600; }
.home-segment-grid { display: grid; gap: 2px; padding: 3px; border-radius: 10px; background: var(--bg-muted); grid-template-columns: repeat(2,minmax(0,1fr)); }
.home-segment-grid button { min-height: 34px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--text-secondary); font-weight: 600; font-size: 12px; cursor: pointer; }
.home-segment-grid button:hover { background: var(--bg-surface); color: var(--text-primary); }
.home-segment-active { background: var(--bg-surface) !important; color: var(--accent-indigo) !important; box-shadow: var(--shadow-xs); }
.home-ratio-list { display: grid; gap: 4px; }
.home-ratio-list-immersive { grid-template-columns: repeat(auto-fit,minmax(56px,1fr)); gap: 3px; padding: 3px; border-radius: 10px; background: var(--bg-muted); }
.home-ratio-list button { display: grid; justify-items: center; align-content: center; gap: 4px; min-height: 56px; border: 0; border-radius: 6px; background: transparent; color: var(--text-primary); font-size: 10px; font-weight: 600; cursor: pointer; }
.home-ratio-active { background: var(--bg-surface) !important; color: var(--accent-indigo) !important; box-shadow: var(--shadow-xs); }
.home-ratio__shape { width: 16px; max-height: 16px; min-height: 6px; border: 1.5px solid currentColor; border-radius: 3px; }
.home-resolution-list { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 2px; padding: 3px; border-radius: 10px; background: var(--bg-muted); }
.home-resolution-list button { min-height: 38px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--text-primary); font-size: 12px; font-weight: 600; cursor: pointer; }
.home-resolution-active { background: var(--bg-surface) !important; color: var(--accent-indigo) !important; box-shadow: var(--shadow-xs); }
.home-dimension-row { display: grid; grid-template-columns: minmax(0,1fr) 36px minmax(0,1fr) 48px; align-items: center; gap: 6px; }
.home-dimension-row span, .home-dimension-row strong { min-height: 38px; display: grid; align-items: center; border-radius: 6px; background: var(--bg-muted); }
.home-dimension-row span { justify-items: center; color: var(--text-muted); font-size: 11px; font-weight: 600; }
.home-dimension-row strong { grid-template-columns: 36px minmax(0,1fr); justify-items: stretch; padding: 0 10px; color: var(--text-primary); font-size: 13px; font-weight: 600; }
.home-dimension-row strong::before { content: attr(data-label); color: var(--text-muted); font-size: 11px; font-weight: 700; }
.home-dimension-row .home-dimension-link { background: transparent; color: var(--text-muted); font-size: 16px; }
.home-seed-row { display: flex; align-items: center; gap: 10px; justify-content: space-between; min-height: 38px; padding: 0 10px; border-radius: 6px; background: var(--bg-muted); font-weight: 700; }
.home-seed-row button { min-height: 34px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--accent-indigo); font-weight: 700; cursor: pointer; }
.home-composer__meta { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; min-height: 34px; max-width: 320px; color: var(--text-muted); font-size: 12px; justify-content: flex-end; text-align: right; }
.home-composer__meta a { color: var(--accent-indigo); font-weight: 700; }
.home-credit-pill { display: inline-flex; align-items: center; min-height: 26px; padding: 0 10px; border: 1px solid var(--border-subtle); border-radius: 999px; background: var(--bg-surface); color: var(--text-primary); font-size: 11px; font-weight: 700; white-space: nowrap; }
.home-credit-pill-exempt { border-color: rgba(16,185,129,0.2); background: rgba(16,185,129,0.06); color: var(--accent-emerald); }
.home-composer__submit {
  position: absolute; right: 18px; bottom: 18px; display: grid; place-items: center;
  width: 36px; height: 36px; border: 0; border-radius: 50%;
  background: var(--accent-indigo); color: #fff;
  box-shadow: 0 4px 12px rgba(79,70,229,0.3); cursor: pointer;
}
.home-composer__submit:disabled { cursor: not-allowed; opacity: 0.4; }
.home-composer__submit svg { width: 16px; height: 16px; }
.home-active-tasks { display: flex; align-items: stretch; gap: 12px; width: min(100%,1120px); margin: 0 auto; overflow-x: auto; padding: 2px 2px 10px; }
.home-active-task-card {
  flex: 0 0 280px; display: grid; gap: 10px; min-height: 160px; padding: 16px;
  border: 1px solid var(--border-subtle); border-radius: 14px; background: var(--bg-surface);
  color: var(--text-primary); text-decoration: none; box-shadow: var(--shadow-xs);
  transition: border-color 200ms ease, box-shadow 200ms ease, transform 200ms ease;
}
.home-active-task-card:hover { transform: translateY(-2px); border-color: var(--border-default); box-shadow: var(--shadow-md); }
.home-active-task-card__top, .home-active-task-card__meta { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }
.home-active-task-card__type, .home-active-task-card__status { display: inline-flex; align-items: center; min-height: 24px; padding: 0 8px; border-radius: 999px; font-size: 10px; font-weight: 700; line-height: 1; white-space: nowrap; }
.home-active-task-card__type { background: var(--bg-muted); color: var(--text-muted); }
.home-active-task-card__status { background: var(--bg-accent-soft); color: var(--accent-indigo); }
.home-active-task-card h2 { display: -webkit-box; min-height: 40px; margin: 0; overflow: hidden; color: var(--text-primary); font-size: 14px; font-weight: 700; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.home-active-task-card p { min-width: 0; margin: 0; overflow: hidden; color: var(--text-muted); font-size: 12px; font-weight: 600; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.home-active-task-card__progress { height: 4px; overflow: hidden; border-radius: 999px; background: var(--bg-muted); }
.home-active-task-card__progress span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue)); transition: width 240ms ease; }
.home-active-task-card__meta { color: var(--text-muted); font-size: 11px; font-weight: 600; }
.home-task-toast { position: fixed; right: 24px; bottom: 24px; z-index: 50; display: grid; gap: 6px; max-width: 340px; }
.home-task-toast button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 36px; padding: 0 14px; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg-surface); color: var(--text-primary); font-size: 12px; font-weight: 700; box-shadow: var(--shadow-lg); cursor: pointer; }
.home-task-toast button:hover { background: var(--bg-muted); }
.home-toast-slide-enter-active, .home-toast-slide-leave-active { transition: opacity 160ms ease, transform 160ms ease; }
.home-toast-slide-enter-from, .home-toast-slide-leave-to { opacity: 0; transform: translateY(8px); }
.home-reference-pill { display: inline-flex; align-items: center; gap: 6px; max-width: 112px; }
.home-reference-pill-inline { margin: 0 0.2em; vertical-align: middle; white-space: nowrap; pointer-events: none; }
.home-reference-pill__thumb { flex: 0 0 auto; width: 22px; height: 22px; overflow: hidden; border-radius: 6px; }
.home-reference-pill__thumb img { width: 100%; height: 100%; object-fit: cover; }
.home-reference-pill__label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); font-size: 11px; font-weight: 600; }
.home-field { display: grid; gap: 4px; }
.home-field span { color: var(--text-muted); font-size: 11px; font-weight: 700; }
.home-field select, .home-field input { min-height: 38px; width: 100%; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg-surface); color: var(--text-primary); font-size: 13px; outline: 0; padding: 0 12px; }
.home-hidden-input { display: none; }
.home-composer__upload-preview-image { position: relative; }
.home-composer__upload-preview-image-remove { position: absolute; top: -6px; right: -6px; display: grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: var(--bg-surface); color: var(--text-muted); border: 1px solid var(--border-subtle); cursor: pointer; }
@media (max-width: 720px) {
  .home-page { padding: 24px 14px 32px; }
  .home-hero h1 { font-size: 22px; }
  .home-composer { padding: 16px; border-radius: 16px; }
  .home-composer__footer { flex-direction: column; align-items: stretch; gap: 10px; }
  .home-composer__submit { position: static; width: 100%; height: 40px; border-radius: 10px; }
  .home-popover { position: fixed; left: 14px; right: 14px; top: auto; bottom: 14px; z-index: 80; width: auto; max-height: min(400px,calc(100dvh - 96px)); border-radius: 20px; }
  .home-active-tasks { gap: 10px; }
  .home-active-task-card { flex-basis: min(86vw,280px); }
  .home-task-toast { right: 16px; bottom: 16px; left: 16px; max-width: none; }
}
</style>
