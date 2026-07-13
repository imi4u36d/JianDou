import { computed, nextTick, ref, type Ref } from "vue";
import type { ReferenceImageItem } from "./useReferenceImages";
import {
  buildPromptMentionChip,
  getPromptSelectionOffset as getSelectionOffset,
  insertPromptTextAtSelection,
  renderPromptEditor as renderEditor,
  restorePromptSelection as restoreSelection,
  serializePromptEditorContent as serializeEditorContent,
  serializePromptEditorNode,
} from "./prompt-editor-dom";

export interface UsePromptEditorOptions {
  onMentionTrigger?: () => void;
}

export function usePromptEditor(
  referenceImages: Ref<ReferenceImageItem[]>,
  options: UsePromptEditorOptions = {},
) {
  const promptEditor = ref<HTMLDivElement | null>(null);
  const promptText = ref("");
  const composingPrompt = ref(false);
  const syncingPromptFromEditor = ref(false);
  const promptEditorFocused = ref(false);
  const showPromptPlaceholder = computed(
    () => !promptText.value.trim() && !promptEditorFocused.value && !composingPrompt.value,
  );

  function serializePromptEditorContent(): string {
    return promptEditor.value ? serializeEditorContent(promptEditor.value) : promptText.value;
  }

  function buildMentionChip(item: ReferenceImageItem) {
    return buildPromptMentionChip(item);
  }

  function renderPromptEditor(value: string) {
    if (promptEditor.value) renderEditor(promptEditor.value, value, referenceImages.value);
  }

  function getPromptSelectionOffset(editor: HTMLDivElement) {
    return getSelectionOffset(editor);
  }

  function restorePromptSelection(editor: HTMLDivElement, targetOffset: number) {
    restoreSelection(editor, targetOffset);
  }

  function focusPromptEditorToEnd() {
    const editor = promptEditor.value;
    if (!editor) return;
    editor.focus();
    restoreSelection(editor, serializeEditorContent(editor).length);
  }

  function insertPlainTextAtSelection(text: string) {
    const editor = promptEditor.value;
    if (!editor) return;
    if (!insertPromptTextAtSelection(editor, text)) {
      focusPromptEditorToEnd();
      insertPromptTextAtSelection(editor, text);
    }
  }

  function syncPromptTextFromEditor() {
    syncingPromptFromEditor.value = true;
    promptText.value = serializePromptEditorContent();
    nextTick(() => {
      syncingPromptFromEditor.value = false;
    });
  }

  function handlePromptEditorInput(event: InputEvent) {
    if (event?.isComposing) {
      composingPrompt.value = true;
      return;
    }
    if (event.inputType === "insertCompositionText" || composingPrompt.value) return;
    syncPromptTextFromEditor();
    if (event.inputType === "insertText" && event.data === "@") options.onMentionTrigger?.();
  }

  function handlePromptEditorFocus() {
    promptEditorFocused.value = true;
  }

  function handlePromptEditorBlur() {
    promptEditorFocused.value = false;
    renderPromptEditor(promptText.value);
  }

  function handlePromptEditorCompositionStart() {
    composingPrompt.value = true;
  }

  function handlePromptEditorCompositionEnd() {
    composingPrompt.value = false;
    syncPromptTextFromEditor();
  }

  function handlePromptEditorBeforeInput(event: InputEvent) {
    if (event.isComposing || event.inputType === "insertCompositionText") composingPrompt.value = true;
  }

  function handlePromptEditorKeydown(event: KeyboardEvent) {
    if (composingPrompt.value || event.isComposing || event.key !== "Enter") return;
    event.preventDefault();
    insertPlainTextAtSelection("\n");
    syncPromptTextFromEditor();
    nextTick(() => renderPromptEditor(promptText.value));
  }

  function handlePromptEditorPaste(event: ClipboardEvent) {
    if (composingPrompt.value) return;
    event.preventDefault();
    insertPlainTextAtSelection(event.clipboardData?.getData("text/plain") ?? "");
    syncPromptTextFromEditor();
    nextTick(() => renderPromptEditor(promptText.value));
  }

  return {
    promptEditor,
    promptText,
    composingPrompt,
    syncingPromptFromEditor,
    promptEditorFocused,
    showPromptPlaceholder,
    serializePromptEditorNode,
    serializePromptEditorContent,
    buildMentionChip,
    renderPromptEditor,
    getPromptSelectionOffset,
    restorePromptSelection,
    focusPromptEditorToEnd,
    insertPlainTextAtSelection,
    syncPromptTextFromEditor,
    handlePromptEditorInput,
    handlePromptEditorFocus,
    handlePromptEditorBlur,
    handlePromptEditorCompositionStart,
    handlePromptEditorCompositionEnd,
    handlePromptEditorBeforeInput,
    handlePromptEditorKeydown,
    handlePromptEditorPaste,
  };
}
