import { computed, nextTick, ref } from "vue";
import type { CreditSummary, GenerationTextAnalysisModelInfo } from "@/types";
import type { AppliedPromptTemplate, HomeSubmissionSnapshot } from "@/features/home/home-submission";
import type { ModeOption, ModeValue, RatioOptionValue, WorkbenchForm } from "./generationFormOptions";
import type { ReferenceImageItem } from "./useReferenceImages";
import type { HomeComposerMenuKey } from "@/views/home/components/HomeComposerToolbar.vue";

interface HomeComposerControlOptions {
  selectedMode: () => ModeOption;
  selectedModeValue: () => ModeValue;
  setSelectedModeValue: (value: ModeValue) => void;
  form: () => WorkbenchForm;
  prompt: () => string;
  setPrompt: (value: string) => void;
  imageOutputCount: () => number;
  selectedImageModel: () => GenerationTextAnalysisModelInfo | null;
  seedMode: () => "auto" | "manual";
  manualSeed: () => number | null;
  autoSeed: () => number;
  referenceImages: () => ReferenceImageItem[];
  clearReferenceImages: () => void;
  collapseReferences: () => void;
  authenticated: () => boolean;
  credits: () => CreditSummary | null;
  saveAspectRatio: (value: RatioOptionValue) => Promise<unknown>;
  authorizeCredits: () => Promise<boolean>;
  openCredits: (summary: CreditSummary | null) => void;
  renderPromptEditor: (value: string) => void;
  focusPromptEditorToEnd: () => void;
}

export function useHomeComposerControls(options: HomeComposerControlOptions) {
  const activeMenu = ref<HomeComposerMenuKey>("");
  const statusText = ref("加载参数");
  const selectedPromptTemplate = ref<AppliedPromptTemplate | null>(null);
  const templateChipNonce = ref(0);
  const hasPromptInput = computed(() => options.prompt().trim().length > 0);
  const promptPlaceholderLead = computed(() =>
    options.selectedMode().kind === "video" ? "描述你想生成的视频" : "描述你想生成的图片，",
  );

  function toggleMenu(menu: Exclude<HomeComposerMenuKey, "">) {
    activeMenu.value = activeMenu.value === menu ? "" : menu;
  }

  function selectMode(value: ModeValue) {
    if (options.selectedModeValue() === value) {
      activeMenu.value = "";
      return;
    }
    options.setSelectedModeValue(value);
    activeMenu.value = "";
    statusText.value = value === "video" ? "视频模式会创建阶段工作流。" : "图片模式支持参考图生成。";
  }

  function openMentionMenuFromPrompt() {
    activeMenu.value = "mention";
  }

  function selectRatio(value: RatioOptionValue) {
    if (options.form().aspectRatio === value) return;
    options.form().aspectRatio = value;
    if (options.authenticated()) void options.saveAspectRatio(value).catch(() => undefined);
  }

  async function openCreditDialog() {
    if (await options.authorizeCredits()) options.openCredits(options.credits());
  }

  function applyPromptTemplate(template: AppliedPromptTemplate) {
    activeMenu.value = "";
    selectedPromptTemplate.value = template;
    templateChipNonce.value += 1;
    statusText.value = `已使用${template.title}`;
    nextTick(() => {
      options.renderPromptEditor(options.prompt());
      options.focusPromptEditorToEnd();
    });
  }

  function submissionSnapshot(): HomeSubmissionSnapshot {
    const form = options.form();
    return {
      mode: options.selectedMode().value,
      prompt: options.prompt(),
      template: selectedPromptTemplate.value,
      aspectRatio: form.aspectRatio,
      textAnalysisModel: form.textAnalysisModel || "",
      imageModel: form.imageModel || "",
      videoModel: form.videoModel || "",
      videoSize: form.videoSize || "",
      outputCount: options.imageOutputCount(),
      supportsSeed: options.selectedImageModel()?.supportsSeed ?? false,
      seedMode: options.seedMode(),
      manualSeed: options.manualSeed(),
      autoSeed: options.autoSeed(),
      referenceImageUrls: options.referenceImages().map((item) => item.fileUrl),
    };
  }

  function resetComposerAfterSuccessfulSubmit() {
    activeMenu.value = "";
    options.setPrompt("");
    options.clearReferenceImages();
    options.collapseReferences();
    nextTick(() => options.renderPromptEditor(""));
  }

  return {
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
  };
}
