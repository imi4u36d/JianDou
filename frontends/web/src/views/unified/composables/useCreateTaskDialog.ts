import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import { fetchGenerationOptions } from "@/api/generation";
import { requireAuth } from "@/auth/modal";
import { useAuthSessionState } from "@/auth/session";
import { createWorkflow, saveDefaultAspectRatio } from "@/features/workflows";
import type { GenerationOptionsResponse } from "@/types";
import { formatApiErrorMessage } from "@/utils/api-error";
import {
  defaultTaskAspectRatio,
  preferredModelValue,
  preferredVideoSizeValue,
  toAspectRatioOptions,
} from "@/views/unified/features/create-task-options";

type CreateTaskDialogDependencies = {
  fetchOptions: typeof fetchGenerationOptions;
  create: typeof createWorkflow;
  saveAspectRatio: typeof saveDefaultAspectRatio;
  authenticate: typeof requireAuth;
  authenticated: () => boolean;
  formatError: typeof formatApiErrorMessage;
};

type CreateTaskDialogOptions = {
  open: () => boolean;
  close: () => void;
  created: (id: string) => void;
  dependencies?: Partial<CreateTaskDialogDependencies>;
};

export function useCreateTaskDialog({
  open,
  close,
  created,
  dependencies = {},
}: CreateTaskDialogOptions) {
  const authState = useAuthSessionState();
  const deps: CreateTaskDialogDependencies = {
    fetchOptions: fetchGenerationOptions,
    create: createWorkflow,
    saveAspectRatio: saveDefaultAspectRatio,
    authenticate: requireAuth,
    authenticated: () => authState.isAuthenticated.value,
    formatError: formatApiErrorMessage,
    ...dependencies,
  };
  const titleInputRef = ref<HTMLInputElement | null>(null);
  const submitting = ref(false);
  const catalog = ref<GenerationOptionsResponse | null>(null);
  const taskTitle = ref("");
  const taskPrompt = ref("");
  const taskAspectRatio = ref("");
  const taskStatusText = ref("");
  let returnFocusTarget: HTMLElement | null = null;

  const aspectRatioOptions = computed(() => toAspectRatioOptions(catalog.value));
  const isStatusError = computed(() => Boolean(
    taskStatusText.value && !taskStatusText.value.includes("成功"),
  ));

  function chooseAspectRatio(source: GenerationOptionsResponse): void {
    taskAspectRatio.value ||= defaultTaskAspectRatio(
      toAspectRatioOptions(source),
      source.defaultAspectRatio,
    );
  }

  async function loadOptions(): Promise<GenerationOptionsResponse> {
    const resolved = catalog.value ?? await deps.fetchOptions();
    catalog.value = resolved;
    chooseAspectRatio(resolved);
    return resolved;
  }

  function restoreFocus(): void {
    const target = returnFocusTarget;
    returnFocusTarget = null;
    target?.focus({ preventScroll: true });
  }

  function requestClose(): void {
    if (!submitting.value) close();
  }

  async function submitTask(): Promise<void> {
    if (!taskTitle.value.trim()) return;
    const authenticated = await deps.authenticate({
      title: "登录后创建任务",
      message: "生成结果会保存到你的任务和素材库中，请先登录或使用邀请码注册。",
    });
    if (!authenticated) return;
    submitting.value = true;
    taskStatusText.value = "";
    try {
      const options = await loadOptions();
      const textAnalysisModel = preferredModelValue(options.textAnalysisModels, "openai");
      const imageModel = preferredModelValue(options.imageModels, "openai");
      const videoModel = preferredModelValue(options.videoModels, "agnes");
      const workflow = await deps.create({
        title: taskTitle.value.trim(),
        transcriptText: taskPrompt.value.trim() || null,
        aspectRatio: taskAspectRatio.value,
        textAnalysisModel,
        imageModel,
        videoModel,
        videoSize: preferredVideoSizeValue(options, videoModel, taskAspectRatio.value),
        durationMode: "auto",
        executionMode: "auto",
      });
      taskTitle.value = "";
      taskPrompt.value = "";
      taskStatusText.value = "创建成功";
      created(workflow.id);
    } catch (error) {
      taskStatusText.value = deps.formatError(error, "创建任务失败");
    } finally {
      submitting.value = false;
    }
  }

  onMounted(() => void loadOptions().catch(() => undefined));
  watch(open, async (isOpen) => {
    if (isOpen) {
      returnFocusTarget = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      await nextTick();
      titleInputRef.value?.focus({ preventScroll: true });
    } else {
      restoreFocus();
    }
  });
  watch(taskAspectRatio, (next, previous) => {
    if (!previous || !next || next === previous || !deps.authenticated()) return;
    void deps.saveAspectRatio(next).catch(() => undefined);
  });
  onBeforeUnmount(restoreFocus);

  return {
    aspectRatioOptions,
    isStatusError,
    requestClose,
    submitTask,
    submitting,
    taskAspectRatio,
    taskPrompt,
    taskStatusText,
    taskTitle,
    titleInputRef: titleInputRef as Ref<HTMLInputElement | null>,
  };
}
