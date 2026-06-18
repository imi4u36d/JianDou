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
                  <span
                    class="home-composer__upload-preview-image-remove"
                    role="button"
                    :aria-label="`移除${item.label}`"
                    @click.stop="removeReferenceImage(item.id)"
                  >
                    ×
                  </span>
                </span>
              </span>
              <span class="home-composer__upload-add-card" :style="referenceAddCardStyle()">
                <span>+</span>
              </span>
              <span class="home-reference-add">+</span>
            </span>
          </template>
          <span v-else>+</span>
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
              <span>输入想法、剧本或上传参考，支持 "/" 使用技能，</span>
              <span class="home-composer__placeholder-tag">@</span>
              <span> 添加主体，和Agent一起创作</span>
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
                      <small>{{ option.description }}</small>
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
                  <p class="home-popover__label">{{ selectedMode.kind === "video" ? "模型链路" : "图片模型" }}</p>
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
                        <span class="home-popover__icon">文</span>
                        <span>
                          <strong>{{ model.label }}</strong>
                          <small>{{ modelOptionDescription(model) }}</small>
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
                        <span class="home-popover__icon">帧</span>
                        <span>
                          <strong>{{ model.label }}</strong>
                          <small>{{ modelOptionDescription(model) }}</small>
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
                        <span class="home-popover__icon">影</span>
                        <span>
                          <strong>{{ model.label }}</strong>
                          <small>{{ modelOptionDescription(model) }}</small>
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
                        <span class="home-popover__icon">文</span>
                        <span>
                          <strong>{{ model.label }}</strong>
                          <small>{{ modelOptionDescription(model) }}</small>
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
                        <span class="home-popover__icon">图</span>
                        <span>
                          <strong>{{ model.label }}</strong>
                          <small>{{ modelOptionDescription(model) }}</small>
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
                    <p class="home-popover__label">选择比例</p>
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
                      <p class="home-popover__label">选择分辨率</p>
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
                  <p class="home-popover__label">视频时长</p>
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
                  <p class="home-popover__label">{{ selectedMode.kind === "image" ? "图片张数" : "分镜数量" }}</p>
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
                  <p class="home-popover__label">可能@的内容</p>
                  <button type="button" class="home-popover__item" @click="insertMention('创建主体')">
                    <span class="home-popover__icon"><IconPlus size="sm" /></span>
                    <span>
                      <strong>创建主体</strong>
                      <small>{{ selectedMode.kind === "image" ? "基于参考图或描述生成主体" : "视频主体功能正在开发中" }}</small>
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
                        <small>{{ item.fileName }}</small>
                      </span>
                    </button>
                  </template>
                  <p v-if="selectedMode.kind === 'video'" class="home-popover__empty">视频模式参考图正在开发中</p>
                  <p v-else-if="!referenceImages.length" class="home-popover__empty">暂无参考图</p>
                </div>
              </transition>
            </div>

            <div class="home-menu">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'seed' }" @click="toggleMenu('seed')">
                <span class="home-tool__icon"><IconTag /></span>
                {{ seedMode === "auto" ? "自动种子" : "手动种子" }}
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
                    <input v-model="seedInput" inputmode="numeric" placeholder="输入非负整数" />
                  </label>
                  <div v-else class="home-seed-row">
                    <span>{{ autoSeed }}</span>
                    <button type="button" @click="refreshAutoSeed">换一个</button>
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
            <RouterLink v-if="createdTaskId" :to="{ name: 'tasks', query: { selected: createdTaskId } }">查看任务</RouterLink>
          </div>
        </div>

        <button class="home-composer__submit" type="submit" :disabled="submitting || loadingOptions || !isFormReady" :title="submitLabel">
          <svg v-if="!submitting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 19V5" />
            <path d="m5 12 7-7 7 7" />
          </svg>
          <span v-else>...</span>
        </button>
      </form>

      <div v-if="referenceDevelopingDialogOpen" class="home-dialog" role="dialog" aria-modal="true" aria-labelledby="reference-developing-title" @click.self="referenceDevelopingDialogOpen = false">
        <div class="home-dialog__panel">
          <h2 id="reference-developing-title">正在开发中</h2>
          <p>视频模式添加参考图正在开发中。</p>
          <button type="button" @click="referenceDevelopingDialogOpen = false">知道了</button>
        </div>
      </div>
    </section>

    <Transition name="home-toast-slide">
      <div v-if="taskToastTaskId" class="home-task-toast" role="status">
        <span>任务已提交，可在任务管理查看进度</span>
        <RouterLink :to="{ name: 'tasks', query: { selected: taskToastTaskId } }">查看任务</RouterLink>
        <button type="button" aria-label="关闭任务提示" @click="dismissTaskToast">×</button>
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
import { IconCheck, IconVideo, IconImage, IconCharacter, IconModel, IconDuration, IconFrame, IconTag, IconPlus } from "@/components/icons";

type MenuKey = "" | "mode" | "model" | "ratio" | "duration" | "count" | "mention" | "seed";

// ---------------------------------------------------------------------------
// Local state (not extracted to composables)
// ---------------------------------------------------------------------------

const authState = useAuthSessionState();
const activeMenu = ref<MenuKey>("");
const statusText = ref("参数加载中...");
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
  referenceDevelopingDialogOpen,
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
    return "创建中...";
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
  statusText.value = "任务已提交，可在任务管理查看进度。";
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
  statusText.value = "任务已提交，可在任务管理查看进度。";
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
  min-height: 100%;
  padding: 76px 48px 56px;
  background:
    radial-gradient(circle at 18% 8%, rgba(139, 212, 80, 0.18), transparent 28%),
    radial-gradient(circle at 82% 12%, rgba(27, 124, 255, 0.12), transparent 30%),
    linear-gradient(180deg, #f6fbff 0%, #ffffff 46%, #f4fbf7 100%);
  color: var(--text-strong);
}

.home-hero {
  display: grid;
  justify-items: center;
  gap: 34px;
}

.home-hero h1 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0;
  max-width: 920px;
  color: #131a20;
  font-size: clamp(1.65rem, 3vw, 2.55rem);
  font-weight: 780;
  letter-spacing: 0;
  line-height: 1.18;
}

.hero-mode-button {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-blue);
  font: inherit;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(27, 124, 255, 0.24);
  text-decoration-thickness: 0.12em;
  text-underline-offset: 0.14em;
}

.home-composer {
  position: relative;
  display: grid;
  width: min(100%, 1120px);
  min-height: 206px;
  padding: 24px 72px 24px 128px;
  border: 1px solid rgba(0, 169, 187, 0.12);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(253, 254, 253, 0.96)),
    #fff;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.98) inset,
    0 18px 42px rgba(27, 124, 255, 0.08),
    0 4px 16px rgba(0, 169, 187, 0.06);
}

.home-hidden-input {
  display: none;
}

.home-composer__upload {
  position: absolute;
  left: 28px;
  top: 24px;
  z-index: 4;
  display: grid;
  place-items: center;
  gap: 6px;
  width: 68px;
  height: 98px;
  border: 1px solid rgba(18, 28, 33, 0.08);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #e9f8ff 100%);
  color: var(--accent-blue);
  transform: rotate(-5deg);
  box-shadow: 0 12px 24px rgba(27, 124, 255, 0.12);
  cursor: pointer;
  overflow: visible;
  transition:
    background 220ms ease,
    box-shadow 220ms ease,
    border-color 220ms ease,
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-composer__upload-has-reference {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
  transform: none;
}

.home-composer__upload-scene {
  position: absolute;
  left: 0;
  top: 0;
  display: block;
  width: 68px;
  height: 98px;
  transition:
    width 520ms cubic-bezier(0.22, 1, 0.36, 1),
    height 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-composer__upload-expanded .home-composer__upload-scene {
  width: 214px;
  height: 122px;
}

.home-composer__upload-preview,
.home-composer__upload-add-card {
  position: absolute;
  width: 68px;
  height: 98px;
  border-radius: 6px;
  transition:
    left 520ms cubic-bezier(0.22, 1, 0.36, 1),
    top 520ms cubic-bezier(0.22, 1, 0.36, 1),
    bottom 520ms cubic-bezier(0.22, 1, 0.36, 1),
    width 520ms cubic-bezier(0.22, 1, 0.36, 1),
    height 520ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 320ms ease,
    box-shadow 320ms ease,
    border-color 320ms ease,
    background 320ms ease;
}

.home-composer__upload-preview {
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  border: 0;
  background: transparent;
  box-shadow: none;
  transform: rotate(0deg);
}

.home-composer__upload-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 7px;
  box-shadow: 0 6px 14px rgba(15, 20, 25, 0.08);
}

.home-composer__upload-preview-image {
  position: absolute;
  border-radius: 7px;
  transition:
    left 520ms cubic-bezier(0.22, 1, 0.36, 1),
    top 520ms cubic-bezier(0.22, 1, 0.36, 1),
    bottom 520ms cubic-bezier(0.22, 1, 0.36, 1),
    width 520ms cubic-bezier(0.22, 1, 0.36, 1),
    height 520ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 320ms ease,
    opacity 320ms ease;
}

.home-composer__upload-preview-image-remove {
  position: absolute;
  right: -5px;
  top: -9px;
  z-index: 8;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(41, 46, 53, 0.94);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 500;
  line-height: 1;
  transform: rotate(var(--preview-remove-rotate, 0deg)) scale(0.84);
  transform-origin: center;
  opacity: 0;
  box-shadow:
    0 10px 24px rgba(15, 20, 25, 0.2),
    0 0 0 1px rgba(255, 255, 255, 0.08);
  transition:
    opacity 220ms ease,
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-composer__upload-add-card {
  left: 60px;
  top: 4px;
  z-index: 0;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(15, 20, 25, 0.12);
  background: linear-gradient(180deg, #fafafa 0%, #f4f4f4 100%);
  color: #7f8b97;
  transform: translateX(-18px) rotate(6deg) scale(0.92);
  opacity: 0;
}

.home-composer__upload-has-multiple .home-composer__upload-preview {
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.home-composer__upload-add-card span {
  font-size: 1.2rem;
  line-height: 1;
  font-weight: 700;
}

.home-composer__upload span {
  font-size: 1.72rem;
  line-height: 1;
  font-weight: 500;
}

.home-composer__upload > img {
  width: 46px;
  height: 46px;
  border-radius: 6px;
  object-fit: cover;
  transform: none;
}

.home-task-toast {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 70;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: min(420px, calc(100vw - 32px));
  min-height: 48px;
  padding: 10px 12px 10px 16px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  color: var(--text-strong);
  box-shadow: 0 18px 42px rgba(15, 20, 25, 0.14);
  backdrop-filter: blur(12px);
}

.home-task-toast span {
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 700;
}

.home-task-toast a {
  flex: 0 0 auto;
  color: var(--accent-cyan);
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
}

.home-task-toast button {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 1.05rem;
  line-height: 1;
}

.home-toast-slide-enter-active,
.home-toast-slide-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.home-toast-slide-enter-from,
.home-toast-slide-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

.home-reference-add {
  position: absolute;
  right: -10px;
  bottom: 8px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(244, 245, 247, 0.96);
  color: #20262d;
  font-size: 1rem !important;
  font-weight: 500;
  transform: none;
  box-shadow:
    0 8px 18px rgba(15, 20, 25, 0.08),
    0 0 0 1px rgba(15, 20, 25, 0.05);
  transition:
    opacity 220ms ease,
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-composer__upload:not(.home-composer__upload-has-multiple) .home-reference-add {
  opacity: 0;
  pointer-events: none;
  transform: scale(0.84);
}

.home-composer__upload-expanded .home-composer__upload-add-card {
  opacity: 1;
  transform: translateX(0) rotate(0deg) scale(1);
  box-shadow: 0 8px 18px rgba(15, 20, 25, 0.06);
}

.home-composer__upload-preview-image:hover {
  z-index: 4;
  transform: rotate(var(--preview-rotate, 0deg)) translateY(-4px) !important;
}

.home-composer__upload-preview-image:hover .home-composer__upload-preview-image-remove {
  opacity: 1;
  transform: rotate(var(--preview-remove-rotate, 0deg)) scale(1);
}

.home-composer__upload-expanded .home-reference-add {
  opacity: 0;
  transform: scale(0.84);
}

.home-composer__body {
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 104px;
}

.home-reference-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 112px;
}

.home-reference-pill-inline {
  margin: 0 0.2em;
  vertical-align: middle;
  white-space: nowrap;
  pointer-events: none;
}

.home-reference-pill__thumb {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  overflow: hidden;
  border-radius: 6px;
}

.home-reference-pill__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-reference-pill__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #657487;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1;
  align-self: center;
}

.home-composer__prompt {
  position: relative;
  display: block;
  min-height: 104px;
  outline: none;
}

.home-composer__prompt:focus-within,
.home-composer__prompt:focus-visible {
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
  color: #8c9aa4;
  font-size: 0.88rem;
  font-weight: 500;
  line-height: 1.5;
  pointer-events: none;
}

.home-composer__placeholder-tag {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(0, 169, 187, 0.18);
  border-radius: 8px;
  background: #effcff;
  color: var(--accent-cyan);
  font-size: 1.04rem;
  font-weight: 800;
  box-shadow: 0 4px 10px rgba(15, 20, 25, 0.04);
}

.home-composer__editor {
  min-height: 104px;
  width: 100%;
  padding: 0 18px 0 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  caret-color: var(--text-strong);
}

.home-composer__editor:focus,
.home-composer__editor:focus-visible {
  border: 0;
  outline: none;
  box-shadow: none;
}

.home-composer__editor:empty::before {
  content: "";
}

.home-composer__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
}

.home-composer__toolbar {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.home-tool {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(18, 28, 33, 0.08);
  border-radius: 8px;
  background: #f7f9f8;
  color: var(--text-strong);
  font-size: 0.8rem;
  font-weight: 720;
  box-shadow: none;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease;
}

.home-tool-accent {
  border-color: rgba(0, 169, 187, 0.2);
  background: #effcff;
  color: #008da1;
}

.home-tool-active {
  border-color: rgba(27, 124, 255, 0.22);
  background: #edf5ff;
  color: var(--accent-blue);
  box-shadow: inset 0 1px 2px rgba(18, 28, 33, 0.04);
}

.home-tool__icon {
  display: inline-grid;
  place-items: center;
  width: 16px;
  height: 16px;
  color: currentColor;
  line-height: 0;
}

.home-tool__icon :deep(svg),
.home-popover__icon :deep(svg),
.home-popover__check svg {
  width: 100%;
  height: 100%;
}

.home-tool__icon :deep(svg),
.home-popover__icon :deep(svg) {
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.home-tool__shape {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-radius: 5px;
}

.home-menu {
  position: relative;
}

.home-popover-float-enter-active,
.home-popover-float-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 220ms ease;
  transform-origin: left top;
}

.home-popover-float-enter-from,
.home-popover-float-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
  filter: blur(6px);
}

.home-popover {
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  z-index: 5;
  display: grid;
  gap: 8px;
  width: 320px;
  max-height: min(480px, calc(100vh - 120px));
  overflow-y: auto;
  padding: 10px;
  border: 1px solid rgba(18, 28, 33, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 18px 42px rgba(18, 28, 33, 0.12),
    0 2px 8px rgba(18, 28, 33, 0.04);
  backdrop-filter: blur(12px);
}

.home-popover-ratio {
  width: min(440px, calc(100vw - 48px));
  gap: 10px;
  padding: 12px;
  border-radius: 16px;
}

.home-popover-model {
  width: min(360px, calc(100vw - 48px));
}

.home-popover-compact,
.home-popover-seed {
  width: 240px;
}

.home-popover-section {
  display: grid;
  gap: 6px;
}

.home-popover__label {
  margin: 0 4px;
  color: #9aa6b2;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.home-popover__item {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 58px;
  border: 0;
  padding: 0 10px;
  border-radius: 12px;
  background: transparent;
  color: var(--text-strong);
  text-align: left;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.home-popover__item-active {
  background: #effcff;
}

.home-popover__icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #effcff;
  color: var(--accent-cyan);
}

.home-popover__image {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  overflow: hidden;
  background: #eef0f2;
}

.home-popover__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-popover__item strong,
.home-popover__item small {
  display: block;
}

.home-popover__item strong {
  font-size: 0.84rem;
  font-weight: 740;
}

.home-popover__item small,
.home-popover-seed small {
  margin-top: 2px;
  color: #738291;
  font-size: 0.72rem;
  line-height: 1.4;
}

.home-popover__check {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  color: #101820;
}

.home-popover__check svg {
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.home-popover__empty {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f8f9;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.home-dialog {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 20, 25, 0.28);
}

.home-dialog__panel {
  display: grid;
  gap: 14px;
  width: min(100%, 360px);
  padding: 22px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 20, 25, 0.2);
}

.home-dialog__panel h2,
.home-dialog__panel p {
  margin: 0;
}

.home-dialog__panel h2 {
  font-size: 1rem;
  font-weight: 850;
}

.home-dialog__panel p {
  color: var(--text-muted);
  font-size: 0.86rem;
  line-height: 1.6;
}

.home-dialog__panel button {
  justify-self: end;
  min-width: 82px;
  min-height: 36px;
  border: 0;
  border-radius: 9px;
  background: var(--text-strong);
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.home-field {
  display: grid;
  gap: 6px;
}

.home-field span {
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.home-field select,
.home-field input {
  min-height: 40px;
  width: 100%;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 10px;
  background: #f7f8f9;
  color: var(--text-strong);
  font-size: 0.86rem;
  outline: 0;
  padding: 0 12px;
}

.home-segment-grid {
  display: grid;
  gap: 6px;
}

.home-ratio-list {
  display: grid;
  gap: 6px;
}

.home-segment-grid button,
.home-seed-row button {
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-body);
  font-weight: 740;
  cursor: pointer;
}

.home-ratio-list-immersive {
  grid-template-columns: repeat(auto-fit, minmax(58px, 1fr));
  align-items: stretch;
  gap: 3px;
  padding: 3px;
  border-radius: 12px;
  background: #f3f4f5;
}

.home-ratio-list button {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 6px;
  min-height: 64px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #222c35;
  font-size: 0.68rem;
  font-weight: 560;
  cursor: pointer;
  transition:
    background 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease;
}

.home-ratio-active,
.home-segment-active {
  background: #fff !important;
  color: var(--accent-blue) !important;
  box-shadow: 0 1px 4px rgba(15, 20, 25, 0.08);
}

.home-ratio-active {
  color: #1f2831 !important;
}

.home-ratio__shape {
  width: 18px;
  max-height: 18px;
  min-height: 8px;
  border: 1.6px solid currentColor;
  border-radius: 4px;
}

.home-resolution-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 3px;
  overflow: hidden;
  padding: 3px;
  border-radius: 12px;
  background: #f3f4f5;
}

.home-resolution-list button {
  min-height: 42px;
  padding: 0 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #1f2831;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 160ms ease,
    box-shadow 160ms ease;
}

.home-resolution-active {
  background: #fff !important;
  color: #1f2831 !important;
  box-shadow: 0 1px 4px rgba(15, 20, 25, 0.08);
}

.home-dimension-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px minmax(0, 1fr) 50px;
  align-items: center;
  gap: 8px;
}

.home-dimension-row span,
.home-dimension-row strong {
  min-height: 42px;
  display: grid;
  align-items: center;
  border-radius: 10px;
  background: #f3f4f5;
}

.home-dimension-row span {
  justify-items: center;
  color: #556473;
  font-size: 0.7rem;
  font-weight: 700;
}

.home-dimension-row strong {
  grid-template-columns: 40px minmax(0, 1fr);
  justify-items: stretch;
  padding: 0 12px;
  color: #1f2831;
  font-size: 0.84rem;
  font-weight: 600;
}

.home-dimension-row strong::before {
  content: attr(data-label);
  display: grid;
  align-items: center;
  color: #556473;
  font-size: 0.74rem;
  font-weight: 700;
}

.home-dimension-row .home-dimension-link {
  background: transparent;
  color: #63717d;
  font-size: 1.18rem;
}

.home-segment-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 8px;
  border-radius: 12px;
  background: #f7f8f9;
}

.home-segment-grid button {
  min-height: 38px;
  padding: 0 10px;
}

.home-seed-row {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
  min-height: 40px;
  padding: 0 10px;
  border-radius: 10px;
  background: #f7f8f9;
  color: var(--text-strong);
  font-weight: 800;
}

.home-seed-row button {
  color: var(--accent-blue);
}

.home-composer__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  min-height: 38px;
  max-width: 320px;
  color: var(--text-muted);
  font-size: 0.78rem;
  justify-content: flex-end;
  text-align: right;
}

.home-composer__meta a {
  color: var(--accent-blue);
  font-weight: 800;
}

.home-credit-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-strong);
  font-size: 0.76rem;
  font-weight: 800;
  white-space: nowrap;
}

.home-credit-pill-exempt {
  border-color: rgba(0, 150, 136, 0.18);
  background: rgba(232, 247, 243, 0.9);
  color: #087767;
}

.home-composer__submit {
  position: absolute;
  right: 20px;
  bottom: 22px;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 50%;
  background: #101819;
  color: #fff;
  box-shadow: 0 10px 24px rgba(15, 20, 25, 0.12);
  cursor: pointer;
}

.home-composer__submit:not(:disabled) {
  background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%);
  box-shadow: 0 12px 26px rgba(27, 124, 255, 0.2);
}

.home-composer__submit:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.home-composer__submit svg {
  width: 18px;
  height: 18px;
}

.home-active-tasks {
  display: flex;
  align-items: stretch;
  gap: 14px;
  width: min(100%, 1120px);
  margin: 14px auto 0;
  overflow-x: auto;
  padding: 2px 2px 10px;
  scroll-snap-type: x proximity;
}

.home-active-tasks::-webkit-scrollbar {
  height: 8px;
}

.home-active-tasks::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(15, 20, 25, 0.12);
}

.home-active-task-card {
  flex: 0 0 304px;
  display: grid;
  grid-template-rows: auto auto auto auto auto;
  gap: 10px;
  min-height: 166px;
  padding: 16px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 14px;
  background: #fff;
  color: var(--text-strong);
  text-decoration: none;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.96) inset,
    0 8px 22px rgba(20, 28, 36, 0.045);
  scroll-snap-align: start;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.home-active-task-card:hover {
  transform: translateY(-2px);
  border-color: rgba(124, 58, 237, 0.22);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.96) inset,
    0 12px 30px rgba(20, 28, 36, 0.07);
}

.home-active-task-card__top,
.home-active-task-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.home-active-task-card__type,
.home-active-task-card__status {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.home-active-task-card__type {
  background: #f5f7f8;
  color: #6a7785;
}

.home-active-task-card__status {
  background: #eef8fb;
  color: var(--accent-blue);
}

.home-active-task-card h2 {
  display: -webkit-box;
  min-height: 44px;
  margin: 0;
  overflow: hidden;
  color: #15202b;
  font-size: 0.98rem;
  font-weight: 820;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.home-active-task-card p {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #6a7785;
  font-size: 0.82rem;
  font-weight: 650;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-active-task-card__progress {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(15, 20, 25, 0.07);
}

.home-active-task-card__progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  transition: width 240ms ease;
}

.home-active-task-card__meta {
  color: #7d8a97;
  font-size: 0.76rem;
  font-weight: 760;
}

@media (max-width: 1180px) {
  .home-page {
    padding: 44px 22px 36px;
  }
}

@media (max-width: 720px) {
  .home-page {
    padding: 26px 14px 32px;
  }

  .home-hero {
    gap: 28px;
  }

  .home-composer {
    min-height: 0;
    padding: 18px 62px 18px 18px;
    border-radius: 18px;
  }

  .home-composer__toolbar,
  .home-composer__meta {
    width: 100%;
  }

  .home-composer__upload {
    position: static;
    margin-bottom: 12px;
    width: 64px;
    height: 92px;
    transform: rotate(-6deg);
  }

  .home-composer__upload-has-reference {
    width: 64px;
  }

  .home-composer__upload-add-card,
  .home-composer__upload-preview-image-remove {
    display: none;
  }

  .home-composer__submit {
    right: 16px;
    bottom: 18px;
    width: 40px;
    height: 40px;
  }

  .home-composer__body {
    min-height: 0;
  }

  .home-composer__prompt {
    min-height: 104px;
  }

  .home-composer__editor {
    min-height: 104px;
    padding-right: 0;
  }

  .home-composer__placeholder {
    max-width: 100%;
    font-size: 1rem;
    line-height: 1.6;
  }

  .home-composer__placeholder-tag {
    width: 30px;
    height: 30px;
    border-radius: 10px;
    font-size: 1.05rem;
  }

  .home-composer__footer {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .home-composer__toolbar {
    padding-right: 54px;
  }

  .home-tool {
    min-height: 38px;
    padding: 0 14px;
    border-radius: 9px;
    font-size: 0.84rem;
  }

  .home-tool__shape {
    width: 18px;
    height: 18px;
    border-width: 2px;
  }

  .home-composer__meta {
    max-width: none;
    padding-right: 54px;
    justify-content: flex-start;
    text-align: left;
  }

  .home-popover {
    position: fixed;
    left: 14px;
    right: 14px;
    top: auto;
    bottom: 76px;
    width: auto;
    max-height: min(430px, calc(100vh - 120px));
  }

  .home-popover-ratio {
    width: auto;
  }

  .home-dimension-row {
    grid-template-columns: 34px minmax(0, 1fr) 28px 34px minmax(0, 1fr) 36px;
    gap: 6px;
  }

  .home-active-tasks {
    gap: 10px;
    margin-top: 12px;
    padding-bottom: 8px;
  }

  .home-active-task-card {
    flex-basis: min(86vw, 304px);
    min-height: 158px;
    border-radius: 16px;
  }

  .home-task-toast {
    right: 16px;
    bottom: 16px;
    left: 16px;
    max-width: none;
  }

}
</style>
