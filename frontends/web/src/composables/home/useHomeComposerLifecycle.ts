import { onBeforeUnmount, onMounted, watch, type Ref } from "vue";
import type { ReferenceImageItem } from "./useReferenceImages";
import type { HomeComposerMenuKey } from "@/views/home/components/HomeComposerToolbar.vue";

export interface HomeComposerLifecycleOptions {
  activeMenu: Ref<HomeComposerMenuKey>;
  statusText: Ref<string>;
  referenceImages: Ref<ReferenceImageItem[]>;
  referenceImagesBridge: Ref<ReferenceImageItem[]>;
  promptText: Ref<string>;
  promptEditor: Ref<HTMLElement | null>;
  composingPrompt: Ref<boolean>;
  syncingPromptFromEditor: Ref<boolean>;
  authenticated: () => boolean;
  renderPromptEditor: (value: string) => void;
  loadOptions: () => Promise<unknown>;
  loadCredits: () => unknown;
  dismissTaskToast: () => void;
}

export function isHomeComposerMenuTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(target.closest(".home-menu"));
}

export function useHomeComposerLifecycle(options: HomeComposerLifecycleOptions) {
  function handleDocumentPointerDown(event: PointerEvent) {
    if (options.activeMenu.value && !isHomeComposerMenuTarget(event.target)) {
      options.activeMenu.value = "";
    }
  }

  function handleDocumentKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") options.activeMenu.value = "";
  }

  watch(
    options.referenceImages,
    (value) => {
      options.referenceImagesBridge.value = value;
    },
    { immediate: true },
  );

  watch(options.promptText, (value) => {
    if (options.composingPrompt.value || options.syncingPromptFromEditor.value) return;
    if (document.activeElement === options.promptEditor.value) return;
    options.renderPromptEditor(value);
  });

  watch(
    options.referenceImages,
    () => {
      if (!options.composingPrompt.value) {
        options.renderPromptEditor(options.promptText.value);
      }
    },
    { deep: true },
  );

  watch(options.authenticated, () => {
    options.loadCredits();
  });

  onMounted(() => {
    options.loadOptions()
      .then(() => {
        options.statusText.value = "";
      })
      .catch((error: unknown) => {
        options.statusText.value = error instanceof Error ? error.message : "加载模型配置失败";
      });
    options.loadCredits();
    document.addEventListener("pointerdown", handleDocumentPointerDown);
    document.addEventListener("keydown", handleDocumentKeydown);
    options.renderPromptEditor(options.promptText.value);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("pointerdown", handleDocumentPointerDown);
    document.removeEventListener("keydown", handleDocumentKeydown);
    options.dismissTaskToast();
  });
}
