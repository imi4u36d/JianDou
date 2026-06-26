/**
 * 工作流详情组合式逻辑。
 * 从 StageWorkflowView 提取，管理工作流画布的全部状态和操作。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import {
  adjustStoryboard,
  deleteAllStageVersions,
  deleteStageVersion,
  fetchWorkflow,
  finalizeWorkflow,
  generateKeyframe,
  generateKeyframeFrame,
  generateStoryboard,
  generateVideo,
  reuseMaterialAsset,
  selectCharacterSheetAsset,
  selectKeyframe,
  selectKeyframeFrame,
  selectStoryboard,
  selectVideo,
  updateWorkflowSettings,
} from "@/features/workflows";
import {
  normalizeWorkflowCanvasStage,
  summaryFrameFailures,
  summaryNumberValue,
  summaryUrlValue,
  workflowCanvasStageFromCurrent as resolveWorkflowCanvasStageFromCurrent,
} from "@/features/workflows/summary";
import type { WorkflowCanvasStageKey } from "@/features/workflows/summary";
import { formatApiErrorMessage } from "@/utils/api-error";
import { messageApi } from "@/composables/useMessage";
import { renderMarkdownToHtml } from "@/utils/markdown";
import type {
  StageVersion,
  UpdateWorkflowSettingsRequest,
  WorkflowCharacterSheet,
  WorkflowClipSlot,
  WorkflowDetail,
} from "@/types";
import { useWorkflowOptions } from "@/composables/workflow/useWorkflowOptions";
import { useImagePreview } from "@/composables/workflow/useImagePreview";
import { useCharacterAssetPicker } from "@/composables/workflow/useCharacterAssetPicker";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import {
  characterSheetKey,
  characterSheetClipIndex,
  characterSheetTitle,
  characterSheetAppearanceSummary,
  characterSheetVersions,
  selectedCharacterSheetVersion,
  hasMissingCharacterSheets,
  characterSheetPreviewFrames,
} from "@/composables/workflow/useCharacterSheetUtils";
import type { AppSelectOption } from "@/components/common/app-select";

type CanvasStageKey = WorkflowCanvasStageKey;
interface PreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

function toAppSelectOptions<T extends { label: string; value: unknown }>(items: T[]): AppSelectOption[] {
  return items.map((item) => ({ label: item.label, value: item.value }));
}

function optionalInteger(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  return Number.isFinite(num) && Number.isInteger(num) ? num : null;
}

export interface UseWorkflowDetailOptions {
  selectedWorkflowId: () => string;
  reloadWorkflows: () => Promise<void>;
}

export function useWorkflowDetail(detailOptions: UseWorkflowDetailOptions) {
  // ── Composables ──
  const route = useRoute();
  const router = useRouter();
  const workflowOptions = useWorkflowOptions();
  const imagePreview = useImagePreview();
  const characterAssetPickerState = useCharacterAssetPicker();
  const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

  const {
    loadingOptions, aspectRatioOptions, stylePresetOptions,
    textModelOptions, imageModelOptions, videoModelOptions, catalogVideoSizeOptions,
    filterVideoSizeOptions, syncVideoSizeSelection, valueOptionLabel, loadOptions,
  } = workflowOptions;

  const {
    imagePreviewOverlayRef, imagePreviewTriggerRef, imagePreviewState,
    imagePreviewCaption, openImagePreview, closeImagePreview, switchImagePreviewFrame,
    captureImagePreviewTrigger, focusImagePreviewOverlay, applyImagePreviewItem,
  } = imagePreview;

  const {
    characterAssetPicker, materialAssetPreviewUrl, materialAssetModelLabel,
    isCharacterAssetPickerOpen, openCharacterAssetPicker, closeCharacterAssetPicker,
    loadCharacterAssetCandidates,
  } = characterAssetPickerState;

  // ── Core State ──
  const selectedWorkflowId = computed(() => detailOptions.selectedWorkflowId());
  const loadingDetail = ref(false);
  const busyActionKey = ref("");
  const activeCanvasStage = ref<CanvasStageKey>("storyboard");
  const previewStoryboardVersionId = ref("");
  const previewCharacterSheetVersionIds = reactive<Record<string, string>>({});
  const selectedCanvasClipIndex = ref<number | null>(null);
  const previewKeyframeVersionIds = reactive<Record<number, string>>({});
  const previewVideoVersionIds = reactive<Record<number, string>>({});
  const imagePreviewLoadFailed = ref(false);
  const failedPreviewImageUrls = ref(new Set<string>());
  const selectedWorkflow = ref<WorkflowDetail | null>(null);
  const storyboardAdjustmentDrafts = reactive<Record<string, string>>({});
  const workflowSettingsOpen = ref(false);
  const workflowSettingsDraft = reactive({
    aspectRatio: "16:9",
    stylePreset: "",
    textAnalysisModel: "",
    imageModel: "",
    videoModel: "",
    videoSize: "",
    keyframeSeed: "",
    videoSeed: "",
    durationMode: "auto" as "auto" | "manual",
    minDurationSeconds: "5",
    maxDurationSeconds: "12",
  });
  const characterSummaryPreviewState = reactive({ open: false, title: "", content: "" });

  // ── Select Options ──
  const textModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(textModelOptions.value));
  const imageModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(imageModelOptions.value));
  const videoModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(videoModelOptions.value));
  const aspectRatioSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(aspectRatioOptions.value));
  const stylePresetSelectOptions = computed<AppSelectOption[]>(() =>
    stylePresetOptions.value.map((item) => ({ label: item.label, value: item.key }))
  );
  const workflowSettingsVideoSizeOptions = computed(() =>
    filterVideoSizeOptions(catalogVideoSizeOptions.value, workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio)
  );
  const workflowSettingsVideoSizeSelectOptions = computed<AppSelectOption[]>(() =>
    toAppSelectOptions(workflowSettingsVideoSizeOptions.value)
  );

  // ── Computed: Workflow Data ──
  const workflowCharacterSheets = computed(() => selectedWorkflow.value?.characterSheets ?? []);
  const missingCharacterSheets = computed(() =>
    workflowCharacterSheets.value.filter((sheet) => !selectedCharacterSheetVersion(sheet))
  );
  const selectedStoryboardVersion = computed(() => {
    const versions = selectedWorkflow.value?.storyboardVersions ?? [];
    if (!versions.length) return null;
    return versions.find((v) => v.id === previewStoryboardVersionId.value)
      ?? versions.find((v) => v.selected) ?? versions[0];
  });
  const selectedCanvasClip = computed(() => {
    const slots = selectedWorkflow.value?.clipSlots ?? [];
    if (!slots.length) return null;
    return slots.find((s) => s.clipIndex === selectedCanvasClipIndex.value) ?? slots[0];
  });
  const previewKeyframeVersion = computed(() => {
    const clip = selectedCanvasClip.value;
    if (!clip) return null;
    const previewId = previewKeyframeVersionIds[clip.clipIndex] || "";
    return clip.keyframeVersions.find((v) => v.id === previewId)
      ?? clip.keyframeVersions.find((v) => v.selected) ?? clip.keyframeVersions[0] ?? null;
  });
  const previewVideoVersion = computed(() => {
    const clip = selectedCanvasClip.value;
    if (!clip) return null;
    const previewId = previewVideoVersionIds[clip.clipIndex] || "";
    return clip.videoVersions.find((v) => v.id === previewId)
      ?? clip.videoVersions.find((v) => v.selected) ?? clip.videoVersions[0] ?? null;
  });

  function previewCharacterSheetVersion(sheet: WorkflowCharacterSheet) {
    const versions = characterSheetVersions(sheet);
    const previewId = previewCharacterSheetVersionIds[characterSheetKey(sheet)] || "";
    return versions.find((v) => v.id === previewId)
      ?? selectedCharacterSheetVersion(sheet) ?? versions[0] ?? null;
  }

  const videoReadiness = computed(() => {
    const slots = selectedWorkflow.value?.clipSlots ?? [];
    return {
      total: slots.length,
      generated: slots.filter((s) => s.videoVersions.some((v) => canSelectVideoVersion(v))).length,
      selected: slots.filter((s) => s.videoVersions.some((v) => v.selected)).length,
      missing: slots.filter((s) => !s.videoVersions.some((v) => v.selected)),
    };
  });

  const canFinalize = computed(() => {
    const wf = selectedWorkflow.value;
    if (!wf || !(wf.clipSlots ?? []).length) return false;
    return (wf.clipSlots ?? []).every((s) => (s.videoVersions ?? []).some((v) => v.selected));
  });

  const finalizeButtonLabel = computed(() => selectedWorkflow.value?.finalResult ? "重拼" : "拼接");
  const finalizeHint = computed(() => {
    const wf = selectedWorkflow.value;
    if (!wf || !(wf.clipSlots ?? []).length) return "等待镜头";
    if (canFinalize.value) return "可拼接";
    return `缺 ${videoReadiness.value.missing.length}`;
  });

  const canvasStageItems = computed(() => {
    const wf = selectedWorkflow.value;
    const storyboardCount = wf?.storyboardVersions?.length ?? 0;
    const keyframeCount = wf?.clipSlots?.reduce((sum, s) => sum + (s.keyframeVersions?.length ?? 0), 0) ?? 0;
    const videoCount = wf?.clipSlots?.reduce((sum, s) => sum + (s.videoVersions?.length ?? 0), 0) ?? 0;
    const selectedCharacterCount = workflowCharacterSheets.value.filter((s) => Boolean(selectedCharacterSheetVersion(s))).length;
    return [
      { key: "storyboard" as const, index: 1, label: "分镜脚本", status: storyboardCount ? "已有版本" : "待生成", count: `${storyboardCount} 版`, ready: storyboardCount > 0 },
      { key: "character" as const, index: 2, label: "角色三视图", status: selectedCharacterCount ? "已有角色" : (storyboardCount ? "可生成" : "等分镜"), count: `${selectedCharacterCount}/${workflowCharacterSheets.value.length || 0}`, ready: selectedCharacterCount > 0 },
      { key: "keyframe" as const, index: 3, label: "关键帧", status: keyframeCount ? "已有关键帧" : (storyboardCount ? "可生成" : "等角色"), count: `${keyframeCount} 版`, ready: keyframeCount > 0 },
      { key: "video" as const, index: 4, label: "视频片段", status: videoCount ? "已有视频" : (keyframeCount ? "可生成" : "等关键帧"), count: `${videoCount} 版`, ready: videoCount > 0 },
      { key: "final" as const, index: 5, label: "成片", status: wf?.finalResult ? "已拼接" : (canFinalize.value ? "可拼接" : "未就绪"), count: wf?.finalResult ? "已完成" : `${videoReadiness.value.selected}/${videoReadiness.value.total || 0}`, ready: Boolean(wf?.finalResult || canFinalize.value) },
    ];
  });

  const workflowParameterTags = computed(() => {
    const wf = selectedWorkflow.value;
    if (!wf) return [];
    return [
      { label: "关键帧模型", value: compactModelLabel(valueOptionLabel(imageModelOptions.value, wf.imageModel, wf.imageModel || "未设置")) },
      { label: "视频模型", value: compactModelLabel(valueOptionLabel(videoModelOptions.value, wf.videoModel, wf.videoModel || "未设置")) },
      { label: "尺寸", value: compactVideoSizeLabel(valueOptionLabel(catalogVideoSizeOptions.value, wf.videoSize, wf.videoSize || "未设置"), wf.aspectRatio) },
    ];
  });

  const workflowSettingsValidationMessage = computed(() => {
    if (!workflowSettingsDraft.textAnalysisModel) return "请选择文本模型";
    if (!workflowSettingsDraft.imageModel) return "请选择关键帧模型";
    if (!workflowSettingsDraft.stylePreset) return "请选择视觉风格";
    if (!workflowSettingsDraft.aspectRatio) return "请选择画幅";
    if (!workflowSettingsDraft.videoModel) return "请选择视频模型";
    if (!workflowSettingsDraft.videoSize) return "请选择输出尺寸";
    if (workflowSettingsDraft.durationMode === "auto") return "";
    const minDur = optionalInteger(workflowSettingsDraft.minDurationSeconds);
    const maxDur = optionalInteger(workflowSettingsDraft.maxDurationSeconds);
    if (minDur === null || maxDur === null || minDur < 1 || maxDur < 1) return "请填写合法的镜头时长";
    if (maxDur < minDur) return "最大时长不能小于最小时长";
    return "";
  });

  // ── Helper Functions ──

  function compactModelLabel(value: string) {
    return value.replace(/\s*\([^)]*\)\s*/g, " ").replace(/\bDoubao\s+/i, "").replace(/\s+/g, " ").trim();
  }
  function compactVideoSizeLabel(sizeLabel: string, aspectRatio?: string | null) {
    const size = (sizeLabel || "未设置").trim();
    const ratio = (aspectRatio || "").trim();
    if (!ratio || size.includes(ratio)) return size;
    return `${size} · ${ratio}`;
  }
  function normalizedStageVersionStatus(version: StageVersion) {
    return (version.status || "").trim().toUpperCase();
  }
  function stageStatusLabel(status?: string | null) {
    switch ((status || "").trim().toUpperCase()) {
      case "SUCCEEDED": case "COMPLETED": return "可用";
      case "RUNNING": case "PROCESSING": return "生成中";
      case "FAILED": return "失败";
      case "PENDING": return "等待";
      default: return "未完成";
    }
  }
  function stageVersionDisplayTitle(version: StageVersion) {
    const rawTitle = (version.title || "").trim();
    const prefix = new RegExp(`^V${version.versionNo}[.、\\-_:：·\\s]*`, "i");
    const deduped = rawTitle.replace(prefix, "").trim();
    return deduped || rawTitle || "未命名版本";
  }
  function videoVersionErrorMessage(version: StageVersion) {
    const msg = version.outputSummary?.error || version.outputSummary?.taskMessage || "";
    return typeof msg === "string" ? msg.trim() : "";
  }
  function compactVideoVersionError(version: StageVersion) {
    const message = videoVersionErrorMessage(version);
    if (!message) return "";
    if (/inference limit|set inference limit/i.test(message)) return "模型额度已达上限";
    if (/safe experience mode|model service has been paused/i.test(message)) return "模型服务暂停";
    if (/timeout|timed out/i.test(message)) return "生成超时";
    if (/rate limit|too many requests/i.test(message)) return "请求过于频繁";
    return message.length > 42 ? `${message.slice(0, 42)}...` : message;
  }
  function canSelectVideoVersion(version: StageVersion) {
    return normalizedStageVersionStatus(version) === "COMPLETED" && Boolean(version.downloadUrl || version.outputSummary?.fileUrl || version.asset?.publicUrl || version.asset?.fileUrl);
  }
  function videoVersionStatusLabel(version: StageVersion) {
    const error = videoVersionErrorMessage(version);
    if (error) return "生成失败";
    const taskStatus = typeof version.outputSummary?.taskStatus === "string" ? version.outputSummary.taskStatus.trim() : "";
    const status = normalizedStageVersionStatus(version);
    if (canSelectVideoVersion(version)) return version.selected ? "当前" : "可选";
    if (status === "FAILED" || taskStatus.toUpperCase() === "FAILED") return "生成失败";
    if (status === "RUNNING" || taskStatus) return taskStatus ? `生成中：${taskStatus}` : "生成中";
    return "未完成";
  }
  function videoSlotStatusLabel(slot: WorkflowClipSlot) {
    if (slot.videoVersions.some((v) => v.selected)) return "当前";
    if (slot.videoVersions.some((v) => canSelectVideoVersion(v))) return "待选择";
    if (slot.videoVersions.some((v) => normalizedStageVersionStatus(v) === "FAILED" || videoVersionErrorMessage(v))) return "生成失败";
    if (slot.videoVersions.length) return "生成中";
    return "未生成";
  }
  function selectCanvasClip(clipIndex: number) { selectedCanvasClipIndex.value = clipIndex; }
  function storyboardPreview(version: StageVersion) {
    const o = version.outputSummary ?? {};
    return (typeof o.scriptMarkdown === "string" ? o.scriptMarkdown : "") || (typeof o.previewText === "string" ? o.previewText : "") || "暂无分镜预览";
  }
  function storyboardPreviewHtml(version: StageVersion) { return renderMarkdownToHtml(storyboardPreview(version)); }
  function isLandscapeKeyframeVersion(version: StageVersion) {
    const o = version.outputSummary ?? {};
    const w = summaryNumberValue(o, "width") || Number(version.asset?.width ?? 0);
    const h = summaryNumberValue(o, "height") || Number(version.asset?.height ?? 0);
    if (Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0) return w > h;
    return (selectedWorkflow.value?.aspectRatio || "").trim().startsWith("16:");
  }
  function keyframePreviewFrames(version: StageVersion, slot?: WorkflowClipSlot): PreviewFrame[] {
    const o = version.outputSummary ?? {};
    const firstFrameUrl = summaryUrlValue(o, "startFrameUrl", "firstFrameUrl");
    const frameFailures = summaryFrameFailures(o);
    const lastFailure = frameFailures.find((item) => item.role === "last");
    const lastFrameUrl = summaryUrlValue(o, "endFrameUrl", "lastFrameUrl")
      || (!lastFailure ? summaryUrlValue(o, "fileUrl") || (typeof version.previewUrl === "string" ? version.previewUrl : "") : "");
    const hasExplicitFirst = slot ? slot.keyframeVersions.some((v) => Boolean(v.outputSummary?.selectedFirstFrame)) : false;
    const hasExplicitLast = slot ? slot.keyframeVersions.some((v) => Boolean(v.outputSummary?.selectedLastFrame)) : false;
    const frames: PreviewFrame[] = [];
    if (firstFrameUrl) frames.push({ role: "first", label: "首帧", url: firstFrameUrl, selected: Boolean(o.selectedFirstFrame || (!hasExplicitFirst && version.selected)), regenerable: version.clipIndex <= 1 });
    const firstFailure = frameFailures.find((item) => item.role === "first");
    if (!firstFrameUrl && firstFailure) frames.push({ role: "first", label: "首帧", url: "", selected: false, regenerable: version.clipIndex <= 1, errorMessage: firstFailure.message });
    if (lastFrameUrl && (!firstFrameUrl || lastFrameUrl !== firstFrameUrl || version.clipIndex === 1)) frames.push({ role: "last", label: "尾帧", url: lastFrameUrl, selected: Boolean(o.selectedLastFrame || (!hasExplicitLast && version.selected)), regenerable: true });
    if (!lastFrameUrl && lastFailure) frames.push({ role: "last", label: "尾帧", url: "", selected: false, regenerable: true, errorMessage: lastFailure.message });
    return frames;
  }
  function isPreviewImageFailed(url?: string | null) { return Boolean(url && failedPreviewImageUrls.value.has(url)); }
  function isPreviewImageAvailable(url?: string | null) { return Boolean(url && !failedPreviewImageUrls.value.has(url)); }
  function markPreviewImageFailed(url?: string | null) {
    if (!url) return;
    const next = new Set(failedPreviewImageUrls.value);
    next.add(url);
    failedPreviewImageUrls.value = next;
  }
  function versionSeed(version: StageVersion) {
    const seed = version.inputSummary?.seed;
    if (seed === undefined || seed === null || seed === "") return null;
    const num = Number(seed);
    return Number.isFinite(num) ? num : null;
  }
  function durationLabel(value?: number | null) {
    return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : "-";
  }
  function clipSceneText(slot: WorkflowClipSlot) { return slot.scene?.trim() || "暂无场景描述"; }
  function clipSceneSummary(slot: WorkflowClipSlot) {
    const text = clipSceneText(slot);
    return text.length > 120 ? `${text.slice(0, 120)}...` : text;
  }
  function formatDateTime(value?: string | null) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
  }
  function openCharacterSummaryPreview(sheet: WorkflowCharacterSheet) {
    characterSummaryPreviewState.open = true;
    characterSummaryPreviewState.title = characterSheetTitle(sheet);
    characterSummaryPreviewState.content = characterSheetAppearanceSummary(sheet);
  }
  function closeCharacterSummaryPreview() {
    characterSummaryPreviewState.open = false;
    characterSummaryPreviewState.title = "";
    characterSummaryPreviewState.content = "";
  }
  function openKeyframeImagePreview(version: StageVersion, frame: PreviewFrame) {
    if (!frame.url) return;
    const frames = keyframePreviewFrames(version).filter((item) => item.url);
    const gallery = frames.map((item) => ({ url: item.url, alt: `${stageVersionDisplayTitle(version)}${item.label}`, caption: `${stageVersionDisplayTitle(version)} ${item.label}` }));
    const currentIndex = Math.max(0, frames.findIndex((item) => item.role === frame.role));
    const currentItem = gallery[currentIndex];
    if (!currentItem) { openImagePreview(frame.url, `${stageVersionDisplayTitle(version)}${frame.label}`); return; }
    captureImagePreviewTrigger();
    imagePreviewState.open = true;
    imagePreviewState.gallery = gallery;
    applyImagePreviewItem(currentItem, currentIndex);
    focusImagePreviewOverlay();
  }
  function handleImagePreviewKeydown(event: KeyboardEvent) {
    if (characterSummaryPreviewState.open && event.key === "Escape") { event.preventDefault(); closeCharacterSummaryPreview(); return; }
    if (!imagePreviewState.open) return;
    if (event.key === "Escape") { event.preventDefault(); closeImagePreview(); return; }
    if (event.key === "ArrowLeft") { event.preventDefault(); switchImagePreviewFrame(-1); return; }
    if (event.key === "ArrowRight") { event.preventDefault(); switchImagePreviewFrame(1); }
  }
  function positionVersionMenu(event: ToggleEvent) {
    if (event.newState !== "open") return;
    const popover = event.target as HTMLElement;
    // 通过 popovertarget 属性精确定位触发按钮，避免 DOM 层级依赖
    const trigger = document.querySelector<HTMLElement>(`[popovertarget="${popover.id}"]`);
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const popoverWidth = popover.offsetWidth || 164;
    const popoverHeight = Math.max(popover.scrollHeight, popover.offsetHeight, 92);
    let left = rect.right - popoverWidth;
    if (left < 8) left = 8;
    if (left + popoverWidth > window.innerWidth - 8) left = window.innerWidth - popoverWidth - 8;
    let top = rect.bottom + 4;
    if (top + popoverHeight > window.innerHeight - 8) top = Math.max(8, rect.top - popoverHeight - 4);
    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
  }

  // ── Data Loading ──

  function syncWorkflowSettingsDraft(workflow: WorkflowDetail) {
    const minDur = workflow.minDurationSeconds ?? 5;
    const maxDur = workflow.maxDurationSeconds ?? 12;
    workflowSettingsDraft.aspectRatio = workflow.aspectRatio || "16:9";
    workflowSettingsDraft.stylePreset = workflow.stylePreset || "";
    workflowSettingsDraft.textAnalysisModel = workflow.textAnalysisModel || "";
    workflowSettingsDraft.imageModel = workflow.imageModel || "";
    workflowSettingsDraft.videoModel = workflow.videoModel || "";
    workflowSettingsDraft.videoSize = workflow.videoSize || "";
    workflowSettingsDraft.keyframeSeed = workflow.keyframeSeed == null ? "" : String(workflow.keyframeSeed);
    workflowSettingsDraft.videoSeed = workflow.videoSeed == null ? "" : String(workflow.videoSeed);
    workflowSettingsDraft.durationMode = workflow.durationMode === "manual" ? "manual" : "auto";
    workflowSettingsDraft.minDurationSeconds = String(minDur);
    workflowSettingsDraft.maxDurationSeconds = String(maxDur);
    syncVideoSizeSelection(workflowSettingsDraft, workflow.videoSize);
  }

  function applyWorkflowDrafts(workflow: WorkflowDetail | null) {
    if (!workflow) { workflowSettingsOpen.value = false; return; }
    syncWorkflowSettingsDraft(workflow);
    for (const version of workflow.storyboardVersions ?? []) {
      storyboardAdjustmentDrafts[version.id] ??= "";
    }
    previewStoryboardVersionId.value =
      workflow.storyboardVersions.find((v) => v.id === previewStoryboardVersionId.value)?.id
      ?? workflow.storyboardVersions.find((v) => v.selected)?.id
      ?? workflow.storyboardVersions[0]?.id ?? "";
    for (const sheet of workflow.characterSheets ?? []) {
      const sheetKey = characterSheetKey(sheet);
      const versions = characterSheetVersions(sheet);
      previewCharacterSheetVersionIds[sheetKey] =
        versions.find((v) => v.id === previewCharacterSheetVersionIds[sheetKey])?.id
        ?? versions.find((v) => v.selected)?.id ?? versions[0]?.id ?? "";
    }
    for (const slot of workflow.clipSlots ?? []) {
      previewKeyframeVersionIds[slot.clipIndex] =
        slot.keyframeVersions.find((v) => v.id === previewKeyframeVersionIds[slot.clipIndex])?.id
        ?? slot.keyframeVersions.find((v) => v.selected)?.id ?? slot.keyframeVersions[0]?.id ?? "";
      previewVideoVersionIds[slot.clipIndex] =
        slot.videoVersions.find((v) => v.id === previewVideoVersionIds[slot.clipIndex])?.id
        ?? slot.videoVersions.find((v) => v.selected)?.id ?? slot.videoVersions[0]?.id ?? "";
    }
  }

  function buildWorkflowSettingsPayload(): UpdateWorkflowSettingsRequest {
    return {
      aspectRatio: workflowSettingsDraft.aspectRatio,
      stylePreset: workflowSettingsDraft.stylePreset,
      textAnalysisModel: workflowSettingsDraft.textAnalysisModel,
      imageModel: workflowSettingsDraft.imageModel,
      videoModel: workflowSettingsDraft.videoModel,
      videoSize: workflowSettingsDraft.videoSize,
      keyframeSeed: optionalInteger(workflowSettingsDraft.keyframeSeed),
      videoSeed: optionalInteger(workflowSettingsDraft.videoSeed),
      durationMode: workflowSettingsDraft.durationMode,
      minDurationSeconds: workflowSettingsDraft.durationMode === "auto" ? null : optionalInteger(workflowSettingsDraft.minDurationSeconds),
      maxDurationSeconds: workflowSettingsDraft.durationMode === "auto" ? null : optionalInteger(workflowSettingsDraft.maxDurationSeconds),
    };
  }

  async function loadWorkflowDetail(workflowId: string, options?: { quiet?: boolean }) {
    const quiet = options?.quiet ?? false;
    if (!quiet) loadingDetail.value = true;
    try {
      selectedWorkflow.value = await fetchWorkflow(workflowId);
      const routeStage = normalizeWorkflowCanvasStage(route.query.stage);
      const resolvedStage = routeStage ?? resolveWorkflowCanvasStageFromCurrent(selectedWorkflow.value, hasMissingCharacterSheets);
      activeCanvasStage.value = resolvedStage;
      // Ensure URL reflects the resolved stage for future refreshes
      if (resolvedStage !== "final" && routeStage !== resolvedStage) {
        router.replace({ query: { ...route.query, stage: resolvedStage } }).catch(() => {});
      }
      applyWorkflowDrafts(selectedWorkflow.value);
      if ((selectedWorkflow.value.clipSlots ?? []).length) {
        const clipSlots = selectedWorkflow.value.clipSlots ?? [];
        if (!clipSlots.some((s) => s.clipIndex === selectedCanvasClipIndex.value)) {
          selectedCanvasClipIndex.value = clipSlots[0].clipIndex;
        }
      } else {
        selectedCanvasClipIndex.value = null;
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "工作流详情加载失败");
      selectedWorkflow.value = null;
    } finally {
      loadingDetail.value = false;
    }
  }

  async function reloadCurrentWorkflow() {
    if (selectedWorkflowId.value) {
      await loadWorkflowDetail(selectedWorkflowId.value);
      await detailOptions.reloadWorkflows();
    }
  }

  async function pollCurrentWorkflow() {
    if (selectedWorkflowId.value) {
      try {
        const data = await fetchWorkflow(selectedWorkflowId.value);
        // Merge into existing ref in-place to avoid replacing the object and triggering full re-render.
        if (selectedWorkflow.value) {
          Object.assign(selectedWorkflow.value, data);
        } else {
          selectedWorkflow.value = data;
        }
      } catch {
        // Silently ignore polling errors — they will surface on the next user action.
      }
    }
  }

  // ── Action Handlers ──

  async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>) {
    const authenticated = await requireAuth({ title: "登录后操作工作流", message: "工作流操作会修改你的个人数据，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.warning("登录后可继续操作工作流。"); return false; }
    busyActionKey.value = actionKey;
    try {
      selectedWorkflow.value = await runner();
      applyWorkflowDrafts(selectedWorkflow.value);
      await detailOptions.reloadWorkflows();
      return true;
    } catch (error) {
      messageApi.error(formatApiErrorMessage(error, "操作失败"));
      return false;
    } finally {
      busyActionKey.value = "";
    }
  }

  async function handleUpdateWorkflowSettings() {
    if (!selectedWorkflowId.value || workflowSettingsValidationMessage.value) return;
    const succeeded = await runAndRefresh("workflow-settings", () => updateWorkflowSettings(selectedWorkflowId.value, buildWorkflowSettingsPayload()));
    if (succeeded) workflowSettingsOpen.value = false;
  }
  async function handleGenerateStoryboard() {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh("storyboard", () => generateStoryboard(selectedWorkflowId.value));
  }
  async function handleAdjustStoryboard(versionId: string) {
    if (!selectedWorkflowId.value) return;
    const prompt = (storyboardAdjustmentDrafts[versionId] || "").trim();
    const succeeded = await runAndRefresh(`storyboard-adjust-${versionId}`, () => adjustStoryboard(selectedWorkflowId.value, versionId, prompt));
    if (succeeded) storyboardAdjustmentDrafts[versionId] = "";
  }
  async function handleSelectStoryboard(versionId: string) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(versionId, () => selectStoryboard(selectedWorkflowId.value, versionId));
  }
  async function handleGenerateKeyframe(clipIndex: number) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(`keyframe-${clipIndex}`, () => generateKeyframe(selectedWorkflowId.value, clipIndex));
  }
  async function handleGenerateMissingCharacterSheets() {
    if (!selectedWorkflowId.value) return;
    const pendingClipIndexes = missingCharacterSheets.value
      .map((s) => characterSheetClipIndex(s))
      .filter((ci): ci is number => ci !== null);
    if (!pendingClipIndexes.length) return;
    busyActionKey.value = "character-missing";
    try {
      for (const clipIndex of pendingClipIndexes) {
        selectedWorkflow.value = await generateKeyframe(selectedWorkflowId.value, clipIndex);
        applyWorkflowDrafts(selectedWorkflow.value);
      }
      await detailOptions.reloadWorkflows();
    } catch (error) {
      messageApi.error(formatApiErrorMessage(error, "角色三视图生成失败"));
    } finally {
      busyActionKey.value = "";
    }
  }
  async function handleGenerateCharacterSheet(sheet: WorkflowCharacterSheet) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (!selectedWorkflowId.value || clipIndex === null) return;
    await runAndRefresh(`character-sheet-${clipIndex}`, () => generateKeyframe(selectedWorkflowId.value, clipIndex));
  }
  async function handleGenerateKeyframeFrame(clipIndex: number, frameRole: string) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(`keyframe-${clipIndex}-${frameRole}`, () => generateKeyframeFrame(selectedWorkflowId.value, clipIndex, frameRole));
  }
  async function handleSelectKeyframe(clipIndex: number, versionId: string) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(versionId, () => selectKeyframe(selectedWorkflowId.value, clipIndex, versionId));
  }
  async function handleSelectCharacterSheetVersion(sheet: WorkflowCharacterSheet, versionId: string) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (!selectedWorkflowId.value || clipIndex === null) return;
    await runAndRefresh(versionId, () => selectKeyframe(selectedWorkflowId.value, clipIndex, versionId));
  }
  async function handleSelectKeyframeFrame(clipIndex: number, versionId: string, frameRole: string) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(`${versionId}-${frameRole}`, () => selectKeyframeFrame(selectedWorkflowId.value, clipIndex, versionId, frameRole));
  }
  async function handleSelectCharacterSheetAsset(sheet: WorkflowCharacterSheet, assetId: string) {
    const clipIndex = characterSheetClipIndex(sheet);
    if (!selectedWorkflowId.value || clipIndex === null) return;
    busyActionKey.value = `character-sheet-asset-${clipIndex}`;
    try {
      await selectCharacterSheetAsset(selectedWorkflowId.value, clipIndex, assetId);
      closeCharacterAssetPicker();
      await reloadCurrentWorkflow();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "角色三视图素材选择失败");
    } finally {
      busyActionKey.value = "";
    }
  }
  async function handleGenerateVideo(clipIndex: number) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(`video-${clipIndex}`, () => generateVideo(selectedWorkflowId.value, clipIndex));
  }
  async function handleSelectVideo(clipIndex: number, versionId: string) {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh(versionId, () => selectVideo(selectedWorkflowId.value, clipIndex, versionId));
  }
  async function handleFinalize() {
    if (!selectedWorkflowId.value) return;
    await runAndRefresh("finalize", () => finalizeWorkflow(selectedWorkflowId.value));
  }
  async function handleDeleteStageVersion(version: StageVersion) {
    const authenticated = await requireAuth({ title: "登录后删除版本", message: "删除版本会修改你的工作流数据，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.warning("登录后可继续删除版本。"); return; }
    if (!selectedWorkflowId.value) return;
    const confirmed = await requestConfirm({ title: "删除版本", message: `删除后不可恢复，确认删除这个版本吗？`, confirmText: "删除" });
    if (!confirmed) return;
    busyActionKey.value = `delete-${version.id}`;
    try {
      selectedWorkflow.value = await deleteStageVersion(selectedWorkflowId.value, version.id);
      applyWorkflowDrafts(selectedWorkflow.value);
      await detailOptions.reloadWorkflows();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "版本删除失败");
    } finally {
      busyActionKey.value = "";
    }
  }
  async function handleClearStageVersions(stageType: string) {
    const stageLabel = stageType === "storyboard" ? "分镜" : stageType === "character" ? "角色三视图" : stageType === "keyframe" ? "关键帧" : "视频";
    const actionKey = `clear-${stageType}-versions`;

    const authenticated = await requireAuth({
      title: `登录后清空${stageLabel}版本`,
      message: `清空${stageLabel}版本会修改你的工作流数据，请先登录或使用邀请码注册。`,
    });
    if (!authenticated) { messageApi.warning("登录后可继续操作。"); return; }
    if (!selectedWorkflowId.value) return;
    const confirmed = await requestConfirm({
      title: `清空${stageLabel}版本`,
      message: `删除后不可恢复，该工作流下的全部${stageLabel}版本都会被清空。确认继续吗？`,
      confirmText: "清空",
    });
    if (!confirmed) return;
    busyActionKey.value = actionKey;
    try {
      if (stageType === "character") {
        const characterVersions = workflowCharacterSheets.value.flatMap((sheet) => characterSheetVersions(sheet));
        for (const version of characterVersions) {
          selectedWorkflow.value = await deleteStageVersion(selectedWorkflowId.value, version.id);
          applyWorkflowDrafts(selectedWorkflow.value);
        }
        if (!characterVersions.length) {
          selectedWorkflow.value = await fetchWorkflow(selectedWorkflowId.value);
        }
      } else {
        selectedWorkflow.value = await deleteAllStageVersions(selectedWorkflowId.value, stageType);
      }
      applyWorkflowDrafts(selectedWorkflow.value);
      await detailOptions.reloadWorkflows();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "版本清空失败");
    } finally {
      busyActionKey.value = "";
    }
  }
  async function handleReuseAsset(assetId: string, versionId: string) {
    if (!assetId) return;
    const authenticated = await requireAuth({ title: "登录后复用素材", message: "复用素材会创建你的阶段工作流，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.warning("登录后可继续复用素材。"); return; }
    busyActionKey.value = `reuse-${versionId}`;
    try {
      await reuseMaterialAsset(assetId, { mode: "clone" });
      await detailOptions.reloadWorkflows();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "素材复用失败");
    } finally {
      busyActionKey.value = "";
    }
  }

  function switchCanvasStage(stage: string) {
    const normalizedStage = normalizeWorkflowCanvasStage(stage) ?? "storyboard";
    activeCanvasStage.value = normalizedStage;
    // Sync stage to URL so it survives page refresh
    if (normalizedStage !== "final") {
      router.replace({ query: { ...route.query, stage: normalizedStage } }).catch(() => {});
    }
  }

  function setPreviewStoryboardVersion(versionId: string) { previewStoryboardVersionId.value = versionId; }
  function setPreviewCharacterSheetVersion(sheetKey: string, versionId: string) { previewCharacterSheetVersionIds[sheetKey] = versionId; }
  function setPreviewKeyframeVersion(clipIndex: number, versionId: string) { previewKeyframeVersionIds[clipIndex] = versionId; }
  function setPreviewVideoVersion(clipIndex: number, versionId: string) { previewVideoVersionIds[clipIndex] = versionId; }

  // ── Watchers: auto-load when selectedWorkflowId changes ──

  watch(selectedWorkflowId, (workflowId) => {
    if (!workflowId) { selectedWorkflow.value = null; return; }
    closeCharacterAssetPicker();
    workflowSettingsOpen.value = false;
    void loadWorkflowDetail(workflowId);
  }, { immediate: true });

  watch(() => imagePreviewState.url, () => { imagePreviewLoadFailed.value = false; });
  watch(
    () => [workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio, catalogVideoSizeOptions.value] as const,
    () => { syncVideoSizeSelection(workflowSettingsDraft, workflowSettingsDraft.videoSize); }
  );

  // ── Lifecycle ──

  onMounted(async () => {
    window.addEventListener("keydown", handleImagePreviewKeydown);
    await loadOptions();
  });
  onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleImagePreviewKeydown);
  });

  return {
    // Core state
    selectedWorkflow,
    selectedWorkflowId,
    loadingDetail,
    loadingOptions,
    busyActionKey,
    activeCanvasStage,
    workflowSettingsOpen,
    workflowSettingsDraft,
    workflowSettingsValidationMessage,
    storyboardAdjustmentDrafts,
    characterSummaryPreviewState,
    // Confirm dialog
    confirmDialog,
    acceptConfirm,
    cancelConfirm,
    // Computed
    canvasStageItems,
    workflowParameterTags,
    workflowCharacterSheets,
    missingCharacterSheets,
    selectedStoryboardVersion,
    selectedCanvasClip,
    previewKeyframeVersion,
    previewVideoVersion,
    canFinalize,
    finalizeButtonLabel,
    finalizeHint,
    videoReadiness,
    // Select options
    textModelSelectOptions,
    imageModelSelectOptions,
    videoModelSelectOptions,
    aspectRatioSelectOptions,
    stylePresetSelectOptions,
    workflowSettingsVideoSizeSelectOptions,
    // Image preview
    imagePreviewOverlayRef,
    imagePreviewTriggerRef,
    imagePreviewState,
    imagePreviewCaption,
    imagePreviewLoadFailed,
    openImagePreview,
    closeImagePreview,
    switchImagePreviewFrame,
    // Character asset picker
    characterAssetPicker,
    materialAssetPreviewUrl,
    materialAssetModelLabel,
    isCharacterAssetPickerOpen,
    openCharacterAssetPicker,
    closeCharacterAssetPicker,
    loadCharacterAssetCandidates,
    // Helper functions
    stageVersionDisplayTitle,
    stageStatusLabel,
    videoVersionErrorMessage,
    compactVideoVersionError,
    canSelectVideoVersion,
    videoVersionStatusLabel,
    videoSlotStatusLabel,
    selectCanvasClip,
    storyboardPreviewHtml,
    isLandscapeKeyframeVersion,
    keyframePreviewFrames,
    isPreviewImageFailed,
    isPreviewImageAvailable,
    markPreviewImageFailed,
    versionSeed,
    durationLabel,
    clipSceneSummary,
    formatDateTime,
    openCharacterSummaryPreview,
    closeCharacterSummaryPreview,
    openKeyframeImagePreview,
    positionVersionMenu,
    previewCharacterSheetVersion,
    // Character sheet utils
    characterSheetKey,
    characterSheetClipIndex,
    characterSheetTitle,
    characterSheetAppearanceSummary,
    characterSheetVersions,
    selectedCharacterSheetVersion,
    hasMissingCharacterSheets,
    characterSheetPreviewFrames,
    // Preview setters
    setPreviewStoryboardVersion,
    setPreviewCharacterSheetVersion,
    setPreviewKeyframeVersion,
    setPreviewVideoVersion,
    // Actions
    switchCanvasStage,
    loadWorkflowDetail,
    reloadCurrentWorkflow,
    pollCurrentWorkflow,
    handleUpdateWorkflowSettings,
    handleGenerateStoryboard,
    handleAdjustStoryboard,
    handleSelectStoryboard,
    handleGenerateKeyframe,
    handleGenerateMissingCharacterSheets,
    handleGenerateCharacterSheet,
    handleGenerateKeyframeFrame,
    handleSelectKeyframe,
    handleSelectCharacterSheetVersion,
    handleSelectKeyframeFrame,
    handleSelectCharacterSheetAsset,
    handleGenerateVideo,
    handleSelectVideo,
    handleFinalize,
    handleDeleteStageVersion,
    handleClearStageVersions,
    handleReuseAsset,
  };
}
