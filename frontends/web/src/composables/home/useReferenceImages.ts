import { nextTick, ref, type ComputedRef, type Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { uploadText } from "@/features/workflows";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ReferenceImageItem {
  id: string;
  label: string;
  fileUrl: string;
  fileName: string;
}

interface SelectedModeLike {
  kind: string;
  label: string;
  value: string;
}

export interface UseReferenceImagesOptions {
  selectedMode: ComputedRef<SelectedModeLike>;
  statusText: Ref<string>;
  promptText: Ref<string>;
  form: Ref<{ title: string; [key: string]: unknown }>;
  activeMenu: Ref<string>;
  renderPromptEditor: (value: string) => void;
  focusPromptEditorToEnd: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REFERENCE_PREVIEW_WIDTH = 68;
const REFERENCE_PREVIEW_HEIGHT = 98;
const REFERENCE_COLLAPSED_WIDTH = 58;
const REFERENCE_COLLAPSED_HEIGHT = 84;
const REFERENCE_EXPANDED_MAX_TILT_DEG = 30;
const REFERENCE_EXPANDED_GAP = 8;
const REFERENCE_EXPANDED_BOTTOM = 8;
const REFERENCE_ADD_CARD_OFFSET = 86;

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useReferenceImages(options: UseReferenceImagesOptions) {
  const { selectedMode, statusText, promptText, form, activeMenu, renderPromptEditor, focusPromptEditorToEnd } = options;

  // ----- state -----

  const uploadingReference = ref(false);
  const referenceExpanded = ref(false);
  const textFileInput = ref<HTMLInputElement | null>(null);
  const referenceImages = ref<ReferenceImageItem[]>([]);

  // ----- helpers -----

  function readTextFile(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
      reader.onerror = () => reject(reader.error ?? new Error("读取文本文件失败"));
      reader.readAsText(file, "utf-8");
    });
  }

  function readImageAsDataUri(file: File): Promise<ReferenceImageItem> {
    if (!file.type.startsWith("image/")) {
      return Promise.reject(new Error(`${file.name || "参考图"} 不是图片文件`));
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = typeof reader.result === "string" ? reader.result : "";
        if (!result.startsWith("data:image/") || !result.includes(";base64,")) {
          reject(new Error(`${file.name || "参考图"} 无法转换为 base64 图片`));
          return;
        }
        const nextIndex = referenceImages.value.length + 1;
        resolve({
          id: `${Date.now()}-${nextIndex}-${file.name}`,
          label: `图片${nextIndex}`,
          fileUrl: result,
          fileName: file.name || `图片${nextIndex}`,
        });
      };
      reader.onerror = () => reject(reader.error ?? new Error("参考图读取失败"));
      reader.readAsDataURL(file);
    });
  }

  // ----- event handlers -----

  function handleReferenceEntryClick() {
    if (selectedMode.value.kind === "video") {
      statusText.value = "视频模式先导入剧本文本，参考图会在分镜阶段补齐。";
      return;
    }
    textFileInput.value?.click();
  }

  function handleReferenceUploadPointerEnter() {
    if (selectedMode.value.kind === "image" && referenceImages.value.length > 0) {
      referenceExpanded.value = true;
    }
  }

  function handleReferenceUploadPointerLeave() {
    referenceExpanded.value = false;
  }

  // ----- style computations -----

  function referenceUploadSceneStyle() {
    if (referenceImages.value.length <= 1) {
      return referenceExpanded.value
        ? {
            width: `${REFERENCE_PREVIEW_WIDTH + REFERENCE_ADD_CARD_OFFSET}px`,
            height: `${REFERENCE_PREVIEW_HEIGHT}px`,
          }
        : undefined;
    }
    if (!referenceExpanded.value) {
      return undefined;
    }
    const step = referenceExpandedStep();
    const cardWidth = REFERENCE_PREVIEW_WIDTH;
    const addCardLeft = referenceImages.value.length * step;
    return {
      width: `${addCardLeft + cardWidth}px`,
      height: "112px",
    };
  }

  function referencePreviewRotation(index: number, expanded: boolean) {
    if (expanded) {
      const expandedRotations = [-9, 6, -7, 8, -5, 7, -8, 5, -6, 9, -4, 6];
      return expandedRotations[index % expandedRotations.length];
    }
    const collapsedRotations = [-7, 4, -5, 6, -4, 5];
    return collapsedRotations[index % collapsedRotations.length];
  }

  function referenceExpandedStep() {
    const radians = REFERENCE_EXPANDED_MAX_TILT_DEG * Math.PI / 180;
    const projectedWidth = REFERENCE_PREVIEW_WIDTH * Math.cos(radians) + REFERENCE_PREVIEW_HEIGHT * Math.sin(radians);
    return Math.ceil(projectedWidth + REFERENCE_EXPANDED_GAP);
  }

  function referenceRotationBottomDelta(rotateDeg: number) {
    return Math.sin(Math.abs(rotateDeg) * Math.PI / 180) * (REFERENCE_PREVIEW_WIDTH / 2);
  }

  function referenceExpandedBottom(rotateDeg: number) {
    const firstDelta = referenceRotationBottomDelta(referencePreviewRotation(0, true));
    const currentDelta = referenceRotationBottomDelta(rotateDeg);
    return `${REFERENCE_EXPANDED_BOTTOM - firstDelta + currentDelta}px`;
  }

  function referencePreviewImageStyle(index: number) {
    const total = referenceImages.value.length;
    if (total <= 1) {
      const rotate = -8;
      return {
        left: "0px",
        top: "0px",
        bottom: "auto",
        width: `${REFERENCE_PREVIEW_WIDTH}px`,
        height: `${REFERENCE_PREVIEW_HEIGHT}px`,
        opacity: "1",
        zIndex: "1",
        "--preview-rotate": `${rotate}deg`,
        "--preview-remove-rotate": `${-rotate}deg`,
        transformOrigin: "center bottom",
        transform: `rotate(${rotate}deg)`,
      };
    }

    if (referenceExpanded.value) {
      const step = referenceExpandedStep();
      const rotate = referencePreviewRotation(index, true);
      return {
        left: `${index * step}px`,
        top: "auto",
        bottom: referenceExpandedBottom(rotate),
        width: `${REFERENCE_PREVIEW_WIDTH}px`,
        height: `${REFERENCE_PREVIEW_HEIGHT}px`,
        opacity: "1",
        zIndex: String(index + 1),
        "--preview-rotate": `${rotate}deg`,
        "--preview-remove-rotate": `${-rotate}deg`,
        transformOrigin: "center bottom",
        transform: `rotate(${rotate}deg)`,
      };
    }

    const visibleIndex = Math.min(index, 4);
    const rotate = referencePreviewRotation(visibleIndex, false);
    return {
      left: `${-6 + visibleIndex * 8}px`,
      top: `${4 - Math.min(visibleIndex, 2) * 2}px`,
      bottom: "auto",
      width: `${REFERENCE_COLLAPSED_WIDTH}px`,
      height: `${REFERENCE_COLLAPSED_HEIGHT}px`,
      opacity: index < 4 ? "0.96" : "0",
      zIndex: String(index + 1),
      "--preview-rotate": `${rotate}deg`,
      "--preview-remove-rotate": `${-rotate}deg`,
      transformOrigin: "center bottom",
      transform: `rotate(${rotate}deg)`,
    };
  }

  function referenceAddCardStyle() {
    if (referenceImages.value.length <= 1) {
      if (!referenceExpanded.value) {
        return undefined;
      }
      return {
        left: `${REFERENCE_ADD_CARD_OFFSET}px`,
        top: "0px",
        bottom: "auto",
      };
    }
    if (!referenceExpanded.value) {
      return undefined;
    }
    const firstDelta = referenceRotationBottomDelta(referencePreviewRotation(0, true));
    return {
      left: `${referenceImages.value.length * referenceExpandedStep()}px`,
      top: "auto",
      bottom: `${REFERENCE_EXPANDED_BOTTOM - firstDelta}px`,
    };
  }

  // ----- file handling -----

  async function handleReferenceFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) {
      return;
    }
    if (selectedMode.value.kind === "image") {
      await handleImageReferenceFiles(files, input);
      return;
    }
    await handleTextReferenceFile(files[0], input);
  }

  async function handleTextReferenceFile(file: File, input: HTMLInputElement) {
    const authenticated = await requireAuth({
      title: "登录后上传参考内容",
      message: "文本上传会保存到你的账号下，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      input.value = "";
      return;
    }
    uploadingReference.value = true;
    statusText.value = "读取参考内容";
    try {
      const [, content] = await Promise.all([uploadText(file), readTextFile(file)]);
      if (content.trim()) {
        promptText.value = content;
        form.value.title = file.name.replace(/\.txt$/i, "") || form.value.title;
      }
      statusText.value = "参考内容已填入";
    } catch (error) {
      statusText.value = error instanceof Error ? error.message : "参考内容读取失败";
    } finally {
      uploadingReference.value = false;
      input.value = "";
    }
  }

  async function handleImageReferenceFiles(files: File[], input: HTMLInputElement) {
    uploadingReference.value = true;
    statusText.value = "读取参考图";
    try {
      const items = await Promise.all(files.map(readImageAsDataUri));
      const previousCount = referenceImages.value.length;
      const merged = [...referenceImages.value, ...items].slice(0, 12);
      referenceImages.value = merged.map((item, index) => ({
        ...item,
        label: `图片${index + 1}`,
      }));
      const addedCount = Math.max(referenceImages.value.length - previousCount, 0);
      statusText.value = addedCount > 0
        ? `已添加 ${addedCount} 张参考图，可通过 @ 引用。`
        : "最多支持 12 张参考图。";
    } catch (error) {
      statusText.value = error instanceof Error ? error.message : "参考图读取失败";
    } finally {
      uploadingReference.value = false;
      input.value = "";
    }
  }

  // ----- image management -----

  function removeReferenceImage(id: string) {
    const previousItems = referenceImages.value;
    const nextItems = referenceImages.value
      .filter((item) => item.id !== id)
      .map((item, index) => ({
        ...item,
        label: `图片${index + 1}`,
      }));
    referenceImages.value = nextItems;
    promptText.value = remapReferenceMentions(promptText.value, previousItems, nextItems);
    if (!nextItems.length) {
      referenceExpanded.value = false;
    }
  }

  // ----- mention handling -----

  function insertMention(label: string) {
    const mention = `@${label}`;
    const currentText = promptText.value;
    if (/(^|\s)@$/.test(currentText)) {
      promptText.value = currentText.replace(/(^|\s)@$/, `$1${mention} `);
    } else if (!promptText.value.includes(mention)) {
      promptText.value = currentText.trim() ? `${currentText.trim()} ${mention} ` : `${mention} `;
    }
    activeMenu.value = "";
    renderPromptEditor(promptText.value);
    nextTick(() => focusPromptEditorToEnd());
  }

  function remapReferenceMentions(text: string, previousItems: ReferenceImageItem[], nextItems: ReferenceImageItem[]) {
    const nextLabelById = new Map(nextItems.map((item) => [item.id, item.label]));
    const nextLabelByPreviousLabel = new Map(
      previousItems.map((item) => [item.label, nextLabelById.get(item.id) ?? null]),
    );
    return text.replace(/@图片\d+/g, (token) => {
      const nextLabel = nextLabelByPreviousLabel.get(token.slice(1));
      if (nextLabel === undefined) {
        return token;
      }
      return nextLabel ? `@${nextLabel}` : "";
    });
  }

  // ----- return -----

  return {
    // constants
    REFERENCE_PREVIEW_WIDTH,
    REFERENCE_PREVIEW_HEIGHT,
    REFERENCE_COLLAPSED_WIDTH,
    REFERENCE_COLLAPSED_HEIGHT,
    REFERENCE_EXPANDED_MAX_TILT_DEG,
    REFERENCE_EXPANDED_GAP,
    REFERENCE_EXPANDED_BOTTOM,
    REFERENCE_ADD_CARD_OFFSET,

    // state
    uploadingReference,
    referenceExpanded,
    textFileInput,
    referenceImages,

    // functions
    readTextFile,
    readImageAsDataUri,
    handleReferenceEntryClick,
    handleReferenceUploadPointerEnter,
    handleReferenceUploadPointerLeave,
    referenceUploadSceneStyle,
    referencePreviewRotation,
    referenceExpandedStep,
    referenceRotationBottomDelta,
    referenceExpandedBottom,
    referencePreviewImageStyle,
    referenceAddCardStyle,
    handleReferenceFileChange,
    handleTextReferenceFile,
    handleImageReferenceFiles,
    removeReferenceImage,
    insertMention,
    remapReferenceMentions,
  };
}
