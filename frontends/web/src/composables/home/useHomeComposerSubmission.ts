import { computed, type Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import { createGenerationTask, saveDefaultAspectRatio } from "@/features/home";
import {
  buildImageGenerationRequest,
  buildSubmitFingerprint,
  buildVideoWorkflowRequest,
  type HomeSubmissionSnapshot,
} from "@/features/home/home-submission";
import { createWorkflow } from "@/features/workflows";
import { formatApiErrorMessage } from "@/utils/api-error";
import { useHomeSubmissionGuard } from "./useHomeSubmissionGuard";

interface HomeSubmissionApi {
  createTask: typeof createGenerationTask;
  createWorkflow: typeof createWorkflow;
  saveAspectRatio: typeof saveDefaultAspectRatio;
}

interface HomeSubmissionDependencies {
  api?: HomeSubmissionApi;
  authenticate?: typeof requireAuth;
  formatError?: typeof formatApiErrorMessage;
}

interface HomeComposerSubmissionOptions {
  statusText: Ref<string>;
  isFormReady: () => boolean;
  modeKind: () => "image" | "video";
  snapshot: () => HomeSubmissionSnapshot;
  imageRequestOptions: () => { assetType: string; resolvedAspectRatio: string };
  defaultVideoSize: () => string | null;
  aspectRatio: () => string;
  isAuthenticated: () => boolean;
  resetComposer: () => void;
  loadActiveTasks: () => Promise<unknown> | void;
  push: (location: { name: string; params: { workflowId: string } }) => Promise<unknown> | unknown;
  dependencies?: HomeSubmissionDependencies;
}

const defaultApi: HomeSubmissionApi = {
  createTask: createGenerationTask,
  createWorkflow,
  saveAspectRatio: saveDefaultAspectRatio,
};

export function useHomeComposerSubmission(options: HomeComposerSubmissionOptions) {
  const dependencies = options.dependencies ?? {};
  const api = dependencies.api ?? defaultApi;
  const authenticate = dependencies.authenticate ?? requireAuth;
  const formatError = dependencies.formatError ?? formatApiErrorMessage;
  const guard = useHomeSubmissionGuard();
  const submitLabel = computed(() => {
    if (guard.submitting.value) return "创建中";
    return options.modeKind() === "video" ? "生成视频" : "生成图片";
  });

  function persistAspectRatio() {
    if (options.isAuthenticated()) {
      void api.saveAspectRatio(options.aspectRatio()).catch(() => undefined);
    }
  }

  async function submitImage(snapshot: HomeSubmissionSnapshot) {
    const task = await api.createTask(buildImageGenerationRequest(snapshot, options.imageRequestOptions()));
    persistAspectRatio();
    guard.createdTaskId.value = task.id;
    guard.showTaskToast(task.id);
    options.statusText.value = "已提交";
    options.resetComposer();
    void options.loadActiveTasks();
  }

  async function submitVideo(snapshot: HomeSubmissionSnapshot) {
    const workflow = await api.createWorkflow(buildVideoWorkflowRequest(snapshot, options.defaultVideoSize()));
    persistAspectRatio();
    options.statusText.value = "已创建视频任务";
    options.resetComposer();
    await options.push({ name: "video-task-detail", params: { workflowId: workflow.id } });
  }

  async function submitComposer() {
    if (guard.submitting.value) {
      options.statusText.value = "正在创建，请稍候。";
      return;
    }
    if (!options.isFormReady()) {
      options.statusText.value = "请先输入内容并补全参数。";
      return;
    }
    const snapshot = options.snapshot();
    const fingerprint = buildSubmitFingerprint(snapshot);
    const startResult = guard.begin(fingerprint);
    if (startResult === "duplicate") {
      options.statusText.value = "相同内容刚刚提交过，请勿重复发送。";
      return;
    }
    if (startResult === "busy") {
      options.statusText.value = "正在创建，请稍候。";
      return;
    }
    const authenticated = await authenticate({
      title: "登录后开始生成",
      message: "生成结果会保存到你的任务和素材库中，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      options.statusText.value = "登录后即可继续生成。";
      guard.finish(fingerprint, false);
      return;
    }
    guard.createdTaskId.value = "";
    let successful = false;
    try {
      if (snapshot.mode === "video") await submitVideo(snapshot);
      else await submitImage(snapshot);
      successful = true;
    } catch (error) {
      options.statusText.value = formatError(error, "创建失败");
    } finally {
      guard.finish(fingerprint, successful);
    }
  }

  return {
    submitting: guard.submitting,
    createdTaskId: guard.createdTaskId,
    taskToastTaskId: guard.taskToastTaskId,
    dismissTaskToast: guard.dismissTaskToast,
    submitLabel,
    submitComposer,
  };
}
