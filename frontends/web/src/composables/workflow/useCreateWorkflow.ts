import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import { formatApiErrorMessage } from "@/utils/api-error";
import { createWorkflow, uploadText } from "@/features/workflows";
import type { CreateWorkflowRequest } from "@/types";
import { useWorkflowOptions } from "./useWorkflowOptions";

interface CreateReviewItem {
  key: string;
  label: string;
  valueLabel: string;
  configured: boolean;
  required: boolean;
}

interface CreateReviewSection {
  key: string;
  title: string;
  eyebrow: string;
  items: CreateReviewItem[];
}

export function useCreateWorkflow(opts: ReturnType<typeof useWorkflowOptions>) {
  const router = useRouter();
  const { valueOptionLabel, keyOptionLabel, syncVideoSizeSelection, options } = opts;

  const creatingWorkflow = ref(false);
  const createComposerVisible = ref(false);
  const createComposerMenu = ref<"" | "models" | "output" | "duration" | "seed">("");
  const createStatusText = ref("参数加载中...");
  const createTextFileInput = ref<HTMLInputElement | null>(null);
  const uploadingCreateText = ref(false);
  const storyboardDurationMode = ref<"auto" | "manual">("auto");
  const storyboardManualDurationSeconds = ref("8");
  const STORYBOARD_MANUAL_DURATION_MIN_SECONDS = 5;
  const STORYBOARD_MANUAL_DURATION_MAX_SECONDS = 12;

  const createForm = reactive({
    title: "",
    transcriptText: "",
    aspectRatio: "16:9",
    stylePreset: "",
    textAnalysisModel: "",
    imageModel: "",
    videoModel: "",
    videoSize: "",
    keyframeSeed: "",
    videoSeed: "",
  });

  const aspectRatioOptions = computed(() => opts.aspectRatioOptions.value);
  const stylePresetOptions = computed(() => opts.stylePresetOptions.value);
  const textModelOptions = computed(() => opts.textModelOptions.value);
  const imageModelOptions = computed(() => opts.imageModelOptions.value);
  const videoModelOptions = computed(() => opts.videoModelOptions.value);
  const videoSizeOptions = computed(() =>
    opts.filterVideoSizeOptions(opts.catalogVideoSizeOptions.value, createForm.videoModel, createForm.aspectRatio)
  );

  function parseStoryboardDurationSeconds(value?: string | null): number | null {
    if (value === undefined || value === null) return null;
    const raw = String(value).trim();
    if (!raw) return null;
    const numericValue = Number(raw);
    if (!Number.isFinite(numericValue) || !Number.isInteger(numericValue)) return null;
    return Math.trunc(numericValue);
  }

  const normalizedStoryboardManualDurationSeconds = computed(() => parseStoryboardDurationSeconds(storyboardManualDurationSeconds.value));

  const storyboardManualDurationValidationMessage = computed(() => {
    if (storyboardDurationMode.value === "auto") return "";
    if (!storyboardManualDurationSeconds.value.trim()) {
      return `请先填写合法的镜头时长（${STORYBOARD_MANUAL_DURATION_MIN_SECONDS}-${STORYBOARD_MANUAL_DURATION_MAX_SECONDS} 秒）`;
    }
    if (normalizedStoryboardManualDurationSeconds.value === null) {
      return `请先填写合法的镜头时长（${STORYBOARD_MANUAL_DURATION_MIN_SECONDS}-${STORYBOARD_MANUAL_DURATION_MAX_SECONDS} 秒）`;
    }
    if (
      normalizedStoryboardManualDurationSeconds.value < STORYBOARD_MANUAL_DURATION_MIN_SECONDS
      || normalizedStoryboardManualDurationSeconds.value > STORYBOARD_MANUAL_DURATION_MAX_SECONDS
    ) {
      return `手动模式的镜头时长需在 ${STORYBOARD_MANUAL_DURATION_MIN_SECONDS}-${STORYBOARD_MANUAL_DURATION_MAX_SECONDS} 秒之间`;
    }
    return "";
  });

  const isStoryboardDurationConfigured = computed(() => {
    if (storyboardDurationMode.value === "auto") return true;
    return Boolean(normalizedStoryboardManualDurationSeconds.value !== null && !storyboardManualDurationValidationMessage.value);
  });

  const createTranscriptCharacterCount = computed(() => createForm.transcriptText.trim().length);

  const createModelMenuLabel = computed(() => {
    const labels = [
      valueOptionLabel(textModelOptions.value, createForm.textAnalysisModel, ""),
      valueOptionLabel(imageModelOptions.value, createForm.imageModel, ""),
      valueOptionLabel(videoModelOptions.value, createForm.videoModel, ""),
    ].filter(Boolean);
    return labels.length ? `模型 · ${labels[labels.length - 1]}` : "模型链路";
  });

  const createOutputMenuLabel = computed(() => {
    const ratio = valueOptionLabel(aspectRatioOptions.value, createForm.aspectRatio, createForm.aspectRatio || "未设置");
    const size = valueOptionLabel(videoSizeOptions.value, createForm.videoSize, createForm.videoSize || "未设置");
    return `输出 · ${ratio} · ${size}`;
  });

  function seedLabel(value?: number | string | null): string {
    if (value === undefined || value === null || value === "") return "自动";
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? String(numericValue) : "自动";
  }

  const createDurationMenuLabel = computed(() => {
    if (storyboardDurationMode.value === "auto") return "时长 · 自动";
    return normalizedStoryboardManualDurationSeconds.value === null
      ? "时长 · 手动"
      : `时长 · ${normalizedStoryboardManualDurationSeconds.value}s`;
  });

  const createSeedMenuLabel = computed(() => {
    const keyframeSeed = seedLabel(createForm.keyframeSeed);
    const videoSeed = seedLabel(createForm.videoSeed);
    if (keyframeSeed === "自动" && videoSeed === "自动") return "Seed · 自动";
    return `Seed · K ${keyframeSeed} / V ${videoSeed}`;
  });

  const createReviewSections = computed<CreateReviewSection[]>(() => [
    {
      key: "base",
      eyebrow: "Workflow Base",
      title: "基础信息",
      items: [
        { key: "title", label: "标题", valueLabel: createForm.title.trim() || "未填写", configured: Boolean(createForm.title.trim()), required: true },
        { key: "transcriptText", label: "正文", valueLabel: createForm.transcriptText.trim() ? "已填写" : "未填写", configured: Boolean(createForm.transcriptText.trim()), required: true },
      ],
    },
    {
      key: "storyboard",
      eyebrow: "Stage 1",
      title: "文本分镜",
      items: [
        { key: "textAnalysisModel", label: "文本模型", valueLabel: valueOptionLabel(textModelOptions.value, createForm.textAnalysisModel, "未设置"), configured: Boolean(createForm.textAnalysisModel), required: true },
        { key: "storyboardDurationSeconds", label: "镜头时长", valueLabel: storyboardDurationMode.value === "auto" ? "自动" : (normalizedStoryboardManualDurationSeconds.value === null ? "未设置" : `${normalizedStoryboardManualDurationSeconds.value} 秒`), configured: isStoryboardDurationConfigured.value, required: true },
      ],
    },
    {
      key: "keyframe",
      eyebrow: "Stage 2",
      title: "关键帧",
      items: [
        { key: "imageModel", label: "关键帧模型", valueLabel: valueOptionLabel(imageModelOptions.value, createForm.imageModel, "未设置"), configured: Boolean(createForm.imageModel), required: true },
        { key: "stylePreset", label: "风格预设", valueLabel: keyOptionLabel(stylePresetOptions.value, createForm.stylePreset, "未设置"), configured: Boolean(createForm.stylePreset), required: true },
        { key: "aspectRatio", label: "长宽比", valueLabel: valueOptionLabel(aspectRatioOptions.value, createForm.aspectRatio, "未设置"), configured: Boolean(createForm.aspectRatio), required: true },
        { key: "keyframeSeed", label: "关键帧 Seed", valueLabel: createForm.keyframeSeed === "" ? "自动" : createForm.keyframeSeed, configured: true, required: false },
      ],
    },
    {
      key: "video",
      eyebrow: "Stage 3",
      title: "视频生成",
      items: [
        { key: "videoModel", label: "视频模型", valueLabel: valueOptionLabel(videoModelOptions.value, createForm.videoModel, "未设置"), configured: Boolean(createForm.videoModel), required: true },
        { key: "videoSize", label: "输出尺寸", valueLabel: valueOptionLabel(videoSizeOptions.value, createForm.videoSize, "未设置"), configured: Boolean(createForm.videoSize), required: true },
        { key: "videoSeed", label: "视频 Seed", valueLabel: createForm.videoSeed === "" ? "自动" : createForm.videoSeed, configured: true, required: false },
      ],
    },
  ]);

  const createReviewRequiredItems = computed(() =>
    createReviewSections.value.flatMap((section) => section.items.filter((item) => item.required))
  );
  const createReviewConfiguredCount = computed(() =>
    createReviewRequiredItems.value.filter((item) => item.configured).length
  );
  const canSubmitCreateReview = computed(() =>
    createReviewRequiredItems.value.every((item) => item.configured)
  );

  watch(
    options,
    (next) => {
      if (!next) return;
      createForm.aspectRatio ||= next.defaultAspectRatio || "16:9";
      createForm.stylePreset ||= next.defaultStylePreset || stylePresetOptions.value[0]?.key || "";
      createForm.textAnalysisModel ||= next.defaultTextAnalysisModel || textModelOptions.value[0]?.value || "";
      createForm.imageModel ||= next.defaultImageModel || imageModelOptions.value[0]?.value || "";
      createForm.videoModel ||= next.defaultVideoModel || videoModelOptions.value[0]?.value || "";
      syncVideoSizeSelection(createForm, next.defaultVideoSize);
    },
    { immediate: true }
  );

  function readTextFile(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
      reader.onerror = () => reject(reader.error ?? new Error("读取文本文件失败"));
      reader.readAsText(file, "utf-8");
    });
  }

  function optionalInteger(value?: string | number | null): number | null {
    if (value === undefined || value === null || value === "") return null;
    const numericValue = Number(value);
    return Number.isFinite(numericValue) && Number.isInteger(numericValue) ? numericValue : null;
  }

  function toggleCreateComposerMenu(menu: "" | "models" | "output" | "duration" | "seed") {
    createComposerMenu.value = createComposerMenu.value === menu ? "" : menu;
  }

  function startCreateWorkflow() {
    createComposerVisible.value = true;
    createComposerMenu.value = "";
    createStatusText.value = "在这里输入正文，创建一个新的阶段画布。";
  }

  async function closeCreateReview() {
    createComposerVisible.value = false;
    createComposerMenu.value = "";
    // Caller should set selectedWorkflow.value = null and push route
  }

  function buildCreatePayload(): CreateWorkflowRequest {
    const fixedDurationSeconds = storyboardDurationMode.value === "manual" ? normalizedStoryboardManualDurationSeconds.value : null;
    return {
      title: createForm.title.trim(),
      transcriptText: createForm.transcriptText.trim() || null,
      aspectRatio: createForm.aspectRatio as "9:16" | "16:9",
      stylePreset: createForm.stylePreset || null,
      textAnalysisModel: createForm.textAnalysisModel,
      imageModel: createForm.imageModel,
      videoModel: createForm.videoModel,
      videoSize: createForm.videoSize || null,
      keyframeSeed: createForm.keyframeSeed === "" ? null : Number(createForm.keyframeSeed),
      videoSeed: createForm.videoSeed === "" ? null : Number(createForm.videoSeed),
      durationMode: storyboardDurationMode.value,
      minDurationSeconds: fixedDurationSeconds,
      maxDurationSeconds: fixedDurationSeconds,
    };
  }

  async function handleCreateTextFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const authenticated = await requireAuth({
      title: "登录后上传正文",
      message: "正文上传会保存到你的账号下，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      input.value = "";
      return;
    }
    uploadingCreateText.value = true;
    createStatusText.value = "正在读取正文...";
    try {
      const [, content] = await Promise.all([uploadText(file), readTextFile(file)]);
      if (content.trim()) {
        createForm.transcriptText = content;
        if (!createForm.title.trim()) {
          createForm.title = file.name.replace(/\.txt$/i, "");
        }
      }
      createStatusText.value = "正文已填入画布输入框。";
    } catch (error) {
      const message = error instanceof Error ? error.message : "正文上传失败";
      createStatusText.value = message;
    } finally {
      uploadingCreateText.value = false;
      input.value = "";
    }
  }

  async function handleCreateWorkflow(openWorkflow: (id: string, stage?: string | null) => void, loadWorkflows: () => Promise<void>) {
    if (storyboardDurationMode.value === "manual" && storyboardManualDurationValidationMessage.value) return;
    const authenticated = await requireAuth({
      title: "登录后创建画布",
      message: "阶段工作流会保存到你的账号下，请先登录或使用邀请码注册。",
    });
    if (!authenticated) return;
    creatingWorkflow.value = true;
    createStatusText.value = "正在创建画布...";
    try {
      const workflow = await createWorkflow(buildCreatePayload());
      createForm.title = "";
      createForm.transcriptText = "";
      createForm.keyframeSeed = "";
      createForm.videoSeed = "";
      storyboardDurationMode.value = "auto";
      storyboardManualDurationSeconds.value = "8";
      createComposerMenu.value = "";
      createStatusText.value = "画布创建完成，正在进入阶段工作流。";
      createComposerVisible.value = false;
      await loadWorkflows();
      openWorkflow(workflow.id, workflow.currentStage);
    } catch (error) {
      const message = formatApiErrorMessage(error, "创建工作流失败");
      createStatusText.value = message;
    } finally {
      creatingWorkflow.value = false;
    }
  }

  return {
    creatingWorkflow,
    createComposerVisible,
    createComposerMenu,
    createStatusText,
    createTextFileInput,
    uploadingCreateText,
    storyboardDurationMode,
    storyboardManualDurationSeconds,
    STORYBOARD_MANUAL_DURATION_MIN_SECONDS,
    STORYBOARD_MANUAL_DURATION_MAX_SECONDS,
    createForm,
    videoSizeOptions,
    normalizedStoryboardManualDurationSeconds,
    storyboardManualDurationValidationMessage,
    isStoryboardDurationConfigured,
    createTranscriptCharacterCount,
    createModelMenuLabel,
    createOutputMenuLabel,
    createDurationMenuLabel,
    createSeedMenuLabel,
    createReviewSections,
    createReviewRequiredItems,
    createReviewConfiguredCount,
    canSubmitCreateReview,
    toggleCreateComposerMenu,
    startCreateWorkflow,
    closeCreateReview,
    buildCreatePayload,
    handleCreateTextFileChange,
    handleCreateWorkflow,
    readTextFile,
    optionalInteger,
    seedLabel,
  };
}
