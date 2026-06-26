<template>
  <main class="home-page">
    <section class="home-hero">
      <h1
        class="home-brand-play"
        :class="{
          'home-brand-play-focused': promptEditorFocused,
          'home-brand-play-active': hasPromptInput,
          'home-brand-play-submitting': submitting,
        }"
        aria-label="JianDou 图片生成工作台"
      >
        <span class="home-brand-play__stage" aria-hidden="true">
          <span class="home-brand-play__halo"></span>
          <svg class="home-brand-play__mark" viewBox="0 0 128 128" role="presentation" focusable="false">
            <defs>
              <linearGradient id="home-brand-gradient" x1="31" y1="29" x2="97" y2="99" gradientUnits="userSpaceOnUse">
                <stop stop-color="#8b5cf6" />
                <stop offset="0.5" stop-color="#6366f1" />
                <stop offset="1" stop-color="#3b82f6" />
              </linearGradient>
              <linearGradient id="home-brand-gloss" x1="30" y1="32" x2="106" y2="65" gradientUnits="userSpaceOnUse">
                <stop stop-color="#c4b5fd" />
                <stop offset="1" stop-color="#ffffff" stop-opacity="0.36" />
              </linearGradient>
            </defs>
            <g class="home-brand-play__letter home-brand-play__letter-j">
              <path class="home-brand-play__logo-shadow" d="M27 39C32.7 34 43.2 33.5 49.5 38.8" />
              <path class="home-brand-play__logo-shadow" d="M44 37C45.2 51.2 44.7 64.5 41.5 75C37.4 88.6 27.9 95.3 18.5 90.5" />
              <path class="home-brand-play__logo-stroke" d="M27 39C32.7 34 43.2 33.5 49.5 38.8" />
              <path class="home-brand-play__logo-stroke" d="M44 37C45.2 51.2 44.7 64.5 41.5 75C37.4 88.6 27.9 95.3 18.5 90.5" />
              <path class="home-brand-play__logo-gloss" d="M31 38.5C35.1 36.7 42 36.8 46.4 39" />
              <g class="home-brand-play__face home-brand-play__face-j">
                <circle cx="35.4" cy="47.4" r="2" />
                <circle cx="44.6" cy="47.8" r="2" />
                <path d="M35.5 54.5C38.4 57 42.7 57 45.5 54.5" />
              </g>
            </g>
            <g class="home-brand-play__letter home-brand-play__letter-d">
              <path
                class="home-brand-play__logo-fill-shadow"
                fill-rule="evenodd"
                clip-rule="evenodd"
                d="M77 32H87C105.7 32 116 44.5 116 64C116 83.5 105.7 96 87 96H77C70.9 96 67 92.1 67 86V42C67 35.9 70.9 32 77 32ZM84 48V80H87C96.4 80 101.4 74.1 101.4 64C101.4 53.9 96.4 48 87 48H84Z"
              />
              <path
                class="home-brand-play__logo-fill"
                fill-rule="evenodd"
                clip-rule="evenodd"
                d="M77 30H87C105.7 30 116 42.5 116 62C116 81.5 105.7 94 87 94H77C70.9 94 67 90.1 67 84V40C67 33.9 70.9 30 77 30ZM84 46V78H87C96.4 78 101.4 72.1 101.4 62C101.4 51.9 96.4 46 87 46H84Z"
              />
              <path class="home-brand-play__logo-gloss" d="M77 40C79.4 36.7 84.2 35.2 89.2 35.5" />
              <g class="home-brand-play__face home-brand-play__face-d">
                <circle cx="88.7" cy="60" r="1.8" />
                <circle cx="96.2" cy="60" r="1.8" />
                <path d="M88.6 67C91.2 69.4 95.3 69.4 97.9 67" />
              </g>
            </g>
          </svg>
          <span class="home-brand-play__collision"></span>
          <span class="home-brand-play__burst">
            <span class="home-brand-play__spark home-brand-play__spark-1"></span>
            <span class="home-brand-play__spark home-brand-play__spark-2"></span>
            <span class="home-brand-play__spark home-brand-play__spark-3"></span>
            <span class="home-brand-play__spark home-brand-play__spark-4"></span>
            <span class="home-brand-play__spark home-brand-play__spark-5"></span>
            <span class="home-brand-play__spark home-brand-play__spark-6"></span>
            <span class="home-brand-play__spark home-brand-play__spark-7"></span>
            <span class="home-brand-play__spark home-brand-play__spark-8"></span>
          </span>
          <span class="home-brand-play__fall">
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-1"></span>
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-2"></span>
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-3"></span>
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-4"></span>
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-5"></span>
            <span class="home-brand-play__fall-dot home-brand-play__fall-dot-6"></span>
          </span>
        </span>
      </h1>

      <form
        class="home-composer liquid-glass"
        :class="{
          'home-composer-linked': promptEditorFocused,
          'home-composer-active': hasPromptInput,
          'home-composer-submitting': submitting,
        }"
        @submit.prevent="submitComposer"
      >
        <span class="home-composer__particle-loop" aria-hidden="true">
          <span class="home-composer__runner home-composer__runner-left home-composer__runner-1"></span>
          <span class="home-composer__runner home-composer__runner-left home-composer__runner-2"></span>
          <span class="home-composer__runner home-composer__runner-left home-composer__runner-3"></span>
          <span class="home-composer__runner home-composer__runner-left home-composer__runner-4"></span>
          <span class="home-composer__runner home-composer__runner-right home-composer__runner-5"></span>
          <span class="home-composer__runner home-composer__runner-right home-composer__runner-6"></span>
          <span class="home-composer__runner home-composer__runner-right home-composer__runner-7"></span>
          <span class="home-composer__runner home-composer__runner-right home-composer__runner-8"></span>
          <span class="home-composer__annihilation"></span>
        </span>
        <button
          type="button"
          class="home-composer__upload"
          :class="{
            'home-composer__upload-has-reference': referenceImages.length > 0,
            'home-composer__upload-has-multiple': referenceImages.length > 1,
            'home-composer__upload-expanded': referenceImages.length > 0 && referenceExpanded,
          }"
          :disabled="uploadingReference"
          @pointerenter="handleReferenceUploadPointerEnter"
          @pointerleave="handleReferenceUploadPointerLeave"
          @click="handleReferenceEntryClick"
        >
          <template v-if="referenceImages.length">
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
          accept="image/*"
          class="home-hidden-input"
          multiple
          @change="handleReferenceFileChange"
        />

        <div class="home-composer__body">
          <label class="home-composer__prompt">
            <div v-if="showPromptPlaceholder" class="home-composer__placeholder" aria-hidden="true">
              <span>描述你想生成的图片，</span>
              <span class="home-composer__placeholder-tag">@</span>
              <span> 引用参考图</span>
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
            <div class="home-menu home-menu-hidden" aria-hidden="true">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'model' }" @click="toggleMenu('model')">
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
                      :class="{ 'home-popover__item-active': form.textAnalysisModel === model.value }"
                      @click="form.textAnalysisModel = model.value"
                    >
                      <span class="home-popover__icon"><IconText size="sm" /></span>
                      <span>
                        <strong>{{ model.label }}</strong>
                      </span>
                      <span v-if="form.textAnalysisModel === model.value" class="home-popover__check" aria-hidden="true">
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
                      :class="{ 'home-popover__item-active': form.imageModel === model.value }"
                      @click="form.imageModel = model.value"
                    >
                      <span class="home-popover__icon"><IconImage size="sm" /></span>
                      <span>
                        <strong>{{ model.label }}</strong>
                      </span>
                      <span v-if="form.imageModel === model.value" class="home-popover__check" aria-hidden="true">
                        <IconCheck size="sm" />
                      </span>
                    </button>
                  </section>
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
                </div>
              </transition>
            </div>

            <div class="home-menu home-menu-hidden" aria-hidden="true">
              <button type="button" class="home-tool" :class="{ 'home-tool-active': activeMenu === 'count' }" @click="toggleMenu('count')">
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
                      @click="imageOutputCount = count"
                    >
                      {{ count }} 张
                    </button>
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
                  <button
                    v-if="!referenceImages.length"
                    type="button"
                    class="home-popover__item home-popover__item-empty"
                    :disabled="uploadingReference"
                    @click="handleReferenceEntryClick"
                  >
                    <span class="home-popover__icon"><IconImage size="sm" /></span>
                    <span>
                      <strong>上传一张图片来作为参考图</strong>
                    </span>
                  </button>
                  <button
                    v-for="item in referenceImages"
                    :key="item.id"
                    type="button"
                    class="home-popover__item home-popover__item-reference"
                    @click="insertMention(item.label)"
                  >
                    <span class="home-popover__image">
                      <img :src="item.fileUrl" :alt="item.label" />
                    </span>
                    <span>
                      <strong>{{ item.label }}</strong>
                    </span>
                  </button>
                </div>
              </transition>
            </div>

            <div class="home-menu home-menu-hidden" aria-hidden="true">
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
            <button
              v-if="creditLabel"
              type="button"
              class="home-credit-pill"
              :class="{ 'home-credit-pill-exempt': credits?.exempt }"
              @click="openCreditDialog"
            >
              {{ creditLabel }}
            </button>
            <RouterLink v-if="createdTaskId" :to="{ name: 'tasks', query: { selected: createdTaskId } }">查看</RouterLink>
          </div>
        </div>

        <button
          class="home-composer__submit"
          :class="{ 'home-composer__submit-submitting': submitting }"
          type="submit"
          :disabled="submitting || loadingOptions || !isFormReady"
          :aria-busy="submitting"
          :title="submitLabel"
        >
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComputedRef } from "vue";
import { requireAuth } from "@/auth/modal";
import { useAuthSessionState } from "@/auth/session";
import { createGenerationTask } from "@/features/home";
import { formatApiErrorMessage } from "@/utils/api-error";
import { formatTaskStatus } from "@/utils/task";

import { usePromptEditor } from "@/composables/home/usePromptEditor";
import { useReferenceImages, type ReferenceImageItem } from "@/composables/home/useReferenceImages";
import { useGenerationForm, type ModeOption, type RatioOptionValue } from "@/composables/home/useGenerationForm";
import { useActiveTasks } from "@/composables/home/useActiveTasks";
import { openCreditDetailsDialog } from "@/composables/useCreditDialog";
import { IconCheck, IconClose, IconImage, IconModel, IconFrame, IconTag, IconPlus, IconText } from "@/components/icons";

type MenuKey = "" | "model" | "ratio" | "count" | "mention" | "seed";

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
} = usePromptEditor(referenceImagesBridge, {
  onMentionTrigger: openMentionMenuFromPrompt,
});

const {
  form,
  selectedMode,
  seedMode,
  seedInput,
  autoSeed,
  imageOutputCount,
  loadingOptions,
  credits,
  promptLabel,
  textModelOptions,
  imageModelOptions,
  selectedImageModelOption,
  selectedPrimaryModelLabel,
  creditLabel,
  ratioOptions,
  selectedMaterialAssetType,
  ratioToolLabel,
  parsedManualSeed,
  seedCapabilityHint,
  isFormReady,
  imageOutputCountOptions,
  refreshAutoSeed,
  resolvedImageAspectRatioForSubmit,
  loadOptions,
  loadCredits,
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
  selectedMode: selectedMode as ComputedRef<ModeOption>,
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
  return "生成图片";
});

const hasPromptInput = computed(() => promptText.value.trim().length > 0);

// ---------------------------------------------------------------------------
// Menu toggle logic (not extracted)
// ---------------------------------------------------------------------------

function toggleMenu(menu: Exclude<MenuKey, "">) {
  activeMenu.value = activeMenu.value === menu ? "" : menu;
}

function openMentionMenuFromPrompt() {
  activeMenu.value = "mention";
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!activeMenu.value) {
    return;
  }
  const target = event.target instanceof Element ? event.target : null;
  if (target?.closest(".home-menu")) {
    return;
  }
  activeMenu.value = "";
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    activeMenu.value = "";
  }
}

function selectRatio(value: RatioOptionValue) {
  form.value.aspectRatio = value;
}

async function openCreditDialog() {
  const authenticated = await requireAuth({
    title: "登录后查看积分",
    message: "登录后可以查看积分余额、充值入口和使用明细。",
  });
  if (!authenticated) {
    return;
  }
  openCreditDetailsDialog(credits.value);
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
    await submitImageGeneration();
  } catch (error) {
    statusText.value = formatApiErrorMessage(error, "创建失败");
  } finally {
    submitting.value = false;
  }
}

async function submitImageGeneration() {
  const taskType = referenceImages.value.length ? "image_to_image" : "image_generation";
  const task = await createGenerationTask({
    title: promptText.value.trim().slice(0, 32) || "OpenAI 图片生成",
    taskType,
    assetType: selectedMaterialAssetType.value,
    creativePrompt: promptText.value.trim(),
    aspectRatio: resolvedImageAspectRatioForSubmit(),
    imageSize: null,
    textAnalysisModel: form.value.textAnalysisModel || null,
    imageModel: form.value.imageModel || null,
    videoModel: null,
    videoSize: null,
    outputCount: imageOutputCount.value,
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
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 14px;
  padding: clamp(32px, 7vh, 72px) 48px;
  background: linear-gradient(180deg, #f4f5f7 0%, #ffffff 46%, #f4f5f7 100%);
  color: var(--text-strong);
}

.home-hero {
  display: grid;
  width: 100%;
  justify-items: center;
  gap: clamp(18px, 3vh, 28px);
}

.home-brand-play {
  display: grid;
  place-items: center;
  width: min(100%, 340px);
  min-height: 148px;
  margin: 0;
  color: var(--text-strong);
  letter-spacing: 0;
  line-height: 1;
}

.home-brand-play__stage {
  position: relative;
  display: block;
  width: min(100%, 284px);
  height: 148px;
  overflow: visible;
  isolation: isolate;
}

.home-brand-play__stage::before,
.home-brand-play__stage::after {
  content: none;
}

.home-brand-play__halo {
  position: absolute;
  left: 50%;
  top: 14px;
  z-index: 0;
  width: 176px;
  height: 106px;
  border-radius: 48% 52% 46% 54%;
  background:
    radial-gradient(circle at 34% 28%, rgba(196, 181, 253, 0.34), transparent 30%),
    radial-gradient(circle at 70% 70%, rgba(59, 130, 246, 0.18), transparent 38%),
    rgba(255, 255, 255, 0.48);
  filter: blur(1px);
  opacity: 0.72;
  transform: translateX(-50%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
  animation: home-brand-halo 4.8s ease-in-out infinite;
}

.home-brand-play__mark {
  position: absolute;
  left: 50%;
  top: -8px;
  z-index: 2;
  width: 172px;
  height: 172px;
  overflow: visible;
  filter: drop-shadow(0 18px 28px rgba(99, 102, 241, 0.14));
  transform: translateX(-50%) scale(0.82);
  transform-origin: 50% 78%;
  animation: home-brand-mark-collision 4.8s cubic-bezier(0.34, 1.56, 0.64, 1) infinite;
  transition: filter 220ms ease;
}

.home-brand-play__letter {
  transform-box: fill-box;
  transform-origin: center bottom;
}

.home-brand-play__letter-j {
  animation: home-brand-j-collision 4.8s cubic-bezier(0.34, 1.56, 0.64, 1) infinite;
}

.home-brand-play__letter-d {
  animation: home-brand-d-collision 4.8s cubic-bezier(0.34, 1.56, 0.64, 1) infinite;
}

.home-brand-play__logo-shadow {
  fill: none;
  stroke: #1e1b4b;
  stroke-linecap: round;
  stroke-opacity: 0.12;
  stroke-width: 18;
}

.home-brand-play__logo-stroke {
  fill: none;
  stroke: url("#home-brand-gradient");
  stroke-linecap: round;
  stroke-width: 14;
}

.home-brand-play__logo-fill-shadow {
  fill: #1e1b4b;
  fill-opacity: 0.12;
}

.home-brand-play__logo-fill {
  fill: url("#home-brand-gradient");
}

.home-brand-play__logo-gloss {
  fill: none;
  stroke: url("#home-brand-gloss");
  stroke-linecap: round;
  stroke-width: 4.5;
}

.home-brand-play__face {
  opacity: 0.94;
  transform-box: fill-box;
  transform-origin: center;
  transition: opacity 180ms ease;
}

.home-brand-play__face circle {
  fill: #fff;
  stroke: rgba(30, 27, 75, 0.18);
  stroke-width: 0.45;
  transform-box: fill-box;
  transform-origin: center;
  animation: home-brand-blink 4.8s ease-in-out infinite;
}

.home-brand-play__face path {
  fill: none;
  stroke: #fff;
  stroke-linecap: round;
  stroke-width: 2.2;
}

.home-brand-play__face-d circle {
  fill: #1e1b4b;
  stroke: none;
}

.home-brand-play__face-d path {
  stroke: #1e1b4b;
  stroke-width: 2;
}

.home-brand-play__collision,
.home-brand-play__spark,
.home-brand-play__fall-dot {
  position: absolute;
  left: 50%;
  display: block;
  pointer-events: none;
}

.home-brand-play__collision {
  top: 65px;
  z-index: 4;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.92) 0 10%, rgba(251, 191, 36, 0.42) 11% 20%, rgba(139, 92, 246, 0.24) 21% 42%, rgba(59, 130, 246, 0) 66%);
  filter: blur(0.6px);
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.18);
  animation: home-brand-collision-flash 4.8s ease-out infinite;
}

.home-brand-play__burst,
.home-brand-play__fall {
  position: absolute;
  inset: 0;
  z-index: 5;
  pointer-events: none;
}

.home-brand-play__spark {
  top: 65px;
  width: 9px;
  height: 1.5px;
  border-radius: 50%;
  background: linear-gradient(90deg, transparent, var(--particle-color), transparent);
  box-shadow: 0 0 8px color-mix(in srgb, var(--particle-color) 56%, transparent);
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.3);
  animation: home-brand-spark-burst 4.8s cubic-bezier(0.2, 0.8, 0.25, 1) infinite;
}

.home-brand-play__spark-1 {
  --particle-color: #8b5cf6;
  --spark-x: -46px;
  --spark-y: -28px;
}

.home-brand-play__spark-2 {
  --particle-color: #3b82f6;
  --spark-x: -26px;
  --spark-y: -46px;
}

.home-brand-play__spark-3 {
  --particle-color: #06b6d4;
  --spark-x: 0px;
  --spark-y: -52px;
}

.home-brand-play__spark-4 {
  --particle-color: #22c55e;
  --spark-x: 30px;
  --spark-y: -42px;
}

.home-brand-play__spark-5 {
  --particle-color: #f97316;
  --spark-x: 48px;
  --spark-y: -20px;
}

.home-brand-play__spark-6 {
  --particle-color: #ec4899;
  --spark-x: 36px;
  --spark-y: 18px;
}

.home-brand-play__spark-7 {
  --particle-color: #facc15;
  --spark-x: -10px;
  --spark-y: 26px;
}

.home-brand-play__spark-8 {
  --particle-color: #a855f7;
  --spark-x: -40px;
  --spark-y: 12px;
}

.home-brand-play__fall-dot {
  top: 76px;
  z-index: 5;
  width: 12px;
  height: 1.5px;
  border-radius: 50%;
  background: linear-gradient(90deg, transparent, var(--particle-color), transparent);
  box-shadow:
    0 0 7px color-mix(in srgb, var(--particle-color) 56%, transparent),
    0 0 12px rgba(99, 102, 241, 0.12);
  opacity: 0;
  transform: translate(-50%, 0) rotate(var(--fall-tilt)) scaleX(0.52);
  animation: home-brand-particle-fall 4.8s cubic-bezier(0.18, 0.82, 0.34, 1) infinite;
}

.home-brand-play__fall-dot-1 {
  --particle-color: #8b5cf6;
  --fall-tilt: -18deg;
  --fall-start-x: -30px;
  --fall-land-x: -48px;
  animation-delay: 20ms;
}

.home-brand-play__fall-dot-2 {
  --particle-color: #3b82f6;
  --fall-tilt: 14deg;
  --fall-start-x: -16px;
  --fall-land-x: -24px;
  animation-delay: 90ms;
}

.home-brand-play__fall-dot-3 {
  --particle-color: #06b6d4;
  --fall-tilt: -10deg;
  --fall-start-x: -2px;
  --fall-land-x: -6px;
  animation-delay: 160ms;
}

.home-brand-play__fall-dot-4 {
  --particle-color: #22c55e;
  --fall-tilt: 12deg;
  --fall-start-x: 10px;
  --fall-land-x: 12px;
  animation-delay: 230ms;
}

.home-brand-play__fall-dot-5 {
  --particle-color: #f97316;
  --fall-tilt: -14deg;
  --fall-start-x: 24px;
  --fall-land-x: 32px;
  animation-delay: 300ms;
}

.home-brand-play__fall-dot-6 {
  --particle-color: #ec4899;
  --fall-tilt: 18deg;
  --fall-start-x: 38px;
  --fall-land-x: 52px;
  animation-delay: 370ms;
}

.home-brand-play-focused .home-brand-play__mark,
.home-brand-play-active .home-brand-play__mark {
  filter: drop-shadow(0 20px 30px rgba(99, 102, 241, 0.2));
}

.home-brand-play-submitting .home-brand-play__mark {
  animation-duration: 1.2s;
}

@keyframes home-brand-halo {
  0%,
  100% {
    transform: translateX(-50%) scale(1);
    opacity: 0.62;
  }
  31% {
    transform: translateX(-50%) scale(1.08);
    opacity: 0.92;
  }
  58% {
    transform: translateX(-50%) scale(1.02);
    opacity: 0.78;
  }
}

@keyframes home-brand-mark-collision {
  0%,
  100% {
    transform: translateX(-50%) scale(0.82);
  }
  24% {
    transform: translateX(-50%) scale(0.86);
  }
  31% {
    transform: translateX(-50%) scale(0.9);
  }
  38% {
    transform: translateX(-50%) scale(0.8);
  }
  54% {
    transform: translateX(-50%) scale(0.83);
  }
}

@keyframes home-brand-j-collision {
  0%,
  100% {
    transform: translateX(0) rotate(-1deg);
  }
  20% {
    transform: translateX(8px) rotate(3deg);
  }
  30% {
    transform: translateX(17px) rotate(8deg) scale(1.04);
  }
  37% {
    transform: translateX(-5px) rotate(-5deg) scale(0.98);
  }
  55% {
    transform: translateX(1px) rotate(1deg);
  }
}

@keyframes home-brand-d-collision {
  0%,
  100% {
    transform: translateX(0) rotate(1deg);
  }
  20% {
    transform: translateX(-8px) rotate(-3deg);
  }
  30% {
    transform: translateX(-17px) rotate(-8deg) scale(1.04);
  }
  37% {
    transform: translateX(5px) rotate(5deg) scale(0.98);
  }
  55% {
    transform: translateX(-1px) rotate(-1deg);
  }
}

@keyframes home-brand-collision-flash {
  0%,
  26%,
  47%,
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.18);
  }
  31% {
    opacity: 0.82;
    transform: translate(-50%, -50%) scaleX(1);
  }
  39% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1.45);
  }
}

@keyframes home-brand-spark-burst {
  0%,
  27%,
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.28);
  }
  31% {
    opacity: 0.82;
    transform: translate(-50%, -50%) scaleX(1);
  }
  43% {
    opacity: 0.82;
    transform: translate(calc(-50% + var(--spark-x)), calc(-50% + var(--spark-y))) rotate(var(--spark-tilt, 0deg)) scaleX(0.86);
  }
  58% {
    opacity: 0;
    transform: translate(calc(-50% + var(--spark-x)), calc(-50% + var(--spark-y) + 34px)) rotate(var(--spark-tilt, 0deg)) scaleX(0.2);
  }
}

@keyframes home-brand-particle-fall {
  0%,
  34%,
  100% {
    opacity: 0;
    transform: translate(calc(-50% + var(--fall-start-x)), 0) scale(0.5);
  }
  43% {
    opacity: 0.72;
    transform: translate(calc(-50% + var(--fall-start-x)), 14px) rotate(var(--fall-tilt)) scaleX(1);
  }
  61% {
    opacity: 0.58;
    transform: translate(calc(-50% + var(--fall-land-x)), 82px) rotate(var(--fall-tilt)) scaleX(0.78);
  }
  70% {
    opacity: 0;
    transform: translate(calc(-50% + var(--fall-land-x)), 106px) rotate(var(--fall-tilt)) scaleX(0.18);
  }
}

@keyframes home-brand-blink {
  0%,
  88%,
  100% {
    transform: scaleY(1);
  }
  92% {
    transform: scaleY(0.16);
  }
}

.home-composer__particle-loop {
  position: absolute;
  inset: -2px;
  z-index: 5;
  overflow: visible;
  border-radius: 20px;
  pointer-events: none;
}

.home-composer__particle-loop::before {
  position: absolute;
  inset: 0;
  content: "";
  border-radius: inherit;
  background:
    linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.72), rgba(59, 130, 246, 0.62), transparent) top left / 42% 1px no-repeat,
    linear-gradient(90deg, transparent, rgba(250, 204, 21, 0.62), rgba(236, 72, 153, 0.66), transparent) bottom right / 46% 1px no-repeat,
    linear-gradient(180deg, transparent, rgba(6, 182, 212, 0.58), transparent) left top / 1px 56% no-repeat,
    linear-gradient(180deg, transparent, rgba(34, 197, 94, 0.5), transparent) right top / 1px 54% no-repeat;
  filter: blur(0.15px);
  opacity: 0;
  animation: home-composer-border-shimmer 4.8s linear infinite;
}

.home-composer__runner {
  position: absolute;
  left: 50%;
  top: 0;
  width: 28px;
  height: 1.5px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, var(--runner-color), transparent);
  box-shadow:
    0 0 8px color-mix(in srgb, var(--runner-color) 68%, transparent),
    0 0 16px rgba(99, 102, 241, 0.18);
  mix-blend-mode: screen;
  opacity: 0;
  transform: translate(-50%, -50%) scaleX(0.68);
  transform-origin: center;
  animation-duration: 4.8s;
  animation-iteration-count: infinite;
  animation-timing-function: linear;
}

.home-composer__runner-left {
  animation-name: home-composer-run-left;
}

.home-composer__runner-right {
  animation-name: home-composer-run-right;
}

.home-composer__runner-1 {
  --runner-color: #8b5cf6;
  animation-delay: 0ms;
}

.home-composer__runner-2 {
  --runner-color: #3b82f6;
  animation-delay: 95ms;
}

.home-composer__runner-3 {
  --runner-color: #06b6d4;
  animation-delay: 190ms;
}

.home-composer__runner-4 {
  --runner-color: #22c55e;
  animation-delay: 285ms;
}

.home-composer__runner-5 {
  --runner-color: #f97316;
  animation-delay: 45ms;
}

.home-composer__runner-6 {
  --runner-color: #ec4899;
  animation-delay: 140ms;
}

.home-composer__runner-7 {
  --runner-color: #facc15;
  animation-delay: 235ms;
}

.home-composer__runner-8 {
  --runner-color: #a855f7;
  animation-delay: 330ms;
}

.home-composer__annihilation {
  position: absolute;
  left: 50%;
  bottom: -3px;
  width: 58px;
  height: 4px;
  border-radius: 50%;
  background:
    radial-gradient(ellipse at center, rgba(255, 255, 255, 0.82) 0 12%, rgba(250, 204, 21, 0.36) 13% 28%, rgba(99, 102, 241, 0.28) 29% 54%, rgba(99, 102, 241, 0) 76%);
  filter: blur(0.8px);
  opacity: 0;
  transform: translateX(-50%) scale(0.2);
  animation: home-composer-annihilation 4.8s ease-out infinite;
}

@keyframes home-composer-border-shimmer {
  0%,
  56%,
  100% {
    opacity: 0;
    background-position:
      top left,
      bottom right,
      left top,
      right top;
  }
  62% {
    opacity: 0.42;
  }
  76% {
    opacity: 0.5;
  }
  94% {
    opacity: 0.4;
    background-position:
      top right,
      bottom left,
      left bottom,
      right bottom;
  }
}

@keyframes home-composer-run-left {
  0%,
  57%,
  100% {
    left: 50%;
    top: 0;
    opacity: 0;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.52);
  }
  60% {
    left: 50%;
    top: 0;
    opacity: 0.82;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(1);
  }
  70% {
    left: 2px;
    top: 0;
    opacity: 0.78;
    transform: translate(-50%, -50%) rotate(90deg) scaleX(0.9);
  }
  84% {
    left: 2px;
    top: 100%;
    opacity: 0.7;
    transform: translate(-50%, -50%) rotate(90deg) scaleX(0.9);
  }
  96% {
    left: 50%;
    top: 100%;
    opacity: 0.82;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.82);
  }
  99% {
    left: 50%;
    top: 100%;
    opacity: 0;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.16);
  }
}

@keyframes home-composer-run-right {
  0%,
  57%,
  100% {
    left: 50%;
    top: 0;
    opacity: 0;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.52);
  }
  60% {
    left: 50%;
    top: 0;
    opacity: 0.82;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(1);
  }
  70% {
    left: calc(100% - 2px);
    top: 0;
    opacity: 0.78;
    transform: translate(-50%, -50%) rotate(-90deg) scaleX(0.9);
  }
  84% {
    left: calc(100% - 2px);
    top: 100%;
    opacity: 0.7;
    transform: translate(-50%, -50%) rotate(-90deg) scaleX(0.9);
  }
  96% {
    left: 50%;
    top: 100%;
    opacity: 0.82;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.82);
  }
  99% {
    left: 50%;
    top: 100%;
    opacity: 0;
    transform: translate(-50%, -50%) rotate(0deg) scaleX(0.16);
  }
}

@keyframes home-composer-annihilation {
  0%,
  78% {
    opacity: 0;
    transform: translateX(-50%) scale(0.2);
  }
  86% {
    opacity: 0.42;
    transform: translateX(-50%) scale(0.58);
  }
  92% {
    opacity: 0.82;
    transform: translateX(-50%) scale(0.82);
  }
  96% {
    opacity: 1;
    transform: translateX(-50%) scale(1.18);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) scale(2);
  }
}

.home-composer {
  position: relative;
  display: grid;
  width: min(100%, 1120px);
  min-height: 188px;
  padding: 22px 68px 22px 118px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(253, 254, 253, 0.96)),
    #fff;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.98) inset,
    0 14px 34px rgba(99, 102, 241, 0.07),
    0 4px 16px rgba(79, 70, 229, 0.06);
  overflow: visible;
  transition:
    border-color 220ms ease,
    box-shadow 220ms ease,
    transform 220ms ease;
}

.home-composer::before {
  content: "";
  position: absolute;
  left: 118px;
  right: 68px;
  top: -2px;
  z-index: 3;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(139, 92, 246, 0), rgba(99, 102, 241, 0.72), rgba(59, 130, 246, 0));
  opacity: 0.34;
  transform: scaleX(0.86);
  transform-origin: center;
  transition:
    opacity 220ms ease,
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
  pointer-events: none;
}

.home-composer-linked,
.home-composer-active {
  border-color: rgba(99, 102, 241, 0.24);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.98) inset,
    0 18px 44px rgba(99, 102, 241, 0.11),
    0 6px 18px rgba(79, 70, 229, 0.08);
  transform: translateY(-1px);
}

.home-composer-linked::before,
.home-composer-active::before {
  opacity: 0.86;
  transform: scaleX(1);
}

.home-composer-submitting {
  border-color: rgba(99, 102, 241, 0.34);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.98) inset,
    0 20px 48px rgba(99, 102, 241, 0.14),
    0 0 0 1px rgba(99, 102, 241, 0.08);
}

.home-hidden-input {
  display: none;
}

.home-composer__upload {
  position: absolute;
  left: 24px;
  top: 22px;
  z-index: 4;
  display: grid;
  place-items: center;
  gap: 6px;
  width: 68px;
  height: 98px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #eef2ff 100%);
  color: var(--accent-blue);
  transform: rotate(-5deg);
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.12);
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
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
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
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  line-height: 0;
  cursor: pointer;
  transform: rotate(var(--preview-remove-rotate, 0deg)) scale(0.84);
  transform-origin: center;
  opacity: 0;
  box-shadow:
    0 10px 24px rgba(0, 0, 0, 0.12),
    0 0 0 1px rgba(0, 0, 0, 0.06);
  transition:
    opacity 220ms ease,
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-composer__upload-preview-image-remove :deep(svg) {
  width: 13px;
  height: 13px;
}

.home-composer__upload-add-card {
  left: 60px;
  top: 4px;
  z-index: 0;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(0, 0, 0, 0.1);
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

.home-composer__upload-add-card :deep(svg),
.home-composer__upload > :deep(svg) {
  width: 20px;
  height: 20px;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  color: var(--text-strong);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.07);
  backdrop-filter: blur(40px) saturate(2.0);
}

.home-task-toast span {
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 700;
}

.home-task-toast a {
  flex: 0 0 auto;
  color: var(--accent-indigo);
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
}

.home-task-toast button {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-muted);
  line-height: 1;
  cursor: pointer;
}

.home-task-toast button:hover,
.home-task-toast button:focus-visible {
  background: #eef2ff;
  color: var(--accent-blue);
}

.home-task-toast button :deep(svg) {
  width: 14px;
  height: 14px;
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
  line-height: 0;
  transform: none;
  box-shadow:
    0 8px 18px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(0, 0, 0, 0.04);
  transition:
    opacity 220ms ease,
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
}

.home-reference-add :deep(svg) {
  width: 14px;
  height: 14px;
}

.home-composer__upload:not(.home-composer__upload-has-multiple) .home-reference-add {
  opacity: 0;
  pointer-events: none;
  transform: scale(0.84);
}

.home-composer__upload-expanded .home-composer__upload-add-card {
  opacity: 1;
  transform: translateX(0) rotate(0deg) scale(1);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
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
  min-height: 96px;
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
  min-height: 96px;
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
  border: 1px solid rgba(79, 70, 229, 0.18);
  border-radius: 8px;
  background: #eef2ff;
  color: var(--accent-indigo);
  font-size: 1.04rem;
  font-weight: 800;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
}

.home-composer__editor {
  min-height: 96px;
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
  margin-top: 10px;
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
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-strong);
  font-size: 0.8rem;
  font-weight: 760;
  box-shadow: none;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.home-tool:hover,
.home-tool:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(79, 70, 229, 0.24);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.07);
}

.home-tool-accent {
  border-color: rgba(79, 70, 229, 0.2);
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.98), rgba(224, 231, 255, 0.94));
  color: #4f46e5;
}

.home-tool-active {
  border-color: rgba(99, 102, 241, 0.22);
  background: #e0e7ff;
  color: var(--accent-blue);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
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
  z-index: 1;
}

.home-menu-hidden {
  display: none;
}

.home-menu:has(.home-popover) {
  z-index: 40;
}

.home-popover-float-enter-active,
.home-popover-float-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
  transform-origin: left top;
}

.home-popover-float-enter-from,
.home-popover-float-leave-to {
  opacity: 0;
  transform: translateY(7px) scale(0.985);
}

.home-popover {
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  z-index: 12;
  display: grid;
  gap: 8px;
  width: min(320px, calc(100vw - 48px));
  max-height: min(480px, calc(100vh - 120px));
  overflow-y: auto;
  padding: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(250, 253, 254, 0.98));
  box-shadow:
    0 18px 42px rgba(0, 0, 0, 0.06),
    0 2px 8px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(40px) saturate(2.0);
  overscroll-behavior: contain;
}

.home-popover-ratio {
  width: min(440px, calc(100vw - 48px));
  gap: 9px;
}

.home-popover-model {
  width: min(304px, calc(100vw - 48px));
}

.home-popover-compact,
.home-popover-seed {
  width: 240px;
}

.home-popover-section {
  display: grid;
  gap: 7px;
}

.home-popover-section + .home-popover-section {
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.home-popover__label {
  margin: 0 4px;
  color: #74838d;
  font-size: 0.7rem;
  font-weight: 820;
  letter-spacing: 0;
}

.home-popover__item {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 40px;
  border: 1px solid transparent;
  padding: 0 9px;
  border-radius: 11px;
  background: transparent;
  color: var(--text-strong);
  text-align: left;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease;
}

.home-popover__item-active {
  border-color: rgba(99, 102, 241, 0.18);
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.96), rgba(224, 231, 255, 0.92));
  color: var(--accent-blue);
  box-shadow: 0 7px 16px rgba(99, 102, 241, 0.055);
}

.home-popover__item:hover {
  border-color: rgba(99, 102, 241, 0.14);
  background: rgba(224, 231, 255, 0.74);
  transform: translateY(-1px);
}

.home-popover__icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 9px;
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.98), rgba(224, 231, 255, 0.94));
  color: var(--accent-indigo);
}

.home-popover__image {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
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
  min-width: 0;
  font-size: 0.84rem;
  font-weight: 740;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  color: var(--accent-blue);
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
  border-radius: 12px;
  background: #f6f9fb;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #f8fafb;
  color: var(--text-strong);
  font-size: 0.86rem;
  outline: 0;
  padding: 0 12px;
}

.home-segment-grid {
  display: grid;
  gap: 4px;
  overflow: hidden;
  padding: 4px;
  border-radius: 12px;
  background: #f4f7f9;
}

.home-ratio-list {
  display: grid;
  gap: 6px;
}

.home-segment-grid button,
.home-seed-row button {
  min-height: 36px;
  padding: 0 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-body);
  font-weight: 740;
  cursor: pointer;
}

.home-segment-grid button:hover,
.home-seed-row button:hover {
  background: rgba(255, 255, 255, 0.72);
  color: var(--accent-blue);
}

.home-ratio-list-immersive {
  grid-template-columns: repeat(auto-fit, minmax(58px, 1fr));
  align-items: stretch;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: #f4f7f9;
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
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
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

.home-segment-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 4px;
  border-radius: 12px;
  background: #f4f7f9;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-strong);
  font-size: 0.76rem;
  font-weight: 800;
  font-family: inherit;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    transform 160ms ease,
    box-shadow 160ms ease;
}

.home-credit-pill:hover,
.home-credit-pill:focus-visible {
  border-color: rgba(99, 102, 241, 0.22);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 8px 22px rgba(99, 102, 241, 0.12);
  outline: none;
  transform: translateY(-1px);
}

.home-credit-pill-exempt {
  border-color: rgba(59, 130, 246, 0.18);
  background: rgba(238, 242, 255, 0.9);
  color: var(--accent-blue);
}

.home-composer__submit {
  position: absolute;
  right: 18px;
  bottom: 20px;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 50%;
  background: #101819;
  color: #fff;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.1);
  cursor: pointer;
}

.home-composer__submit:not(:disabled) {
  background: linear-gradient(135deg, var(--accent-indigo) 0%, var(--accent-blue) 100%);
  box-shadow: 0 12px 26px rgba(99, 102, 241, 0.2);
}

.home-composer__submit-submitting,
.home-composer__submit-submitting:disabled {
  background: linear-gradient(135deg, var(--accent-indigo) 0%, var(--accent-blue) 100%);
  color: #fff;
  opacity: 1;
  box-shadow: 0 12px 26px rgba(99, 102, 241, 0.2);
  cursor: wait;
}

.home-composer__submit:disabled:not(.home-composer__submit-submitting) {
  cursor: not-allowed;
  opacity: 0.42;
}

.home-composer__submit svg,
.home-composer__submit :deep(svg) {
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
  background: rgba(0, 0, 0, 0.1);
}

.home-active-task-card {
  flex: 0 0 304px;
  display: grid;
  grid-template-rows: auto auto auto auto auto;
  gap: 10px;
  min-height: 166px;
  padding: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
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
  border-color: rgba(99, 102, 241, 0.2);
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
  background: rgba(0, 0, 0, 0.06);
}

.home-active-task-card__progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue));
  transition: width 240ms ease;
}

.home-active-task-card__meta {
  color: #7d8a97;
  font-size: 0.76rem;
  font-weight: 760;
}

@media (max-width: 1180px) {
  .home-page {
    padding: 34px 22px 36px;
  }
}

@media (max-width: 720px) {
  .home-page {
    padding: 26px 14px 32px;
  }

  .home-hero {
    gap: 0;
  }

  .home-brand-play {
    display: none;
  }

  .home-brand-play__stage {
    width: 236px;
    height: 122px;
  }

  .home-brand-play__halo {
    top: 10px;
    width: 144px;
    height: 88px;
  }

  .home-brand-play__mark {
    top: -13px;
    width: 150px;
    height: 150px;
    transform: translateX(-50%) scale(0.78);
  }

  .home-brand-play-focused .home-brand-play__mark {
    transform: translateX(-50%) translateY(4px) scale(0.8);
  }

  .home-composer {
    min-height: 0;
    padding: 18px 62px 18px 18px;
    border-radius: 18px;
  }

  .home-composer__particle-loop {
    display: none;
  }

  .home-composer::before {
    left: 18px;
    right: 62px;
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
    bottom: 14px;
    z-index: 80;
    width: auto;
    max-height: min(430px, calc(100dvh - 96px));
    padding: 20px 10px 10px;
    border-radius: 22px;
    box-shadow:
      0 -18px 46px rgba(0, 0, 0, 0.08),
      0 0 0 1px rgba(255, 255, 255, 0.82) inset;
  }

  .home-popover::before {
    content: "";
    justify-self: center;
    width: 38px;
    height: 4px;
    margin: -9px 0 2px;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.08);
  }

  .home-popover-ratio {
    width: auto;
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
