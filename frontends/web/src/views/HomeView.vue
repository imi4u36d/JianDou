<template>
  <main class="home-page">
    <header class="workbench-header">
      <strong>工作台</strong>
      <button
        v-if="creditLabel"
        type="button"
        class="workbench-header__credits"
        :class="{ 'workbench-header__credits-exempt': credits?.exempt }"
        @click="openCreditDialog"
      >
        {{ creditLabel }}
      </button>
    </header>

    <section class="workbench-stage">
      <div class="home-hero">
        <h1 class="home-hero__title">描述你想生成的画面</h1>
        <form
          class="home-composer liquid-glass"
          :class="{
            'home-composer-linked': promptEditorFocused,
            'home-composer-active': hasPromptInput,
            'home-composer-submitting': submitting,
            'home-composer-video': selectedMode.kind === 'video',
          }"
          @submit.prevent="submitComposer"
        >
          <button
            v-if="selectedMode.kind === 'image'"
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
            v-if="selectedMode.kind === 'image'"
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
                <span>{{ promptPlaceholderLead }}</span>
                <template v-if="selectedMode.kind === 'image'">
                  <span class="home-composer__placeholder-tag">@</span>
                  <span> 参考图</span>
                </template>
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
            <HomeComposerToolbar
              :active-menu="activeMenu"
              :selected-mode="selectedMode"
              :selected-mode-value="selectedModeValue"
              :mode-options="modeOptions"
              :selected-primary-model-label="selectedPrimaryModelLabel"
              :text-model-options="textModelOptions"
              :image-model-options="imageModelOptions"
              :text-analysis-model="form.textAnalysisModel"
              :image-model="form.imageModel"
              :ratio-tool-label="ratioToolLabel"
              :aspect-ratio="form.aspectRatio"
              :ratio-options="ratioOptions"
              :selected-prompt-template="selectedPromptTemplate"
              :template-chip-nonce="templateChipNonce"
              :image-output-count="imageOutputCount"
              :image-output-count-options="imageOutputCountOptions"
              :reference-images="referenceImages"
              :uploading-reference="uploadingReference"
              :seed-mode="seedMode"
              :seed-input="seedInput"
              :auto-seed="autoSeed"
              :seed-capability-hint="seedCapabilityHint"
              @toggle-menu="toggleMenu"
              @select-mode="selectMode"
              @select-ratio="selectRatio"
              @select-text-model="form.textAnalysisModel = $event"
              @select-image-model="form.imageModel = $event"
              @select-output-count="imageOutputCount = $event"
              @open-reference="handleReferenceEntryClick"
              @insert-mention="insertMention"
              @select-seed-mode="seedMode = $event"
              @update-seed-input="seedInput = $event"
              @refresh-auto-seed="refreshAutoSeed"
            />

            <div class="home-composer__meta">
              <RouterLink v-if="createdTaskId" :to="{ name: 'image-tasks', query: { selected: createdTaskId } }"
                >查看</RouterLink
              >
            </div>
          </div>

          <button
            class="home-composer__submit jd-button jd-button--secondary jd-button--sm jd-button--icon-only"
            :class="{ 'home-composer__submit-submitting': submitting }"
            type="submit"
            :disabled="submitting || loadingOptions || !isFormReady"
            :aria-busy="submitting"
            :title="submitLabel"
          >
            <svg
              v-if="!submitting"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 19V5" />
              <path d="m5 12 7-7 7 7" />
            </svg>
            <IconLoading v-else size="sm" />
          </button>
        </form>

        <div v-if="statusText" class="home-composer-status home-composer-status-visible" aria-live="polite">
          <span aria-hidden="true"></span>{{ statusText }}
        </div>
      </div>

      <aside class="workbench-task-rail">
        <div class="workbench-task-rail__head">
          <h2>进行中</h2>
          <RouterLink to="/image-tasks">全部</RouterLink>
        </div>
        <HomeActiveTasks :tasks="activeTasks" />
        <div v-if="!activeTasks.length" class="workbench-task-rail__empty">
          <span>暂无任务</span>
        </div>
      </aside>
    </section>

    <PromptTemplateGallery @apply="applyPromptTemplate" />

    <PublicShareGallery />

    <HomeTaskToast :task-id="taskToastTaskId" @dismiss="dismissTaskToast" />
  </main>
</template>

<script setup lang="ts">
import { ref, type ComputedRef } from "vue";
import { useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import { useAuthSessionState } from "@/auth/session";
import { saveDefaultAspectRatio } from "@/features/home";

import { usePromptEditor } from "@/composables/home/usePromptEditor";
import { useReferenceImages, type ReferenceImageItem } from "@/composables/home/useReferenceImages";
import { useGenerationForm, type ModeOption } from "@/composables/home/useGenerationForm";
import { useActiveTasks } from "@/composables/home/useActiveTasks";
import { useHomeComposerSubmission } from "@/composables/home/useHomeComposerSubmission";
import { useHomeComposerLifecycle } from "@/composables/home/useHomeComposerLifecycle";
import { useHomeComposerControls } from "@/composables/home/useHomeComposerControls";
import { openCreditDetailsDialog } from "@/composables/useCreditDialog";
import { IconClose, IconLoading, IconPlus } from "@/components/icons";
import PromptTemplateGallery from "@/components/home/PromptTemplateGallery.vue";
import PublicShareGallery from "@/components/home/PublicShareGallery.vue";
import HomeActiveTasks from "@/views/home/components/HomeActiveTasks.vue";
import HomeComposerToolbar from "@/views/home/components/HomeComposerToolbar.vue";
import HomeTaskToast from "@/views/home/components/HomeTaskToast.vue";

const authState = useAuthSessionState();
const router = useRouter();
const referenceImagesBridge = ref<ReferenceImageItem[]>([]);

const controls = useHomeComposerControls({
  selectedMode: () => selectedMode.value,
  selectedModeValue: () => selectedModeValue.value,
  setSelectedModeValue: (value) => {
    selectedModeValue.value = value;
  },
  form: () => form.value,
  prompt: () => promptText.value,
  setPrompt: (value) => {
    promptText.value = value;
  },
  imageOutputCount: () => imageOutputCount.value,
  selectedImageModel: () => selectedImageModelOption.value,
  seedMode: () => seedMode.value,
  manualSeed: () => parsedManualSeed.value,
  autoSeed: () => autoSeed.value,
  referenceImages: () => referenceImages.value,
  clearReferenceImages: () => {
    referenceImages.value = [];
  },
  collapseReferences: () => {
    referenceExpanded.value = false;
  },
  authenticated: () => authState.isAuthenticated.value,
  credits: () => credits.value,
  saveAspectRatio: saveDefaultAspectRatio,
  authorizeCredits: () =>
    requireAuth({
      title: "登录后查看积分",
      message: "登录后可以查看积分余额、充值入口和使用明细。",
    }),
  openCredits: openCreditDetailsDialog,
  renderPromptEditor: (value) => renderPromptEditor(value),
  focusPromptEditorToEnd: () => focusPromptEditorToEnd(),
});
const {
  activeMenu,
  statusText,
  selectedPromptTemplate,
  templateChipNonce,
  hasPromptInput,
  promptPlaceholderLead,
  toggleMenu,
  selectMode,
  openMentionMenuFromPrompt,
  selectRatio,
  openCreditDialog,
  applyPromptTemplate,
  submissionSnapshot,
  resetComposerAfterSuccessfulSubmit,
} = controls;

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
  modeOptions,
  selectedMode,
  selectedModeValue,
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
  videoSizeOptions,
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

const { activeTasks, loadActiveTasks } = useActiveTasks();

const { submitting, createdTaskId, taskToastTaskId, dismissTaskToast, submitLabel, submitComposer } =
  useHomeComposerSubmission({
    statusText,
    isFormReady: () => isFormReady.value,
    modeKind: () => selectedMode.value.kind,
    snapshot: submissionSnapshot,
    imageRequestOptions: () => ({
      assetType: selectedMaterialAssetType.value,
      resolvedAspectRatio: resolvedImageAspectRatioForSubmit(),
    }),
    defaultVideoSize: () => videoSizeOptions.value[0]?.value || null,
    aspectRatio: () => form.value.aspectRatio,
    isAuthenticated: () => authState.isAuthenticated.value,
    resetComposer: resetComposerAfterSuccessfulSubmit,
    loadActiveTasks,
    push: (location) => router.push(location),
  });

useHomeComposerLifecycle({
  activeMenu,
  statusText,
  referenceImages,
  referenceImagesBridge,
  promptText,
  promptEditor,
  composingPrompt,
  syncingPromptFromEditor,
  authenticated: () => authState.isAuthenticated.value,
  renderPromptEditor,
  loadOptions,
  loadCredits,
  dismissTaskToast,
});
</script>
<style scoped src="./home-view.css"></style>
<style scoped src="./home-workbench.css"></style>
